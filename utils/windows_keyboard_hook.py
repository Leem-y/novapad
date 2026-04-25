from __future__ import annotations

import sys
from dataclasses import dataclass


def _is_windows() -> bool:
    return sys.platform == "win32"


@dataclass(frozen=True, slots=True)
class HookHotkey:
    mods: int  # shift=1, ctrl=2, alt=4
    key: str   # A-Z, 0-9, F1-F24
    payload: object


def _vk_from_key(key: str) -> int | None:
    k = (key or "").strip().upper()
    if not k:
        return None
    if len(k) == 1:
        ch = k[0]
        if "A" <= ch <= "Z":
            return ord(ch)
        if "0" <= ch <= "9":
            return ord(ch)
    if k.startswith("F"):
        try:
            n = int(k[1:])
            if 1 <= n <= 24:
                return 0x70 + (n - 1)
        except Exception:
            return None
    return None


class WindowsKeyboardHook:
    """
    Low-level keyboard hook (WH_KEYBOARD_LL).

    CopyTexty-style behavior:
    - detect hotkey on key-down (modifiers + key)
    - consume the key events so the target app doesn't also act on the hotkey
    - fire the action on key-up (key released), which reduces "modifiers still held"
      issues when we later inject Ctrl+V.
    """

    def __init__(self, on_fire):
        self._on_fire = on_fire
        self._bindings: list[tuple[int, int, object]] = []  # (mods, vk, payload)
        self._enabled = False

        self._pressed: set[int] = set()
        self._active_payload: object | None = None
        self._active_vk: int | None = None
        self._consume_vk: int | None = None

        self._h_hook = None
        self._proc_ref = None
        self._last_error: int = 0

    def last_error(self) -> int:
        return int(self._last_error or 0)

    def set_bindings(self, bindings: list[HookHotkey]):
        out: list[tuple[int, int, object]] = []
        for b in bindings or []:
            vk = _vk_from_key(b.key)
            if vk is None:
                continue
            if int(b.mods or 0) == 0:
                continue
            out.append((int(b.mods), int(vk), b.payload))
        self._bindings = out

    def start(self) -> bool:
        if not _is_windows():
            return False
        if self._enabled:
            return True

        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        WH_KEYBOARD_LL = 13
        WM_KEYDOWN = 0x0100
        WM_KEYUP = 0x0101
        WM_SYSKEYDOWN = 0x0104
        WM_SYSKEYUP = 0x0105

        VK_SHIFT = 0x10
        VK_CONTROL = 0x11
        VK_MENU = 0x12  # Alt

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG_PTR if hasattr(wintypes, "ULONG_PTR") else ctypes.c_size_t),
            ]

        LowLevelProc = ctypes.WINFUNCTYPE(wintypes.LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        # Correct prototype for SetWindowsHookExW: (int, HOOKPROC, HINSTANCE, DWORD) -> HHOOK
        try:
            user32.SetWindowsHookExW.argtypes = [ctypes.c_int, LowLevelProc, wintypes.HINSTANCE, wintypes.DWORD]
            user32.SetWindowsHookExW.restype = wintypes.HANDLE
        except Exception:
            # Don't let prototype setup block hook install
            pass

        def _mods_now() -> int:
            m = 0
            try:
                if user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
                    m |= 1
                if user32.GetAsyncKeyState(VK_CONTROL) & 0x8000:
                    m |= 2
                if user32.GetAsyncKeyState(VK_MENU) & 0x8000:
                    m |= 4
            except Exception:
                pass
            return m

        def _fire(payload):
            try:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._on_fire(payload))
            except Exception:
                try:
                    self._on_fire(payload)
                except Exception:
                    pass

        def hook_proc(nCode, wParam, lParam):
            try:
                if nCode < 0:
                    return user32.CallNextHookEx(self._h_hook, nCode, wParam, lParam)

                msg = int(wParam)
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = int(kb.vkCode)

                is_down = msg in (WM_KEYDOWN, WM_SYSKEYDOWN)
                is_up = msg in (WM_KEYUP, WM_SYSKEYUP)

                if is_down:
                    self._pressed.add(vk)

                    mods = _mods_now()
                    for need_mods, need_vk, payload in self._bindings:
                        if vk != need_vk:
                            continue
                        if (mods & need_mods) != need_mods:
                            continue
                        # Activate: consume this key, and fire on key-up.
                        self._active_payload = payload
                        self._active_vk = vk
                        self._consume_vk = vk
                        return 1  # eat

                if is_up:
                    self._pressed.discard(vk)
                    if self._consume_vk is not None and vk == self._consume_vk:
                        payload = self._active_payload
                        self._active_payload = None
                        self._active_vk = None
                        self._consume_vk = None
                        if payload is not None:
                            _fire(payload)
                        return 1  # eat key-up too

                return user32.CallNextHookEx(self._h_hook, nCode, wParam, lParam)
            except Exception:
                return user32.CallNextHookEx(self._h_hook, nCode, wParam, lParam)

        self._proc_ref = LowLevelProc(hook_proc)

        # For WH_KEYBOARD_LL, hMod can be NULL; try NULL first (most compatible),
        # then fall back to module handle.
        self._h_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc_ref, None, 0)
        if not self._h_hook:
            self._last_error = ctypes.get_last_error()
            h_mod = kernel32.GetModuleHandleW(None)
            self._h_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc_ref, h_mod, 0)
        if not self._h_hook:
            self._last_error = ctypes.get_last_error() or self._last_error
            self._proc_ref = None
            return False
        self._enabled = True
        self._last_error = 0
        return True

    def stop(self) -> None:
        if not _is_windows():
            return
        if not self._enabled:
            return

        import ctypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        try:
            if self._h_hook:
                user32.UnhookWindowsHookEx(self._h_hook)
        except Exception:
            pass
        self._h_hook = None
        self._proc_ref = None
        self._enabled = False

