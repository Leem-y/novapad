from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer


class SessionController(QObject):
    """
    Owns session autosave wiring for a window:
    - debounced save after document edits (800ms)
    - periodic save for cursor/scroll changes (30s)

    This keeps `main.py` independent of TabManager/CodeEditor internals.
    """

    def __init__(self, session, tabs, parent: QObject | None = None):
        super().__init__(parent)
        self._session = session
        self._tabs = tabs

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._save_now)

        self._connected_editors: set[int] = set()

        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._save_now)
        self._auto_timer.start(30_000)

        # Wire up whenever a tab becomes active (covers new tab creation too)
        self._tabs.tab_changed.connect(lambda _: self._connect_all_editors())
        self._connect_all_editors()

    def _save_now(self):
        try:
            window = self._tabs.parent()
            if window is not None:
                self._session.save(window)
        except Exception:
            # Session save should never crash the UI loop
            pass

    def _connect_all_editors(self):
        for e in self._tabs.all_editors():
            eid = id(e)
            if eid in self._connected_editors:
                continue
            self._connected_editors.add(eid)
            try:
                e.document().contentsChanged.connect(lambda: self._save_timer.start())
            except Exception:
                pass

