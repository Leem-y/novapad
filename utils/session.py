# utils/session.py -- NovaPad Session Manager (v4)
#
# Full session persistence:
#   - Saves ALL open tabs on close (saved AND unsaved)
#   - Unsaved content written to AppData/NovaPad/session/tabs/<id>.txt
#   - Metadata in session.json: path, label, cursor, scroll, modified
#   - Crash detection: lock file set at startup, cleared on clean exit
#   - Restore prompt when crash detected
#   - Atomic file writes prevent corruption on sudden shutdown
#   - Auto-session save every 30s (driven by timer in main.py)
#
# Session directory layout:
#   AppData/NovaPad/
#     session/
#       session.json      <- metadata for all tabs
#       running.lock      <- exists while app is running (crash marker)
#       tabs/
#         <uuid>.txt      <- content of each unsaved/modified tab

from __future__ import annotations

import json
import os
import platform
import tempfile
import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

def _appdata_dir() -> str:
    """Return the NovaPad app-data directory, creating it if needed."""
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif platform.system() == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    d = os.path.join(base, "NovaPad")
    os.makedirs(d, exist_ok=True)
    return d


def _session_dir() -> str:
    d = os.path.join(_appdata_dir(), "session", "tabs")
    os.makedirs(d, exist_ok=True)
    return d


def _meta_path() -> str:
    return os.path.join(_appdata_dir(), "session", "session.json")


def _lock_path() -> str:
    """Presence of this file means the app did NOT close cleanly."""
    return os.path.join(_appdata_dir(), "session", "running.lock")


# ---------------------------------------------------------------------------
# ATOMIC WRITE
# ---------------------------------------------------------------------------

def _atomic_write(path: str, text: str) -> None:
    """Write text to a temp file then rename -- prevents partial writes."""
    dir_ = os.path.dirname(path)
    os.makedirs(dir_, exist_ok=True)
    try:
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)   # atomic on all modern OSes
    except OSError:
        pass


# ---------------------------------------------------------------------------
# SESSION MANAGER
# ---------------------------------------------------------------------------

class SessionManager:
    """
    Save and restore the full editor session, including unsaved content.

    Session metadata format (session.json)
    ---------------------------------------
    {
      "version": 2,
      "active_index": 1,
      "tabs": [
        {
          "id":        "a3f2...",
          "label":     "Untitled-1",
          "file_path": null,
          "temp_file": "tabs/a3f2.txt",
          "modified":  true,
          "cursor":    [12, 5],
          "scroll_y":  120
        }
      ]
    }
    """

    def __init__(self) -> None:
        self._session_dir = _session_dir()

    # -- Crash detection -----------------------------------------------------

    def was_crash(self) -> bool:
        """Return True if a lock file exists (previous run crashed)."""
        return os.path.exists(_lock_path())

    def mark_running(self) -> None:
        """Create the lock file at startup."""
        _atomic_write(_lock_path(), str(time.time()))

    def mark_clean_exit(self) -> None:
        """Remove the lock file on clean exit."""
        try:
            if os.path.exists(_lock_path()):
                os.remove(_lock_path())
        except OSError:
            pass

    # -- Save ----------------------------------------------------------------

    def save(self, window: "MainWindow", clean: bool = True) -> None:
        """
        Persist the full session state.
        Called on clean exit AND by the periodic auto-save timer.
        Does NOT overwrite original user files -- only writes to temp storage.
        """
        tabs_meta = []
        tabs = window._tabs

        for i in range(tabs.count()):
            editor = tabs.editor_at(i)
            if editor is None:
                continue

            label     = tabs.tab_label_at(i)
            file_path = editor.file_path
            modified  = editor.document().isModified()
            content   = editor.toPlainText()

            # Cursor position
            cursor  = editor.textCursor()
            ln      = cursor.blockNumber() + 1
            col     = cursor.columnNumber() + 1

            # Scroll position
            scrollbar = editor.verticalScrollBar()
            scroll_y  = scrollbar.value() if scrollbar else 0

            # Get or create a stable ID for this tab
            tab_widget = tabs.widget(i)
            tab_id = getattr(tab_widget, "_session_id", None)
            if tab_id is None:
                tab_id = uuid.uuid4().hex
                tab_widget._session_id = tab_id

            # Write content to temp file for unsaved or modified tabs
            temp_rel = None
            if file_path is None or modified:
                temp_rel = os.path.join("tabs", f"{tab_id}.txt")
                temp_abs = os.path.join(_appdata_dir(), "session", temp_rel)
                _atomic_write(temp_abs, content)

            tabs_meta.append({
                "id":        tab_id,
                "label":     label,
                "file_path": file_path,
                "temp_file": temp_rel,
                "modified":  modified,
                "cursor":    [ln, col],
                "scroll_y":  scroll_y,
            })

        meta = {
            "version":      2,
            "active_index": tabs.currentIndex(),
            "tabs":         tabs_meta,
        }

        _atomic_write(_meta_path(), json.dumps(meta, indent=2))

    # -- Restore -------------------------------------------------------------

    def restore(self, window: "MainWindow", force: bool = False) -> None:
        """
        Re-open all tabs from the previous session.
        Restores content, cursor position, and scroll position.
        Does NOT overwrite any user files.
        """
        if not os.path.exists(_meta_path()):
            return

        try:
            with open(_meta_path(), encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        tab_list = meta.get("tabs", [])
        if not tab_list:
            return

        active = meta.get("active_index", 0)

        for entry in tab_list:
            label     = entry.get("label", "Untitled")
            file_path = entry.get("file_path")
            temp_rel  = entry.get("temp_file")
            modified  = entry.get("modified", False)
            cursor    = entry.get("cursor", [1, 1])
            scroll_y  = entry.get("scroll_y", 0)
            tab_id    = entry.get("id", uuid.uuid4().hex)

            # Determine content to load
            content   = ""
            used_temp = False

            # Prefer temp file (has unsaved edits)
            if temp_rel:
                temp_abs = os.path.join(_appdata_dir(), "session", temp_rel)
                if os.path.exists(temp_abs):
                    try:
                        with open(temp_abs, encoding="utf-8", errors="replace") as f:
                            content   = f.read()
                        used_temp = True
                    except (OSError, UnicodeDecodeError):
                        pass

            # Fall back to the original file if temp not available
            if not used_temp and file_path and os.path.exists(file_path):
                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except (OSError, UnicodeDecodeError):
                    pass

            # Open the tab
            editor = window._tabs.new_tab(
                file_path      = file_path if (file_path and not used_temp) else None,
                content        = content,
                label_override = label,
            )

            # Tag widget with session ID
            idx = window._tabs.index_of_editor(editor)
            w   = window._tabs.widget(idx)
            if w:
                w._session_id = tab_id

            # Mark as modified if it was
            if modified:
                editor.document().setModified(True)

            # Restore cursor position
            from PyQt6.QtGui import QTextCursor
            target_line = max(0, cursor[0] - 1)
            target_col  = max(0, cursor[1] - 1)
            block = editor.document().findBlockByLineNumber(target_line)
            if block.isValid():
                c = QTextCursor(block)
                c.movePosition(
                    QTextCursor.MoveOperation.Right,
                    QTextCursor.MoveMode.MoveAnchor,
                    min(target_col, block.length() - 1),
                )
                editor.setTextCursor(c)

            # Restore scroll
            sb = editor.verticalScrollBar()
            if sb:
                sb.setValue(scroll_y)

        # Restore active tab
        count = window._tabs.count()
        if count > 0:
            window._tabs.setCurrentIndex(min(active, count - 1))

    def restore_last_session(self, window: "MainWindow") -> bool:
        """Alias for restore() — returns True if session data existed."""
        if not os.path.exists(_meta_path()):
            return False
        self.restore(window)
        return True

    # -- Discard -------------------------------------------------------------

    def discard(self) -> None:
        """Delete all session temp files and metadata (user chose not to restore)."""
        try:
            if os.path.exists(_meta_path()):
                os.remove(_meta_path())
            tabs_dir = os.path.join(_appdata_dir(), "session", "tabs")
            if os.path.isdir(tabs_dir):
                for fname in os.listdir(tabs_dir):
                    try:
                        os.remove(os.path.join(tabs_dir, fname))
                    except OSError:
                        pass
        except OSError:
            pass
