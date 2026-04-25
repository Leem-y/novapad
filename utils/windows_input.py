from __future__ import annotations

import sys
import os


def _is_windows() -> bool:
    return sys.platform == "win32"


_last_paste_method: str = ""
_last_paste_error: int = 0
_last_paste_exception: str = ""


def last_paste_info() -> tuple[str, int, str]:
    return (
        str(_last_paste_method or ""),
        int(_last_paste_error or 0),
        str(_last_paste_exception or ""),
    )


def send_ctrl_v() -> bool:
    """
    Best-effort paste into the foreground application.
    Returns True if a paste was dispatched.
    """
    if not _is_windows():
        return False

    global _last_paste_method, _last_paste_error
    _last_paste_method = "init"
    _last_paste_error = 0
    global _last_paste_exception
    _last_paste_exception = ""

    try:
        import ctypes
        import time
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        INPUT_KEYBOARD = 1
        KEYEVENTF_KEYUP = 0x0002
        KEYEVENTF_SCANCODE = 0x0008

        VK_CONTROL = 0x11
        VK_SHIFT = 0x10
        VK_MENU = 0x12  # Alt
        VK_V = 0x56
        VK_LCONTROL = 0xA2
        VK_RCONTROL = 0xA3
        VK_LSHIFT = 0xA0
        VK_RSHIFT = 0xA1
        VK_LMENU = 0xA4
        VK_RMENU = 0xA5

        WM_PASTE = 0x0302
        MAPVK_VK_TO_VSC = 0
        ASFW_ANY = 0xFFFFFFFF

        ULONG_PTR = getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            ]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            ]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD),
            ]

        # Union must include the largest Win32 member or SendInput fails with 87 on x64.
        class INPUT_UNION(ctypes.Union):
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT),
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]

        def _scan(vk: int) -> int:
            try:
                return int(user32.MapVirtualKeyW(int(vk), MAPVK_VK_TO_VSC)) & 0xFFFF
            except Exception:
                return 0

        def _inp_scan(vk: int, up: bool) -> INPUT:
            i = INPUT()
            i.type = INPUT_KEYBOARD
            i.u.ki = KEYBDINPUT(
                wVk=0,
                wScan=_scan(vk),
                dwFlags=(KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0)),
                time=0,
                dwExtraInfo=0,
            )
            return i

        def _inp_vk(vk: int, up: bool) -> INPUT:
            i = INPUT()
            i.type = INPUT_KEYBOARD
            i.u.ki = KEYBDINPUT(
                wVk=vk,
                wScan=0,
                dwFlags=(KEYEVENTF_KEYUP if up else 0),
                time=0,
                dwExtraInfo=0,
            )
            return i

        def _send(seq: tuple[INPUT, ...]) -> bool:
            nonlocal user32
            global _last_paste_error
            arr = (INPUT * len(seq))(*seq)
            cb = int(ctypes.sizeof(INPUT))
            sent = int(user32.SendInput(len(seq), arr, cb))
            if sent == len(seq):
                return True
            _last_paste_error = int(ctypes.get_last_error())
            return False

        kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        kernel32.GetCurrentThreadId.argtypes = []

        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetForegroundWindow.argtypes = []

        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD

        user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        user32.AttachThreadInput.restype = wintypes.BOOL

        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL

        user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
        user32.AllowSetForegroundWindow.restype = wintypes.BOOL

        tid_self = int(kernel32.GetCurrentThreadId())
        tid_target = tid_self
        attached = False
        try:
            fg = user32.GetForegroundWindow()
            if fg:
                tid_target = int(user32.GetWindowThreadProcessId(fg, None))
                if tid_target and tid_target != tid_self:
                    try:
                        user32.AllowSetForegroundWindow(ASFW_ANY)
                    except Exception:
                        pass
                    if user32.AttachThreadInput(tid_self, tid_target, True):
                        attached = True
                        try:
                            user32.SetForegroundWindow(fg)
                        except Exception:
                            pass
                        time.sleep(0.02)

            # Clear stuck chord from the global hotkey so the next SendInput is a clean Ctrl+V.
            _force_vks = (
                VK_LMENU,
                VK_RMENU,
                VK_LSHIFT,
                VK_RSHIFT,
                VK_LCONTROL,
                VK_RCONTROL,
            )
            _send(tuple(_inp_scan(vk, True) for vk in _force_vks))
            _send(tuple(_inp_vk(vk, True) for vk in _force_vks))

            _last_paste_method = "sendinput_scancode"
            if _send(
                (
                    _inp_scan(VK_CONTROL, False),
                    _inp_scan(VK_V, False),
                    _inp_scan(VK_V, True),
                    _inp_scan(VK_CONTROL, True),
                ),
            ):
                return True

            _last_paste_method = "sendinput_vk"
            if _send(
                (
                    _inp_vk(VK_CONTROL, False),
                    _inp_vk(VK_V, False),
                    _inp_vk(VK_V, True),
                    _inp_vk(VK_CONTROL, True),
                ),
            ):
                return True

            # WM_PASTE can be ignored by many apps (e.g. Electron/browsers). We still
            # dispatch it as a best-effort fallback, but report False so the caller
            # can show "Press Ctrl+V" (clipboard is already set).
            _last_paste_method = "wm_paste_foreground"
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                kernel32.SetLastError(0)
                pm_ok = bool(user32.PostMessageW(hwnd, WM_PASTE, 0, 0))
                _last_paste_error = int(ctypes.get_last_error()) if not pm_ok else 0
                return False

            _last_paste_method = "all_failed"
            return False
        finally:
            if attached:
                try:
                    user32.AttachThreadInput(tid_self, tid_target, False)
                except Exception:
                    pass
    except Exception as e:
        # Never crash the app; leave clipboard as the fallback.
        try:
            import ctypes as _ct

            _last_paste_error = _ct.get_last_error()
        except Exception:
            _last_paste_error = 0
        _last_paste_method = "exception_top"
        try:
            import traceback

            details = traceback.format_exc()
        except Exception:
            details = repr(e)

        try:
            # Write details to a predictable file for debugging.
            log_path = os.path.join(os.path.dirname(__file__), "paste_error.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(details)
            _last_paste_exception = "see paste_error.log"
        except Exception:
            _last_paste_exception = repr(e)
        return False
