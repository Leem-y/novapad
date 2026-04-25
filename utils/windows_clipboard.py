from __future__ import annotations

import sys


def _is_windows() -> bool:
    return sys.platform == "win32"

_last_error: int = 0
_last_stage: str = ""  # "open" | "empty" | "alloc" | "lock" | "setdata" | ""


def last_error() -> int:
    """Last Win32 error code observed by set_clipboard_text()."""
    return int(_last_error or 0)


def last_stage() -> str:
    """Which step failed (empty string if unknown or success)."""
    return str(_last_stage or "")


def set_clipboard_text(text: str) -> bool:
    """Set Unicode text to the Windows clipboard (Windows only)."""
    global _last_error, _last_stage
    _last_error = 0
    _last_stage = ""
    if not _is_windows():
        return False
    if text is None:
        text = ""

    import ctypes
    import time
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # Prototypes (so last_error is reliable)
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    # Clipboard is often briefly held by other apps; retry with modest backoff.
    delays_ms = (10, 15, 20, 25, 30, 40, 50, 60, 75, 90, 100, 120)
    opened = False
    for delay in delays_ms:
        if user32.OpenClipboard(None):
            opened = True
            break
        _last_error = ctypes.get_last_error()
        _last_stage = "open"
        time.sleep(delay / 1000.0)
    if not opened:
        return False

    try:
        if not user32.EmptyClipboard():
            _last_error = ctypes.get_last_error()
            _last_stage = "empty"
            return False

        data = (text + "\x00").encode("utf-16-le")
        hglob = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not hglob:
            _last_error = ctypes.get_last_error()
            _last_stage = "alloc"
            return False

        locked = kernel32.GlobalLock(hglob)
        if not locked:
            _last_error = ctypes.get_last_error()
            _last_stage = "lock"
            kernel32.GlobalFree(hglob)
            return False

        try:
            ctypes.memmove(locked, data, len(data))
        finally:
            kernel32.GlobalUnlock(hglob)

        if not user32.SetClipboardData(CF_UNICODETEXT, hglob):
            _last_error = ctypes.get_last_error()
            _last_stage = "setdata"
            kernel32.GlobalFree(hglob)
            return False

        _last_stage = ""
        # On success, the system owns hglob.
        return True
    finally:
        user32.CloseClipboard()
