from __future__ import annotations

import sys
from dataclasses import dataclass

from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, Qt


def _is_windows() -> bool:
    return sys.platform == "win32"


@dataclass(frozen=True, slots=True)
class GlobalHotkey:
    mods: int  # shift=1, ctrl=2, alt=4
    key: str   # A-Z, 0-9, F1-F24


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


def _win_mods(mods: int) -> int:
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    out = 0
    if mods & 1:
        out |= MOD_SHIFT
    if mods & 2:
        out |= MOD_CONTROL
    if mods & 4:
        out |= MOD_ALT
    return out


class _HotkeySinkWidget:
    """
    A tiny hidden QWidget that receives WM_HOTKEY directly via nativeEvent.
    Using a real HWND here is more reliable than depending on a global native
    event filter across Qt versions.
    """

    def __init__(self, on_hotkey, id_to_payload: dict[int, object]):
        from PyQt6.QtWidgets import QWidget

        class Sink(QWidget):
            def nativeEvent(self, eventType, message):
                try:
                    import ctypes
                    from ctypes import wintypes

                    WM_HOTKEY = 0x0312
                    msg = wintypes.MSG.from_address(int(message))
                    if msg.message == WM_HOTKEY:
                        hid = int(msg.wParam)
                        payload = id_to_payload.get(hid)
                        if payload is not None and callable(on_hotkey):
                            on_hotkey(payload)
                        return True, 0
                except Exception:
                    pass
                return False, 0

        self.widget = Sink(None)
        self.widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.widget.setWindowFlag(Qt.WindowType.Tool, True)
        self.widget.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.widget.resize(1, 1)
        self.widget.show()  # force HWND creation

    def hwnd(self) -> int:
        return int(self.widget.winId())

    def close(self):
        try:
            self.widget.close()
            self.widget.deleteLater()
        except Exception:
            pass


class WindowsGlobalHotkeyManager(QObject, QAbstractNativeEventFilter):
    """
    Safe global hotkeys:
    - RegisterHotKey with hwnd=NULL (posts WM_HOTKEY to this thread's message queue)
    - Capture WM_HOTKEY via Qt native event filter

    This avoids relying on a particular window handle during startup.
    """

    def __init__(self, on_hotkey):
        super().__init__()
        self._on_hotkey = on_hotkey
        self._next_id = 2000
        self._id_to_payload: dict[int, object] = {}
        self._hwnd: int | None = None
        self._sink: _HotkeySinkWidget | None = None

    def set_hwnd(self, hwnd: int | None):
        """Set the HWND that should receive WM_HOTKEY (recommended)."""
        self._hwnd = int(hwnd) if hwnd else None

    def ensure_sink_hwnd(self) -> int | None:
        if not _is_windows():
            return None
        if self._sink is None:
            self._sink = _HotkeySinkWidget(self._on_hotkey, self._id_to_payload)
            self._hwnd = self._sink.hwnd()
        return self._hwnd

    def clear(self):
        if not _is_windows():
            self._id_to_payload.clear()
            return
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = self._hwnd
        for hid in list(self._id_to_payload.keys()):
            try:
                user32.UnregisterHotKey(hwnd, hid)
            except Exception:
                pass
        self._id_to_payload.clear()
        # Keep the sink alive; it’s harmless and avoids HWND churn.

    def register(self, hk: GlobalHotkey, payload: object) -> int | None:
        if not _is_windows():
            return None
        vk = _vk_from_key(hk.key)
        if vk is None:
            return None
        mods = _win_mods(hk.mods)
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = self._hwnd
        hid = self._next_id
        self._next_id += 1
        ok = bool(user32.RegisterHotKey(hwnd, hid, mods, vk))
        if not ok:
            return None
        self._id_to_payload[hid] = payload
        return hid

    def nativeEventFilter(self, eventType, message):
        if not _is_windows():
            return False, 0
        try:
            import ctypes
            from ctypes import wintypes

            WM_HOTKEY = 0x0312
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                hid = int(msg.wParam)
                payload = self._id_to_payload.get(hid)
                if payload is not None and callable(self._on_hotkey):
                    self._on_hotkey(payload)
                return True, 0
        except Exception:
            pass
        return False, 0

