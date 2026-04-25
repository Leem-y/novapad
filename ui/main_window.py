"""
ui/main_window.py  –  NovaPad Main Window
==========================================
Assembles menus, toolbar, tab manager, find bar, and status bar.

Shortcut strategy (eliminates ALL conflicts)
--------------------------------------------
Every shortcut is registered on exactly ONE QAction, on the QMainWindow,
with ShortcutContext = WindowShortcut (the default).  No shortcut is ever
registered on a child widget separately.  The find bar uses no shortcuts;
it exposes named methods (find_next, find_prev) which are called by the
actions wired here.

F3  and Shift+F3 are handled via a QShortcut (not QAction) because they
need to call methods on the bar, not trigger menu items.
"""

from __future__ import annotations

import datetime
import os
import tempfile

from PyQt6.QtCore    import QEvent, QObject, QSettings, Qt, QTimer
from PyQt6.QtGui     import QAction, QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QSplitter, QStatusBar, QSystemTrayIcon, QToolBar, QVBoxLayout, QWidget,
)

from assets.icons    import get_app_icon, get_icon, toolbar_color
from core.editor     import CodeEditor, make_arrow_cursor
from core.tab_manager import TabManager
from core.app_context import AppContext
from ui.find_bar       import FindBar
from ui.minimap        import Minimap
from ui.scrollbar_overlay import ScrollbarOverlay
from ui.command_palette import CommandPalette
from ui.format_toolbar import FormatToolbar
from ui.goto_line      import GotoLineBar
from ui.bookmarks      import BookmarkManager
from ui.theme        import ThemeManager, THEME_NAMES, DEFAULT_THEME, apply_titlebar_color
from ui.theme_picker import ThemePicker, ThemeTransitionOverlay
from ui.dialogs      import themed_info, themed_error, themed_question
from utils.session_controller import SessionController
from utils import daily_notes
from ui.date_picker import pick_date
from utils.system_cursor import enable_novapad_system_cursors, disable_novapad_system_cursors
from ui.signature_manager import SignatureManagerDialog
from utils.signatures import load_items as load_signature_items, save_items as save_signature_items, SignatureItem
from utils.windows_global_hotkeys import GlobalHotkey, WindowsGlobalHotkeyManager
from utils.windows_input import send_ctrl_v, last_paste_info as win_last_paste_info
from utils.windows_clipboard import (
    set_clipboard_text as win_set_clipboard_text,
    last_error as win_clip_last_error,
    last_stage as win_clip_last_stage,
)


FILE_FILTER = (
    "All Files (*);;"
    "Text Files (*.txt);;"
    "Python Files (*.py);;"
    "JavaScript (*.js *.ts *.jsx *.tsx);;"
    "HTML (*.html *.htm);;"
    "CSS (*.css *.scss);;"
    "JSON (*.json);;"
    "Markdown (*.md);;"
    "XML (*.xml *.svg)"
)



def _smart_title_case(text: str) -> str:
    """
    Title case that handles hyphenated words, apostrophes, and special chars.
    Each word (split on whitespace) has its first letter capitalized.
    Words after hyphens also get capitalized. Apostrophes don't start new words.
    """
    import re
    result = []
    for word in re.split(r'(\s+)', text):
        if not word or word.isspace():
            result.append(word)
            continue
        # Capitalize after hyphens within a word
        parts = word.split("-")
        capped = "-".join(
            p[0].upper() + p[1:].lower() if p else p
            for p in parts
        )
        result.append(capped)
    return "".join(result)

class _AppCursorFilter(QObject):
    """
    App-level event filter: every top-level NovaPad window that becomes
    visible automatically receives the themed arrow cursor.
    This covers dialogs, command palette, theme picker, about box, etc.
    """
    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.Show and
                isinstance(obj, QWidget) and obj.isWindow()):
            from ui.theme import ThemeManager
            t = ThemeManager.current()
            obj.setCursor(make_arrow_cursor(t["accent"], t.get("is_dark", True)))
        return False   # never consume events


class MainWindow(QMainWindow):
    """NovaPad main window."""

    def __init__(self, context: AppContext | None = None, session=None):
        super().__init__()
        self._ctx = context
        if self._ctx is None:
            # Backwards-compatible fallback (e.g. MainWindow() from older callers)
            self._settings = QSettings("NovaPad", "NovaPad")
            self._session = session
            self._theme = self._settings.value("theme", DEFAULT_THEME, str)
            self._theme_apply = lambda name: ThemeManager.apply(QApplication.instance(), name)
        else:
            self._settings = self._ctx.settings
            self._session = self._ctx.session
            self._theme = self._ctx.theme.name
            self._theme_apply = self._ctx.theme.apply

        self._word_wrap = self._settings.value("word_wrap",    False, bool)
        self._show_ln   = self._settings.value("line_numbers", True,  bool)
        self._auto_save = self._settings.value("auto_save",    True,  bool)
        self._system_cursor = self._settings.value("system_cursor_global", False, bool)
        self._autosave_connected: set[int] = set()
        self._autosave_timers: dict[int, QTimer] = {}
        self._autosave_writing: set[int] = set()
        self._autosave_debounce_ms = 600

        # Signatures
        self._sig_items: list[SignatureItem] = []
        self._sig_dialog: SignatureManagerDialog | None = None
        self._sig_hotkeys = WindowsGlobalHotkeyManager(self._on_signature_hotkey)
        self._sig_hotkey_sink: QWidget | None = None
        self._sig_autopaste = bool(self._settings.value("signatures.autopaste", True, bool))

        self._tray: QSystemTrayIcon | None = None
        self._quit_requested = False

        # Apply theme FIRST so every subsequent build step uses the correct colors
        self._theme_apply(self._theme)

        self._setup_window()
        self._build_central()
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()
        self._build_shortcuts()

        # Re-apply theme to elements built after the initial apply
        self._findbar._apply_theme()
        _ti = ThemeManager.current()
        self._minimap_wrapper.setStyleSheet(f"background: {_ti['bg_tab_bar']};")
        # Drop shadow falls leftward onto the editor (extends outside widget bounds)
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        _shadow = QGraphicsDropShadowEffect(self._minimap_wrapper)
        _shadow.setBlurRadius(18)
        _shadow.setOffset(-8, 0)
        _shadow.setColor(QColor(0, 0, 0, 70))
        self._minimap_wrapper.setGraphicsEffect(_shadow)
        # Rebuild toolbar icons now that all state is initialised
        self._refresh_toolbar_icons()
        self._propagate_settings()

        # Observe theme changes (single source of truth when context is used)
        if self._ctx is not None:
            self._ctx.theme.theme_changed.connect(self._on_theme_changed)

        # Install app-level cursor filter ONCE so every future NovaPad
        # window automatically gets the themed arrow cursor on show.
        self._cursor_filter = _AppCursorFilter(self)
        QApplication.instance().installEventFilter(self._cursor_filter)
        self._apply_themed_cursors()

        # Global hotkeys: use thread message queue + native event filter (Windows only).
        try:
            QApplication.instance().installNativeEventFilter(self._sig_hotkeys)
        except Exception:
            pass

        # Autosave-on-edit is wired per editor (debounced). No periodic sweep timer.

        # Session autosave wiring (debounced + periodic), owned by MainWindow
        if self._session is not None:
            self._session_controller = SessionController(self._session, self._tabs, self)

        # Status refresh
        st = QTimer(self)
        st.timeout.connect(self._refresh_status)
        st.start(400)

        # Restore system cursors on quit (if enabled)
        try:
            QApplication.instance().aboutToQuit.connect(self._ensure_system_cursor_restored)
        except Exception:
            pass

        # Apply on startup if previously enabled
        if self._system_cursor:
            self._apply_system_cursor(True)

        # Signatures: load + register after event loop starts (avoid early Win32 calls).
        self._sig_items = load_signature_items(self._settings)
        QTimer.singleShot(0, self._init_signature_hotkeys)

        self._install_system_tray()

    # ── Public surface (for main.py / external callers) ────────────────────

    def quit_fully(self) -> None:
        """Exit the process for good (File → Exit, updater, etc.). Bypasses tray."""
        self._quit_requested = True
        self.close()

    def tabs(self) -> TabManager:
        return self._tabs

    def active_editor(self) -> CodeEditor | None:
        return self._tabs.current_editor() if hasattr(self, "_tabs") else None

    def open_paths(self, paths: list[str]) -> None:
        """Open a list of paths in new tabs (used for CLI file args)."""
        for p in paths:
            self.open_file(p)

    def remove_default_empty_tab_if_unused(self) -> bool:
        return self._tabs.remove_default_empty_tab_if_unused()

    def open_daily_note(self, date: datetime.date | None = None, focus: bool = True) -> str | None:
        """
        Open (or create) the daily note for the given date in a tab.
        Returns the note path on success.
        """
        date = date or datetime.date.today()
        path = daily_notes.note_path_for_date(date)
        try:
            daily_notes.ensure_note_exists(path, date)
        except OSError as err:
            themed_error(self, "Daily Notes", str(err))
            return None

        # Activate if already open
        for e in self._tabs.all_editors():
            if e.file_path == path:
                if focus:
                    self._tabs.setCurrentIndex(self._tabs.index_of_editor(e))
                    e.setFocus()
                return path

        # Otherwise open as a normal file-backed tab
        self.open_file(path)
        if focus:
            e = self._tabs.current_editor()
            if e:
                e.setFocus()
        return path

    def _pick_daily_note_date(self):
        chosen = pick_date(self, initial=datetime.date.today())
        if chosen:
            self.open_daily_note(chosen, focus=True)

    # ── Theme integration ─────────────────────────────────────────────────

    def _on_theme_changed(self, name: str, tokens: dict, is_dark: bool):
        # Keep local theme name consistent (used by minimap/theme picker UI)
        self._theme = name
        self._apply_dwm_titlebar()
        self._tabs.set_dark_mode(is_dark)
        self._refresh_toolbar_icons()
        self._findbar.refresh_icons()
        if hasattr(self, "_minimap"):
            self._minimap.set_theme(name)
            self._minimap_wrapper.setStyleSheet(f"background: {tokens['bg_tab_bar']};")
        self._findbar._apply_theme()
        # Force every editor to repaint its theme-dependent state
        for e in self._tabs.all_editors():
            e.set_dark_mode(is_dark)
            e.apply_theme()
            e.viewport().update()
        self._propagate_settings()
        self.setWindowIcon(get_app_icon())
        self._apply_themed_cursors()

        # If the user enabled system-wide cursors, refresh them to match the new theme.
        try:
            if bool(self._system_cursor):
                self._apply_system_cursor(True)
        except Exception:
            pass

    # ── Window ────────────────────────────────────────────────────────────

    def _apply_themed_cursors(self):
        """Set accent-colored arrow cursor on all NovaPad widgets."""
        t       = ThemeManager.current()
        acc     = t["accent"]
        is_dark = t.get("is_dark", True)
        arrow   = make_arrow_cursor(acc, is_dark)

        for w in QApplication.topLevelWidgets():
            w.setCursor(arrow)

        # Child widgets that Qt won't inherit through because they override
        # the cursor internally (scroll areas, custom-paint widgets, etc.)
        for attr in ("_minimap", "_minimap_wrapper", "_tabs", "_lbl_eol",
                     "_lbl_zoom", "_findbar"):
            w = getattr(self, attr, None)
            if w is not None:
                w.setCursor(arrow)
                # Also cover any viewport child (QAbstractScrollArea)
                vp = getattr(w, "viewport", None)
                if callable(vp):
                    vp().setCursor(arrow)

    def _setup_window(self):
        self.setWindowTitle("NovaPad")
        self._transition_overlay = ThemeTransitionOverlay(self)
        # Delay icon + titlebar color so theme tokens are fully initialised
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self._apply_startup_chrome)
        w = self._settings.value("win_w", 1100, int)
        h = self._settings.value("win_h", 720,  int)
        self.resize(w, h)
        x = self._settings.value("win_x", -1, int)
        y = self._settings.value("win_y", -1, int)
        if x >= 0 and y >= 0:
            self.move(x, y)
        if self._settings.value("win_maximized", False, bool):
            self.showMaximized()

    # ── Central area ──────────────────────────────────────────────────────

    def _build_central(self):
        container = QWidget(self)
        lay       = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Tabs + minimap side by side
        self._tabs    = TabManager(self)
        self._minimap = Minimap()
        self._minimap.set_theme(self._theme if hasattr(self, '_theme') else 'NovaPad Dark')
        self._minimap_visible = self._settings.value("minimap", True, bool)
        # Wrap the minimap so it starts below the tab bar
        from PyQt6.QtCore import QObject, QEvent
        self._minimap_wrapper = QWidget()
        self._minimap_wrapper.setFixedWidth(self._minimap.WIDTH)
        self._minimap_wrapper.setAutoFillBackground(True)
        _mm_lay = QVBoxLayout(self._minimap_wrapper)
        _mm_lay.setContentsMargins(0, 0, 0, 0)
        _mm_lay.setSpacing(0)
        _mm_lay.addWidget(self._minimap)

        class _TabBarWatcher(QObject):
            def __init__(self_, wrapper, tabbar):
                super().__init__(tabbar)
                self_._w = wrapper
                tabbar.installEventFilter(self_)
            def eventFilter(self_, obj, event):
                if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                    self_._w.layout().setContentsMargins(0, obj.height(), 0, 0)
                return False

        self._tabbar_watcher = _TabBarWatcher(self._minimap_wrapper, self._tabs.tabBar())
        self._minimap_wrapper.setVisible(self._minimap_visible)

        editor_row = QHBoxLayout()
        editor_row.setContentsMargins(0, 0, 0, 0)
        editor_row.setSpacing(0)
        editor_row.addWidget(self._tabs)
        editor_row.addWidget(self._minimap_wrapper)

        editor_container = QWidget()
        editor_container.setLayout(editor_row)

        self._findbar = FindBar(self)
        self._findbar.setVisible(False)
        # Wire minimap to receive search result positions
        if hasattr(self, "_minimap"):
            self._findbar.set_minimap(self._minimap)

        lay.addWidget(editor_container)
        lay.addWidget(self._findbar)
        self.setCentralWidget(container)

        # Seed with one empty tab
        self._tabs.new_tab()

        self._tabs.tab_changed.connect(self._on_tab_changed)
        self._tabs.title_changed.connect(self._update_title)
        self._tabs.modification_changed.connect(lambda _: self._update_title())
        self._tabs.set_save_handler(lambda editor: self.save_file(editor=editor))

        # Bookmark manager (shared across all tabs)
        self._bookmarks = BookmarkManager()

        # Go-to-line bar
        self._goto_bar = GotoLineBar(self)
        self._goto_bar.setVisible(False)
        lay.addWidget(self._goto_bar)

        # Sync minimap/findbar/etc. to the initial tab (created before signal connection)
        e = self._tabs.current_editor()
        if e:
            self._on_tab_changed(e)

    # ── Menu bar ──────────────────────────────────────────────────────────

    def _apply_startup_chrome(self):
        """Apply themed icon and title bar color after the event loop starts."""
        self.setWindowIcon(get_app_icon())
        self._apply_dwm_titlebar()

    def _apply_dwm_titlebar(self) -> None:
        """Windows 11: tint native caption/border to match QMenuBar (bg_toolbar)."""
        if not bool(self._settings.value("titlebar.match_windows_dwm", True, bool)):
            return
        t = ThemeManager.current()
        fg = t.get("fg_tab_active") or t.get("fg_primary")
        apply_titlebar_color(
            self,
            t["bg_toolbar"],
            is_dark=bool(t.get("is_dark", True)),
            fg_hex=str(fg) if fg else None,
        )

    def _build_menu(self):
        mb = self.menuBar()

        # ── File ──────────────────────────────────────────────────────
        fm = mb.addMenu("&File")
        self._act(fm, "&New Tab",          self.new_file,       "Ctrl+T")
        self._act(fm, "New Tab (&Alt)",    self.new_file,       "Ctrl+N")
        self._act(fm, "New &Window",       self.new_window,     "Ctrl+Shift+N")
        fm.addSeparator()
        self._act(fm, "&Open…",            self.open_file,      "Ctrl+O")
        self._recent_menu = fm.addMenu("Recent &Files")
        self._rebuild_recent_menu()
        fm.addSeparator()
        self._act(fm, "&Save",             lambda _: self.save_file(),    "Ctrl+S")
        self._act(fm, "Save &As…",         lambda _: self.save_file_as(), "Ctrl+Shift+S")
        self._act(fm, "Save Al&l",         self.save_all,       "Ctrl+Alt+S")
        fm.addSeparator()
        self._act(fm, "&Close Tab",        self._close_current,    "Ctrl+W")
        fm.addSeparator()
        self._act(fm, "Restore Last &Session", self._restore_session, None)
        fm.addSeparator()
        self._act(fm, "&Print…",           self._print_doc,     "Ctrl+P")
        fm.addSeparator()
        self._act(fm, "E&xit",             self.quit_fully,     None)

        # ── Edit ──────────────────────────────────────────────────────
        em = mb.addMenu("&Edit")
        self._act(em, "&Undo",             self._undo,          "Ctrl+Z")
        self._act(em, "&Redo",             self._redo,          "Ctrl+Y")
        em.addSeparator()
        self._act(em, "Cu&t",              self._cut,           "Ctrl+X")
        self._act(em, "&Copy",             self._copy,          "Ctrl+C")
        self._act(em, "&Paste",            self._paste,         "Ctrl+V")
        self._act(em, "Select &All",       self._select_all,    "Ctrl+A")
        em.addSeparator()
        # NOTE: Ctrl+F / Ctrl+H are ONLY registered here, nowhere else.
        self._act(em, "&Find…",            self.show_find,      "Ctrl+F")
        self._act(em, "Find and &Replace…",self.show_replace,   "Ctrl+H")
        em.addSeparator()
        self._act(em, "Insert &Timestamp",  self.insert_timestamp, "F5")
        self._act(em, "&Duplicate Line",       self._duplicate_line,       "Ctrl+D")
        self._act(em, "Select &All Occurrences", self._select_all_occurrences, "Ctrl+Shift+L")
        self._act(em, "Toggle &Comment",    self._toggle_comment,  "Ctrl+/")

        # ── View ──────────────────────────────────────────────────────
        vm = mb.addMenu("&View")
        vm.addSeparator()
        self._act_wrap = self._checkable_act(
            vm, "&Word Wrap", self._toggle_word_wrap,
            "Alt+Z", self._word_wrap
        )
        self._act_ln = self._checkable_act(
            vm, "&Line Numbers", self._toggle_line_numbers,
            "Ctrl+Shift+G", self._show_ln
        )
        self._act_mode = self._checkable_act(
            vm, "&Code Mode", self._toggle_mode,
            "Ctrl+Shift+M", False
        )
        vm.addSeparator()
        self._act(vm, "&Fullscreen / Focus Mode", self._toggle_distraction_free, "F11")
        self._checkable_act(vm, "&Minimap", self._toggle_minimap, "Ctrl+Shift+M", self._minimap_visible)
        tm = vm.addMenu("&Theme")
        for _tn in THEME_NAMES:
            _a = tm.addAction(_tn)
            _a.triggered.connect(lambda _, n=_tn: self._apply_theme(n))
        vm.addSeparator()
        self._act(vm, "Zoom &In",          self._zoom_in,       "Ctrl+=")
        self._act(vm, "Zoom &Out",         self._zoom_out,      "Ctrl+-")
        self._act(vm, "&Reset Zoom",       self._zoom_reset,    "Ctrl+0")

        # ── Format ────────────────────────────────────────────────────
        fmt = mb.addMenu("F&ormat")
        self._act(fmt, "&Indent Lines",      self._indent,                    "Ctrl+]")
        self._act(fmt, "&Unindent Lines",    self._unindent,                  "Ctrl+[")
        self._act(fmt, "Move Line &Up",      self._move_line_up,              "Alt+Up")
        self._act(fmt, "Move Line &Down",    self._move_line_down,            "Alt+Down")
        fmt.addSeparator()
        self._act(fmt, "&UPPERCASE",         lambda: self._case("upper"),     "Ctrl+Shift+U")
        self._act(fmt, "&lowercase",         lambda: self._case("lower"),     None)
        self._act(fmt, "&Title Case",        lambda: self._case("title"),     None)
        fmt.addSeparator()
        self._act(fmt, "&Sort Lines",        self._sort_lines,                None)
        self._act(fmt, "Remove &Duplicates", self._remove_duplicates,         None)
        self._act(fmt, "&Join Lines",        self._join_lines,                None)
        fmt.addSeparator()
        self._act(fmt, "Trim &Trailing Whitespace", self._trim_whitespace,    None)

        # ── Session ───────────────────────────────────────────────────
        sm = mb.addMenu("&Session")
        self._act(sm, "&Restore Last Session", self._restore_last_session, None)
        sm.addSeparator()
        self._act(sm, "&Save Session Now",     self._save_session_now,     None)

        # ── Navigate ──────────────────────────────────────────────────
        nm = mb.addMenu("&Navigate")
        self._act(nm, "&Go to Line…",           self.show_goto_line,      "Ctrl+G")
        self._act(nm, "Add Cursor &Above",       self._cursor_above,       "Ctrl+Alt+Up")
        self._act(nm, "Add Cursor &Below",       self._cursor_below,       "Ctrl+Alt+Down")
        nm.addSeparator()
        self._act(nm, "Toggle &Bookmark",     self.toggle_bookmark,      "Ctrl+F2")
        self._act(nm, "Next Bookmark",        self.goto_next_bookmark,   "F2")
        self._act(nm, "Previous Bookmark",    self.goto_prev_bookmark,   "Shift+F2")
        nm.addSeparator()
        self._act(nm, "Next Tab",             self._next_tab,            "Ctrl+Tab")
        self._act(nm, "Previous Tab",         self._prev_tab,            "Ctrl+Shift+Tab")

        # ── Tools ──────────────────────────────────────────────────────
        tools = mb.addMenu("&Tools")
        self._act(tools, "&Signature Manager…", self._open_signature_manager, None)

        # ── Help ──────────────────────────────────────────────────────
        hm = mb.addMenu("&Help")
        self._act(hm, "&About NovaPad…",   self._about,         "F1")
        self._act(hm, "&Command Palette",  self._show_palette,  "Ctrl+P")


    @staticmethod
    def _act(menu, label: str, slot, shortcut: str | None) -> QAction:
        a = QAction(label, menu.parent() or menu)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot)
        menu.addAction(a)
        return a

    @staticmethod
    def _checkable_act(menu, label: str, slot, shortcut: str | None,
                       checked: bool) -> QAction:
        a = QAction(label, menu.parent() or menu)
        a.setCheckable(True)
        a.setChecked(checked)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.toggled.connect(slot)
        menu.addAction(a)
        return a

    # ── Toolbar ───────────────────────────────────────────────────────────

    def _build_toolbar(self):
        self._toolbar = QToolBar("Main", self)
        self._toolbar.setMovable(False)
        self._toolbar.setFloatable(False)
        self.addToolBar(self._toolbar)
        self._refresh_toolbar_icons()

    def _refresh_toolbar_icons(self):
        """Rebuild toolbar actions with correctly-coloured icons."""
        self._toolbar.clear()
        dark = ThemeManager.is_dark()
        ic   = lambda name: get_icon(name, toolbar_color(dark), 16)

        def btn(icon_name: str, tip: str, slot):
            a = QAction(ic(icon_name), "", self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            self._toolbar.addAction(a)
            return a

        btn("new_file",  "New (Ctrl+N)",          self.new_file)
        btn("open_file", "Open (Ctrl+O)",          self.open_file)
        btn("save",      "Save (Ctrl+S)",          self.save_file)
        self._toolbar.addSeparator()
        self._tb_autosave = QAction(ic("autosave"), "AutoSave", self)
        self._tb_autosave.setToolTip("AutoSave (write edits to disk)")
        self._tb_autosave.setCheckable(True)
        self._tb_autosave.setChecked(bool(self._auto_save))
        self._tb_autosave.toggled.connect(self._toggle_autosave)
        self._toolbar.addAction(self._tb_autosave)
        self._toolbar.addSeparator()
        btn("undo",      "Undo (Ctrl+Z)",          self._undo)
        btn("redo",      "Redo (Ctrl+Y)",          self._redo)
        self._toolbar.addSeparator()
        btn("cut",       "Cut (Ctrl+X)",           self._cut)
        btn("copy",      "Copy (Ctrl+C)",          self._copy)
        btn("paste",     "Paste (Ctrl+V)",         self._paste)
        self._toolbar.addSeparator()
        btn("search",    "Find (Ctrl+F)",          self.show_find)
        btn("replace",   "Find & Replace (Ctrl+H)",self.show_replace)
        btn("calendar",  "Daily Notes (Pick Date)", self._pick_daily_note_date)
        hidden = getattr(self, '_timestamps_hidden', False)
        self._tb_insert_ts = btn("clock", "Insert Timestamp (F5)", self.insert_timestamp)
        self._tb_insert_ts.setEnabled(not hidden)
        eye_icon = "eye_off" if hidden else "eye"
        self._tb_toggle_ts = btn(eye_icon, "Hide Timestamps" if not hidden else "Show Timestamps",
                                 self.toggle_timestamps)
        self._toolbar.addSeparator()

        # Theme picker button (paintbrush icon)
        self._tb_theme = QAction(ic("theme"), "", self)
        self._tb_theme.setToolTip("Choose Theme")
        self._tb_theme.setCheckable(False)
        self._tb_theme.setChecked(dark)
        self._tb_theme.triggered.connect(self._show_theme_picker)
        self._toolbar.addAction(self._tb_theme)

        # Word-wrap toggle
        self._tb_wrap = QAction(ic("wrap"), "", self)
        self._tb_wrap.setToolTip("Toggle Word Wrap (Alt+Z)")
        self._tb_wrap.setCheckable(True)
        self._tb_wrap.setChecked(self._word_wrap)
        self._tb_wrap.triggered.connect(self._toggle_word_wrap)
        self._toolbar.addAction(self._tb_wrap)

        # Line-numbers toggle
        self._tb_ln = QAction(ic("hash"), "", self)
        self._tb_ln.setToolTip("Toggle Line Numbers (Ctrl+Shift+G)")
        self._tb_ln.setCheckable(True)
        self._tb_ln.setChecked(self._show_ln)
        self._tb_ln.triggered.connect(self._toggle_line_numbers)
        self._toolbar.addAction(self._tb_ln)

        # Formatting toolbar (second row)
        if not hasattr(self, "_fmt_toolbar"):
            self._fmt_toolbar = FormatToolbar(self)
            self.addToolBarBreak()
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._fmt_toolbar)
        self._fmt_toolbar.set_dark(dark)
        self._fmt_toolbar.set_editor(self._tabs.current_editor())

    # ── Status bar ────────────────────────────────────────────────────────

    def _build_status_bar(self):
        sb = QStatusBar(self)
        self.setStatusBar(sb)
        self._lbl_pos    = QLabel("Ln 1,  Col 1")
        self._lbl_words  = QLabel("0 words")
        self._lbl_chars  = QLabel("0 chars")
        self._lbl_lang   = QLabel("Plain Text")
        self._lbl_enc    = QLabel("UTF-8")
        self._lbl_eol    = QLabel("CRLF")
        self._lbl_zoom   = QLabel("100%")
        self._lbl_mod    = QLabel("")
        for lbl in (self._lbl_pos, self._lbl_words, self._lbl_chars,
                    self._lbl_lang, self._lbl_enc, self._lbl_eol,
                    self._lbl_zoom, self._lbl_mod):
            sb.addPermanentWidget(lbl)
        # Make EOL and zoom clickable
        self._lbl_eol.setCursor(Qt.CursorShape.ArrowCursor)
        self._lbl_eol.mousePressEvent  = lambda e: self._toggle_eol()
        self._lbl_zoom.setCursor(Qt.CursorShape.ArrowCursor)
        self._lbl_zoom.mousePressEvent = lambda e: self._zoom_reset()

    def _refresh_status(self):
        e = self._tabs.current_editor()
        if not e:
            return
        ln, col = e.cursor_position()
        self._lbl_pos.setText(f"Ln {ln},  Col {col}")
        cursor = e.textCursor()
        if cursor.hasSelection():
            from core.editor import _is_timestamp_block
            # Walk selected blocks, skipping timestamp lines.
            tmp = e.textCursor()
            tmp.setPosition(min(cursor.anchor(), cursor.position()))
            sel_end = max(cursor.anchor(), cursor.position())
            sel_lines = []
            while tmp.position() <= sel_end:
                blk = tmp.block()
                if not _is_timestamp_block(blk):
                    sel_lines.append(blk.text())
                if not tmp.movePosition(tmp.MoveOperation.NextBlock):
                    break
            sel   = "\n".join(sel_lines)
            words = len(sel.split()) if sel.strip() else 0
            chars = len(sel.replace("\n", ""))
            self._lbl_words.setText(f"{words:,} sel words")
            self._lbl_chars.setText(f"{chars:,} sel chars")
        else:
            text  = e.get_plain_export()
            words = len(text.split()) if text.strip() else 0
            chars = len(text.replace("\n", ""))
            self._lbl_words.setText(f"{words:,} words")
            self._lbl_chars.setText(f"{chars:,} chars")
        lang  = e.language.replace("javascript", "JavaScript").capitalize()
        self._lbl_lang.setText(lang if lang != "Plain" else "Plain Text")
        self._lbl_mod.setText("  ●" if e.document().isModified() else "")
        # Zoom level
        # pointSize() returns -1 for pixel-sized fonts; use fontMetrics instead
        base_h   = 18  # default font metrics height at 100%
        cur_h    = e.fontMetrics().height()
        zoom_pct = max(10, int(cur_h / base_h * 100))
        self._lbl_zoom.setText(f"{zoom_pct}%")
        # EOL detection
        text = e.toPlainText()
        if "\r\n" in text:
            self._lbl_eol.setText("CRLF")
        else:
            self._lbl_eol.setText("LF")

    # ── Shortcut wiring (F3 / Shift+F3) ──────────────────────────────────

    def _build_shortcuts(self):
        """
        F3 / Shift+F3, Ctrl+Tab, Ctrl+Shift+Tab use QShortcut (WindowShortcut)
        so they never conflict with child widget focus.
        """
        def _sc(key, slot):
            s = QShortcut(QKeySequence(key), self)
            s.setContext(Qt.ShortcutContext.WindowShortcut)
            s.activated.connect(slot)

        _sc("F3",       self._find_next_shortcut)
        _sc("Shift+F3", self._find_prev_shortcut)

    def _find_next_shortcut(self):
        if self._findbar.isVisible():
            self._findbar.find_next()
        else:
            self.show_find()

    def _find_prev_shortcut(self):
        if self._findbar.isVisible():
            self._findbar.find_prev()

    # ── Tab navigation ────────────────────────────────────────────────────

    def _next_tab(self):
        n = self._tabs.count()
        if n > 1:
            self._tabs.setCurrentIndex((self._tabs.currentIndex() + 1) % n)

    def _prev_tab(self):
        n = self._tabs.count()
        if n > 1:
            self._tabs.setCurrentIndex((self._tabs.currentIndex() - 1) % n)

    # ── Go to line ────────────────────────────────────────────────────────

    def show_goto_line(self):
        e = self._tabs.current_editor()
        if e:
            self._goto_bar.set_editor(e)
        self._goto_bar.show_bar()

    # ── Bookmarks ─────────────────────────────────────────────────────────

    def toggle_bookmark(self):
        e = self._tabs.current_editor()
        if e:
            self._bookmarks.toggle(e)
            e._line_num_area.update()
            e.update()
            self._minimap.update()

    def goto_next_bookmark(self):
        e = self._tabs.current_editor()
        if e:
            self._bookmarks.goto_next(e)

    def goto_prev_bookmark(self):
        e = self._tabs.current_editor()
        if e:
            self._bookmarks.goto_prev(e)

    # ── File operations ───────────────────────────────────────────────────

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        recents = self._settings.value("recent_files", [], list) or []
        if not recents:
            a = self._recent_menu.addAction("(none)")
            a.setEnabled(False)
            return
        for path in recents[:10]:
            a = self._recent_menu.addAction(os.path.basename(path))
            a.setToolTip(path)
            a.triggered.connect(lambda _, p=path: self.open_file(p))
        self._recent_menu.addSeparator()
        self._recent_menu.addAction("Clear Recent Files").triggered.connect(self._clear_recent)

    def _add_recent(self, path: str):
        recents = self._settings.value("recent_files", [], list) or []
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        self._settings.setValue("recent_files", recents[:10])
        self._rebuild_recent_menu()

    def _clear_recent(self):
        self._settings.setValue("recent_files", [])
        self._rebuild_recent_menu()

    def new_file(self):
        self._tabs.new_tab()
        self._apply_settings_to(self._tabs.current_editor())

    def new_window(self):
        w = MainWindow()
        w.show()

    def open_file(self, path: str | None = None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open File", "", FILE_FILTER)
        if not path:
            return
        # Activate tab if already open
        for e in self._tabs.all_editors():
            if e.file_path == path:
                self._tabs.setCurrentIndex(self._tabs.index_of_editor(e))
                return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as err:
            themed_error(self, "Error", str(err))
            return
        editor = self._tabs.new_tab(file_path=path, content="")
        editor.load_content(content, path)
        self._apply_settings_to(editor)
        self._wire_autosave(editor)
        editor.set_bookmark_manager(self._bookmarks)
        self._add_recent(path)
        if hasattr(self, "_fmt_toolbar"):
            self._fmt_toolbar.set_editor(editor)
        if hasattr(self, "_goto_bar"):
            self._goto_bar.set_editor(editor)
        if hasattr(self, "_minimap"):
            self._minimap.set_editor(editor)
        self._update_title()

    def save_file(self, editor: CodeEditor | None = None) -> bool:
        # QAction.triggered passes a boolean "checked" argument; ignore it.
        if isinstance(editor, bool):
            editor = None
        if editor is None:
            editor = self._tabs.current_editor()
        if editor is None:
            return False
        if not editor.file_path:
            return self.save_file_as(editor=editor)
        return self._write(editor, editor.file_path)

    def save_file_as(self, editor: CodeEditor | None = None) -> bool:
        # QAction.triggered passes a boolean "checked" argument; ignore it.
        if isinstance(editor, bool):
            editor = None
        if editor is None:
            editor = self._tabs.current_editor()
        if editor is None:
            return False
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", editor.file_path or "", FILE_FILTER
        )
        if not path:
            return False
        return self._write(editor, path)

    def save_all(self):
        for e in self._tabs.all_editors():
            if e.document().isModified():
                self.save_file(editor=e)

    def _write(self, editor: CodeEditor, path: str) -> bool:
        try:
            # Atomic write in the same directory (better for OneDrive / network shares):
            # write -> flush+fsync -> replace. This keeps the on-disk file in sync.
            dir_ = os.path.dirname(path) or "."
            os.makedirs(dir_, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".novapad.tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                    f.write(editor.get_content_for_save(path))
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        # Some filesystems/shares may not support fsync reliably.
                        pass
                os.replace(tmp, path)
            finally:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except OSError:
                    pass
            editor.file_path = path
            editor.document().setModified(False)
            self._tabs.refresh_tab_title(editor)
            self._update_title()
            return True
        except OSError as err:
            themed_error(self, "Save Error", str(err))
            return False

    def _toggle_autosave(self, checked: bool):
        self._auto_save = bool(checked)
        self._settings.setValue("auto_save", self._auto_save)
        # Ensure autosave is wired for any already-open editors
        for e in self._tabs.all_editors():
            self._wire_autosave(e)
        # If turning autosave ON, immediately flush any already-modified
        # file-backed documents so the user doesn't need to type again.
        if self._auto_save:
            for e in self._tabs.all_editors():
                if e.file_path and e.document().isModified():
                    # Schedule via single-shot so we don't re-enter during the toggle signal.
                    QTimer.singleShot(0, lambda ed=e: self._autosave_flush(ed))

    def _close_current(self):
        self._tabs.close_tab(self._tabs.currentIndex())

    # ── Edit operations ───────────────────────────────────────────────────

    def _undo(self):      self._call("undo")
    def _redo(self):      self._call("redo")
    def _cut(self):       self._call("cut")
    def _copy(self):      self._call("copy")
    def _paste(self):     self._call("paste")
    def _select_all(self):self._call("selectAll")

    def _call(self, method: str):
        e = self._tabs.current_editor()
        if e:
            getattr(e, method)()

    def insert_timestamp(self):
        if getattr(self, '_timestamps_hidden', False):
            return
        e = self._tabs.current_editor()
        if e:
            e.insert_timestamp()

    def toggle_timestamps(self):
        e = self._tabs.current_editor()
        if not e:
            return
        from core.editor import _is_timestamp_block
        hide = not getattr(self, '_timestamps_hidden', False)
        self._timestamps_hidden = hide
        doc   = e.document()
        block = doc.begin()
        while block.isValid():
            if _is_timestamp_block(block):
                block.setVisible(not hide)
            block = block.next()
        e.document().markContentsDirty(0, e.document().characterCount())
        e._guard_timestamp_cursor()
        e.viewport().update()
        e._line_num_area.update()
        # Update toolbar buttons to reflect new state
        dark = ThemeManager.is_dark()
        col  = toolbar_color(dark)
        if hasattr(self, '_tb_insert_ts'):
            self._tb_insert_ts.setEnabled(not hide)
        if hasattr(self, '_tb_toggle_ts'):
            eye_icon = "eye_off" if hide else "eye"
            self._tb_toggle_ts.setIcon(get_icon(eye_icon, col, 16))
            self._tb_toggle_ts.setToolTip("Show Timestamps" if hide else "Hide Timestamps")

    # ── Find / Replace ────────────────────────────────────────────────────

    def show_find(self):
        if self._findbar.isVisible():
            self._findbar.hide_bar()
            return
        self._attach_findbar()
        self._findbar.show_bar(replace=False)

    def show_replace(self):
        self._attach_findbar()
        self._findbar.show_bar(replace=True)

    def _attach_findbar(self):
        e = self._tabs.current_editor()
        if e:
            self._findbar.set_editor(e)

    # ── View / Theme ──────────────────────────────────────────────────────

    def toggle_dark_mode(self, checked: bool | None = None):
        # Legacy toggle: swap between NovaPad Dark and NovaPad Light
        new_theme = "NovaPad Light" if ThemeManager.is_dark() else "NovaPad Dark"
        self._apply_theme(new_theme)

    def _show_theme_picker(self):
        current = self._ctx.theme.name if self._ctx is not None else ThemeManager.current_name()
        picker = ThemePicker(current, self._apply_theme, self)
        # Position below the toolbar
        tb_rect = self._toolbar.geometry()
        gpos    = self.mapToGlobal(tb_rect.bottomLeft())
        picker.move(gpos.x() + 4, gpos.y() + 2)
        picker.exec()

    def _apply_theme(self, name: str):
        # 1. Capture current look BEFORE applying new theme
        if hasattr(self, "_transition_overlay"):
            self._transition_overlay.capture()

        # 2. Apply new theme instantly underneath the overlay (single path)
        if self._ctx is not None:
            self._ctx.theme.apply(name)
        else:
            # Legacy path without AppContext
            self._theme = name
            ThemeManager.apply(QApplication.instance(), name)
            self._on_theme_changed(name, ThemeManager.current(), ThemeManager.is_dark())

        # 3. Fade out the old-theme overlay to reveal new theme underneath
        if hasattr(self, "_transition_overlay"):
            self._transition_overlay.fade_out(duration_ms=300)

    def _toggle_word_wrap(self, checked: bool):
        self._word_wrap = checked
        self._tabs.set_word_wrap(checked)
        self._act_wrap.blockSignals(True)
        self._act_wrap.setChecked(checked)
        self._act_wrap.blockSignals(False)
        self._settings.setValue("word_wrap", checked)

    def _toggle_line_numbers(self, checked: bool):
        self._show_ln = checked
        self._tabs.toggle_line_numbers(checked)
        self._act_ln.blockSignals(True)
        self._act_ln.setChecked(checked)
        self._act_ln.blockSignals(False)
        self._settings.setValue("line_numbers", checked)

    def _toggle_mode(self, checked: bool):
        e = self._tabs.current_editor()
        if e:
            e.set_mode("code" if checked else "rich")

    def _zoom_in(self):    self._zoom(1)
    def _zoom_out(self):   self._zoom(-1)
    def _zoom_reset(self): self._zoom(0)

    def _zoom(self, direction: int):
        from PyQt6.QtCore import QTimer
        e = self._tabs.current_editor()
        if not e:
            return
        # Track zoom level as a step count on the editor itself
        old_step = getattr(e, "_zoom_steps", 0)
        if direction == 0:
            new_step = 0
        else:
            new_step = max(-8, min(16, old_step + direction))
        delta = new_step - old_step
        e._zoom_steps = new_step

        if delta == 0:
            return

        if e.is_rich_mode():
            # Rich mode: update document default font and re-stamp all blocks.
            # Defer the heavy block iteration so it runs after the current
            # event cycle, avoiding a repaint collision with setDefaultFont.
            from PyQt6.QtGui import QFontDatabase, QFont, QTextCharFormat, QTextCursor
            base_rich = getattr(e, "_rich_font_size", 12)
            new_rich  = max(6, base_rich + new_step)
            fam    = getattr(e, "_rich_font_family", "Segoe UI")
            styles = QFontDatabase.styles(fam)
            sname  = next((s for s in styles if s.lower() in ("regular", "normal")), None)
            rf = QFontDatabase.font(fam, sname, new_rich) if sname else QFont(fam, new_rich)
            e.document().setDefaultFont(rf)

            def _stamp_blocks():
                # Remember the block at the top of the viewport so zoom
                # doesn't cause the view to drift to a different line.
                from PyQt6.QtCore import QPoint
                anchor_block_num = e.cursorForPosition(QPoint(0, 0)).blockNumber()

                rfmt = QTextCharFormat()
                rfmt.setFontFamilies([fam])
                rfmt.setFontPointSize(float(new_rich))
                from core.editor import _is_timestamp_block
                doc    = e.document()
                cursor = QTextCursor(doc)
                cursor.beginEditBlock()
                block  = doc.begin()
                while block.isValid():
                    if not _is_timestamp_block(block):
                        cursor.setPosition(block.position())
                        cursor.setBlockCharFormat(rfmt)
                        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                            QTextCursor.MoveMode.KeepAnchor)
                        cursor.mergeCharFormat(rfmt)
                    block = block.next()
                cursor.endEditBlock()
                e.mergeCurrentCharFormat(rfmt)
                e._refresh_timestamp_colors()
                e.update_line_number_area_width()
                e._line_num_area.update()
                if hasattr(self, "_minimap"):
                    self._minimap._invalidate()

                # Restore scroll position: find the anchor block and set
                # the scrollbar so that block appears at the top of the viewport.
                anchor_block = doc.findBlockByNumber(anchor_block_num)
                if anchor_block.isValid():
                    block_top = int(doc.documentLayout().blockBoundingRect(anchor_block).top())
                    e.verticalScrollBar().setValue(block_top)

            QTimer.singleShot(0, _stamp_blocks)
        else:
            # Code mode: use Qt's built-in zoom API instead of setFont() directly.
            # zoomIn/zoomOut handle the internal layout state correctly and avoid
            # the access violation that manual setFont() causes mid-repaint.
            if delta > 0:
                e.zoomIn(delta)
            else:
                e.zoomOut(-delta)
            # Defer margin/gutter update so it runs after Qt finishes the layout.
            def _after_zoom():
                e.update_line_number_area_width()
                e._line_num_area.update()
                if hasattr(self, "_minimap"):
                    self._minimap._invalidate()
            QTimer.singleShot(0, _after_zoom)

    # ── Format ────────────────────────────────────────────────────────────

    def _duplicate_line(self):
        e = self._tabs.current_editor()
        if e:
            e._duplicate_line()

    def _toggle_comment(self):
        e = self._tabs.current_editor()
        if e:
            e._toggle_comment()

    def _move_line_up(self):
        e = self._tabs.current_editor()
        if e: e._move_line(-1)

    def _move_line_down(self):
        e = self._tabs.current_editor()
        if e: e._move_line(1)

    def _sort_lines(self):
        e = self._tabs.current_editor()
        if not e: return
        cursor = e.textCursor()
        if not cursor.hasSelection():
            return
        text  = cursor.selectedText().replace("\u2029", "\n")
        lines = sorted(text.splitlines())
        cursor.insertText("\n".join(lines))

    def _remove_duplicates(self):
        e = self._tabs.current_editor()
        if not e: return
        cursor = e.textCursor()
        if not cursor.hasSelection():
            return
        text  = cursor.selectedText().replace("\u2029", "\n")
        seen  = set()
        lines = []
        for line in text.splitlines():
            if line not in seen:
                seen.add(line)
                lines.append(line)
        cursor.insertText("\n".join(lines))

    def _join_lines(self):
        e = self._tabs.current_editor()
        if not e: return
        cursor = e.textCursor()
        if not cursor.hasSelection():
            return
        text = cursor.selectedText().replace("\u2029", " ")
        cursor.insertText(text)

    def _trim_whitespace(self):
        e = self._tabs.current_editor()
        if not e: return
        doc   = e.document()
        block = doc.begin()
        cursor = e.textCursor()
        cursor.beginEditBlock()
        while block.isValid():
            text = block.text()
            stripped = text.rstrip()
            if stripped != text:
                c = e.textCursor()
                c.setPosition(block.position() + len(stripped))
                c.movePosition(
                    c.MoveOperation.EndOfBlock,
                    c.MoveMode.KeepAnchor
                )
                c.removeSelectedText()
            block = block.next()
        cursor.endEditBlock()

    def _toggle_minimap(self, checked: bool):
        self._minimap_visible = checked
        self._minimap_wrapper.setVisible(checked)
        self._settings.setValue("minimap", checked)

    def _toggle_eol(self):
        """Toggle between CRLF and LF in the current document."""
        e = self._tabs.current_editor()
        if not e: return
        text = e.toPlainText()
        if "\r\n" in text:
            new_text = text.replace("\r\n", "\n")
            self._lbl_eol.setText("LF")
        else:
            new_text = text.replace("\n", "\r\n")
            self._lbl_eol.setText("CRLF")
        cursor = e.textCursor()
        cursor.select(cursor.SelectionType.Document)
        cursor.insertText(new_text)

    def _show_palette(self):
        """Open command palette with all menu actions."""
        commands = []
        seen = set()
        def _harvest(menu, prefix=""):
            for action in menu.actions():
                if action.isSeparator():
                    continue
                if action.menu():
                    # Skip the Theme submenu — replaced by a single "Themes…" entry
                    label = action.text().replace("&", "")
                    if label.strip() == "Theme":
                        continue
                    _harvest(action.menu(), prefix + label + " → ")
                elif action.text() and action.isEnabled():
                    base  = (prefix + action.text().replace("&","")).strip()
                    if base in seen:
                        continue
                    seen.add(base)
                    sc    = action.shortcut().toString()
                    label = f"{base}  ({sc})" if sc else base
                    commands.append((label, action.trigger))
        for action in self.menuBar().actions():
            if action.menu():
                _harvest(action.menu())
        # Add unified theme picker entry at the top
        commands.insert(0, ("Themes…", self._show_theme_picker))
        # Add system-cursor toggle (palette-only)
        label = "System Cursor: On" if not self._system_cursor else "System Cursor: Off"
        commands.insert(1, (label, self._toggle_system_cursor))

        palette = CommandPalette(commands, self)
        # Center it near the top of the window
        geo  = self.geometry()
        pw   = palette.sizeHint().width() or 480
        px   = geo.x() + (geo.width() - pw) // 2
        py   = geo.y() + 80
        palette.move(px, py)
        palette.exec()

    # ── Signatures ────────────────────────────────────────────────────────

    def _open_signature_manager(self):
        if self._sig_dialog is None:
            self._sig_dialog = SignatureManagerDialog(self, self._sig_items)
            self._sig_dialog.finished.connect(self._on_signature_dialog_closed)
            self._sig_dialog.items_changed.connect(self._on_signature_items_changed)
            self._sig_dialog.autopaste_changed.connect(self._on_signature_autopaste_changed)
            self._sig_dialog.set_autopaste_checked(self._sig_autopaste)
        else:
            # Refresh dialog with latest items if it was reused
            pass
        self._sig_dialog.show()
        self._sig_dialog.raise_()
        self._sig_dialog.activateWindow()

    def _on_signature_dialog_closed(self, _code: int):
        if not self._sig_dialog:
            return
        self._sig_items = self._sig_dialog.items()
        save_signature_items(self._settings, self._sig_items)
        self._refresh_signature_hotkeys()
        self._sig_dialog.deleteLater()
        self._sig_dialog = None

    def _on_signature_items_changed(self):
        if not self._sig_dialog:
            return
        self._sig_items = self._sig_dialog.items()
        save_signature_items(self._settings, self._sig_items)
        self._refresh_signature_hotkeys()

    def _on_signature_autopaste_changed(self, on: bool):
        self._sig_autopaste = bool(on)
        self._settings.setValue("signatures.autopaste", self._sig_autopaste)
        self._refresh_signature_hotkeys()

    def _refresh_signature_hotkeys(self):
        status: dict[str, bool] = {}

        try:
            self._sig_hotkeys.clear()
        except Exception:
            return

        for it in self._sig_items:
            if not it.enabled:
                continue
            key = (it.hotkey_key or "").strip().upper()
            mods = int(it.hotkey_mods or 0)
            if not key or mods == 0:
                continue
            hid = self._sig_hotkeys.register(GlobalHotkey(mods=mods, key=key), payload=it.id)
            status[it.id] = bool(hid is not None)

        if self._sig_dialog is not None:
            try:
                self._sig_dialog.set_hotkey_status(status)
            except Exception:
                pass

    def _init_signature_hotkeys(self):
        # Ensure we have a real HWND that receives WM_HOTKEY directly.
        try:
            self._sig_hotkeys.ensure_sink_hwnd()
        except Exception:
            pass
        self._refresh_signature_hotkeys()

    def _on_signature_hotkey(self, sig_id: object):
        sid = str(sig_id or "")
        if not sid:
            return
        it = next((x for x in self._sig_items if x.id == sid and x.enabled), None)
        if not it:
            return
        text = it.text or ""
        if not text:
            return
        clip_ok = False

        # If NovaPad is currently focused, insert directly into the editor.
        try:
            fw = QApplication.focusWidget()
            if isinstance(fw, CodeEditor):
                fw.insertPlainText(text)
                clip_ok = True  # no clipboard needed
                try:
                    self.statusBar().showMessage(
                        f'Signature: "{it.name}"  |  Insert: OK',
                        2200,
                    )
                except Exception:
                    pass
                return
        except Exception:
            pass

        # Otherwise (another app is focused), use clipboard + paste.
        # Prefer native clipboard first; then mirror into Qt.
        try:
            clip_ok = bool(win_set_clipboard_text(text))
        except Exception:
            clip_ok = False

        try:
            QApplication.clipboard().setText(text)
        except Exception:
            pass

        if not bool(self._sig_autopaste):
            try:
                clip_extra = ""
                if not clip_ok:
                    stg = win_clip_last_stage()
                    if stg:
                        clip_extra = f", stage={stg}"
                self.statusBar().showMessage(
                    (
                        f'Signature: "{it.name}"  |  Clipboard: {"OK" if clip_ok else "FAILED"}'
                        f' (err={win_clip_last_error() if not clip_ok else 0}{clip_extra})'
                        f'  |  Paste: skipped (Auto Paste off — press Ctrl+V)'
                    ),
                    2800,
                )
            except Exception:
                pass
            return

        # Defer synthetic Ctrl+V so the global hotkey chord is fully released.
        QTimer.singleShot(
            100,
            lambda n=it.name, c=clip_ok: self._finish_signature_autopaste(n, c),
        )

    def _finish_signature_autopaste(self, sig_name: str, clip_ok: bool):
        paste_ok = False
        pm, pe, px = ("", 0, "")
        try:
            paste_ok = bool(send_ctrl_v())
        except Exception:
            paste_ok = False
        try:
            pm, pe, px = win_last_paste_info()
        except Exception:
            pass
        try:
            clip_extra = ""
            if not clip_ok:
                stg = win_clip_last_stage()
                if stg:
                    clip_extra = f", stage={stg}"
            self.statusBar().showMessage(
                (
                    f'Signature: "{sig_name}"  |  Clipboard: {"OK" if clip_ok else "FAILED"}'
                    f' (err={win_clip_last_error() if not clip_ok else 0}{clip_extra})'
                    f'  |  Paste: {"OK" if paste_ok else "FAILED"}'
                    + ("" if paste_ok else f" (method={pm or 'unknown'}, err={pe})")
                    + ("" if paste_ok or not px else f" ({px})")
                    + ("" if paste_ok else "  (Tip: clipboard ready — press Ctrl+V)")
                ),
                2800,
            )
        except Exception:
            pass

    def _apply_system_cursor(self, on: bool):
        t = ThemeManager.current()
        if on:
            enable_novapad_system_cursors(accent=t["accent"], is_dark=bool(t.get("is_dark", True)))
        else:
            disable_novapad_system_cursors()

    def _toggle_system_cursor(self):
        self._system_cursor = not bool(self._system_cursor)
        self._settings.setValue("system_cursor_global", self._system_cursor)
        self._apply_system_cursor(self._system_cursor)

    def _ensure_system_cursor_restored(self):
        if bool(self._settings.value("system_cursor_global", False, bool)):
            # Always restore on exit to avoid leaving the system cursor altered.
            disable_novapad_system_cursors()

    def _select_all_occurrences(self):
        e = self._tabs.current_editor()
        if e: e.select_all_occurrences()

    def _cursor_above(self):
        e = self._tabs.current_editor()
        if e: e._add_cursor_above()

    def _cursor_below(self):
        e = self._tabs.current_editor()
        if e: e._add_cursor_below()

    def _toggle_distraction_free(self):
        if getattr(self, "_distraction_free", False):
            self._distraction_free = False
            self.menuBar().setVisible(True)
            self.statusBar().setVisible(True)
            self._toolbar.setVisible(True)
            if hasattr(self, "_fmt_toolbar"):
                self._fmt_toolbar.setVisible(True)
            if hasattr(self, "_exit_focus_btn") and self._exit_focus_btn:
                self._exit_focus_btn.hide()
                self._exit_focus_btn.deleteLater()
                self._exit_focus_btn = None
            if getattr(self, "_was_maximized", False):
                self.showMaximized()
            else:
                self.showNormal()
                w = self._settings.value("win_w", 1100, int)
                h = self._settings.value("win_h", 720,  int)
                self.resize(w, h)
            # Re-attach minimap after restoring
            if hasattr(self, "_minimap"):
                e = self._tabs.current_editor()
                if e:
                    self._minimap.set_editor(e)
                self._minimap_wrapper.setVisible(self._minimap_visible)
        else:
            self._distraction_free = True
            self._was_maximized    = self.isMaximized()
            self.menuBar().setVisible(False)
            self.statusBar().setVisible(False)
            self._toolbar.setVisible(False)
            if hasattr(self, "_fmt_toolbar"):
                self._fmt_toolbar.setVisible(False)
            self.showFullScreen()
            # Re-attach minimap
            if hasattr(self, "_minimap"):
                e = self._tabs.current_editor()
                if e:
                    self._minimap.set_editor(e)
                self._minimap_wrapper.setVisible(self._minimap_visible)
                self._minimap.update()
            self._show_exit_focus_btn()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        btn = getattr(self, "_exit_focus_btn", None)
        if btn and btn.isVisible():
            btn.move(self.width() - btn.width() - 16, 16)
        if hasattr(self, "_minimap"):
            self._minimap._sync_height()

    def _show_exit_focus_btn(self):
        """Show a small pill button in top-right corner to exit focus mode."""""
        from PyQt6.QtWidgets import QPushButton
        t   = ThemeManager.current()
        btn = QPushButton("✕  Exit Focus", self)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['bg_hover']};
                color: {t['fg_secondary']};
                border: 1px solid {t['border']};
                border-radius: 12px;
                padding: 4px 14px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {t['accent']};
                color: #FFFFFF;
                border-color: {t['accent']};
            }}
        """)
        btn.clicked.connect(self._toggle_distraction_free)
        btn.adjustSize()
        btn.move(self.width() - btn.width() - 16, 16)
        btn.raise_()
        btn.show()
        self._exit_focus_btn = btn

    def _print_doc(self):
        e = self._tabs.current_editor()
        if not e: return
        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dlg     = QPrintDialog(printer, self)
            if dlg.exec():
                e.print(printer)
        except ImportError:
            themed_info(self, "Print", "Print support is not available in this build.")

    def _indent(self):
        e = self._tabs.current_editor()
        if e:
            e._indent_selection(e.textCursor(), indent=True)

    def _unindent(self):
        e = self._tabs.current_editor()
        if e:
            e._indent_selection(e.textCursor(), indent=False)

    def _case(self, mode: str):
        e = self._tabs.current_editor()
        if not e:
            return
        c = e.textCursor()
        if not c.hasSelection():
            c.select(c.SelectionType.Document)
        t = c.selectedText().replace("\u2029", "\n")
        if mode == "upper":
            result = t.upper()
        elif mode == "lower":
            result = t.lower()
        elif mode == "title":
            result = _smart_title_case(t)
        else:
            return
        c.insertText(result)
        e.setTextCursor(c)

    # ── Settings propagation ──────────────────────────────────────────────

    def _propagate_settings(self):
        for e in self._tabs.all_editors():
            self._apply_settings_to(e)

    def _apply_settings_to(self, e: CodeEditor | None):
        if e:
            e.set_dark_mode(ThemeManager.is_dark())
            e.set_word_wrap(self._word_wrap)
            e.toggle_line_numbers(self._show_ln)
            try:
                e.zoom_step.disconnect(self._zoom)
            except (RuntimeError, TypeError):
                pass
            e.zoom_step.connect(self._zoom)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _update_title(self, label: str | None = None):
        e = self._tabs.current_editor()
        if e and e.file_path:
            base = os.path.basename(e.file_path)
            mod  = "  \u2022" if e.document().isModified() else ""
            self.setWindowTitle(f"NovaPad  \u2014  {base}{mod}")
        elif label:
            self.setWindowTitle(f"NovaPad  \u2014  {label.lstrip('* ')}")
        else:
            self.setWindowTitle("NovaPad")

    def _on_tab_changed(self, editor: CodeEditor | None):
        if editor:
            self._findbar.set_editor(editor)
            self._apply_settings_to(editor)
            self._wire_autosave(editor)
            # Attach bookmark manager so gutter can paint dots
            editor.set_bookmark_manager(self._bookmarks)
            if hasattr(self, "_fmt_toolbar"):
                self._fmt_toolbar.set_editor(editor)
            if hasattr(self, "_goto_bar"):
                self._goto_bar.set_editor(editor)
            if hasattr(self, "_minimap"):
                self._minimap.set_editor(editor)
        self._update_title()

    def _wire_autosave(self, editor: CodeEditor | None):
        if editor is None:
            return
        eid = id(editor)
        if eid in self._autosave_connected:
            return
        self._autosave_connected.add(eid)

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self._autosave_debounce_ms)
        timer.timeout.connect(lambda e=editor: self._autosave_flush(e))
        self._autosave_timers[eid] = timer

        def _on_change(*_args, e=editor):
            if not self._auto_save:
                return
            if e.file_path is None:
                return
            if id(e) in self._autosave_writing:
                return
            try:
                self._autosave_timers[id(e)].start()
            except Exception:
                pass

        try:
            editor.document().contentsChanged.connect(_on_change)
        except Exception:
            pass
        try:
            # Some edit paths (rich text operations) can be more reliably observed via textChanged.
            editor.textChanged.connect(_on_change)
        except Exception:
            pass

    def _autosave_flush(self, editor: CodeEditor):
        if not self._auto_save:
            return
        if editor.file_path is None:
            return
        if not editor.document().isModified():
            return

        eid = id(editor)
        if eid in self._autosave_writing:
            return
        self._autosave_writing.add(eid)
        try:
            self._write(editor, editor.file_path)
        finally:
            self._autosave_writing.discard(eid)

    def _restore_session(self):
        """File → Restore Last Session."""
        session = getattr(self, "_session", None)
        if session is None:
            from utils.session import SessionManager
            session = SessionManager()
        session.restore(self)

    # ── Session actions ──────────────────────────────────────────────────────

    def _restore_last_session(self):
        if self._session:
            restored = self._session.restore_last_session(self)
            if not restored:
                from ui.dialogs import themed_info as _ti
                _ti(self, "Session",
                    "No previous session data found.")

    def _save_session_now(self):
        if self._session:
            self._session.save(self, clean=False)
            self.statusBar().showMessage("Session saved.", 3000)

    # ── About ─────────────────────────────────────────────────────────────

    def _about(self):
        from PyQt6.QtWidgets import QApplication
        from ui.dialogs import themed_about
        app = QApplication.instance()
        v = app.applicationVersion() if app else "3.1.5"
        themed_about(self, "About NovaPad",
            f"<h2>NovaPad {v}</h2>"
            "<p>A modern, lightweight text editor built with PyQt6.</p>"

            "<h3>What's New</h3>"

            "<p><b>3.1.7</b> &nbsp;<span style='color:#888'>2026-04-24</span></p>"
            "<ul>"
            "<li>Daily Notes — a calendar button in the toolbar opens today's note automatically; "
            "click the calendar icon to pick any date from a themed popup calendar</li>"
            "<li>Signature Manager (CopyTexty) — Tools menu opens a manager where you can store "
            "text snippets, assign a global hotkey to each, and have them instantly pasted into "
            "any app (Ctrl+V is sent automatically)</li>"
            "<li>Themed cursor — text caret and I-beam mouse cursor are now colored with each theme's accent</li>"
            "<li>Installer now requires administrator — fixes install failures on machines where C:\\Program Files requires elevation</li>"
            "<li>Removed code file-type associations (.py, .bat, .cmd, .sh, .ps1, .c, .go, .rs, etc.) from the installer to prevent accidental breakage of double-click execution</li>"
            "<li>Fixed Ctrl+scroll zoom no longer also scrolls the editor — scrollbar is locked while zooming</li>"
            "<li>Fixed gutter clipping at high line counts or large zoom levels</li>"
            "<li>Zoom no longer drifts to a different line — viewport anchors to the first visible block</li>"
            "<li>Fixed crash on launch when installed to C:\\Program Files — crash.log is now written to %%APPDATA%%\\NovaPad instead of the protected install folder</li>"
            "</ul>"

            "<p><b>3.1.6</b> &nbsp;<span style='color:#888'>2026-04-01</span></p>"
            "<ul>"
            "<li>Zoom performance — block reformatting is now batched in a single edit block, eliminating per-block repaints on large documents</li>"
            "</ul>"

            "<p><b>3.1.5</b> &nbsp;<span style='color:#888'>2026-03-28</span></p>"
            "<ul>"
            "<li>Added 10 gradient themes — Sunset, Aurora, Neon City, Deep Ocean,"
            " Midnight Bloom, Candy, Tropical Sunrise, Sky Gradient, Rose Gold, Citrus</li>"
            "<li>Fixed tab bar rendering glitch on startup with gradient themes</li>"
            "<li>Gradient applies only to toolbar so tabs and editor are never disrupted</li>"
            "<li>Improved tab width calculation: browser-style dynamic shrink with ellipsis</li>"
            "<li>Scroll buttons appear automatically when tabs overflow the tab bar</li>"
            "</ul>"

            "<p><b>3.1.4</b> &nbsp;<span style='color:#888'>2026-03-27</span></p>"
            "<ul>"
            "<li>Document auto-saves 800 ms after any keystroke — no more waiting for the"
            " 30-second timer after a change</li>"
            "<li>Timestamp lines now survive session restore and autosave restore correctly</li>"
            "<li>Fixed: backspace on a timestamp line now deletes the whole line cleanly</li>"
            "<li>Fixed: deleting a timestamp when another timestamp is directly below"
            " no longer traps the cursor</li>"
            "<li>Fixed: timestamp color and font size now match the current theme on file"
            " open and session restore</li>"
            "</ul>"

            "<p><b>3.1.3</b> &nbsp;<span style='color:#888'>2026-03-25</span></p>"
            "<ul>"
            "<li>Minimap — live scaled preview of the document with viewport indicator</li>"
            "<li>Scrollbar overlay rendered on top of the minimap</li>"
            "<li>Format toolbar — Bold, Italic, Underline, font family and size picker</li>"
            "<li>Go to Line bar (Ctrl+G)</li>"
            "<li>Bookmark manager — toggle, navigate, and clear bookmarks</li>"
            "<li>Command palette (Ctrl+P) for fuzzy-search access to all actions</li>"
            "<li>Theme picker overlay with live preview on hover</li>"
            "</ul>"

            "<p><b>3.1.2</b> &nbsp;<span style='color:#888'>2026-03-20</span></p>"
            "<ul>"
            "<li>68 themes — 38 dark and 30 light including Catppuccin, Tokyo Night,"
            " Dracula, Gruvbox, Nord, Rose Piné, Kanagawa, and many more</li>"
            "<li>Windows 11+ (build 22000+): title bar and border tinted via DWM to match the menu/toolbar; "
            "set <code>titlebar.match_windows_dwm</code> false in QSettings to use the OS default caption</li>"
            "<li>Animated theme transition — cross-fade overlay when switching themes</li>"
            "<li>Auto-update checker — background GitHub release check with one-click"
            " download and silent reinstall</li>"
            "</ul>"

            "<p><b>3.1.1</b> &nbsp;<span style='color:#888'>2026-03-15</span></p>"
            "<ul>"
            "<li>Crash recovery — lock file detects unclean exits and prompts to restore</li>"
            "<li>Full session persistence — unsaved tab content written to temp storage,"
            " restored exactly on next launch</li>"
            "<li>Read-only timestamp lines — F5 inserts a styled, protected date/time line</li>"
            "<li>Find &amp; Replace with live match highlighting and match counter</li>"
            "<li>Syntax highlighting — Python, JavaScript/TypeScript, HTML, CSS, JSON</li>"
            "<li>Drag-to-reorder tabs, close button on each tab</li>"
            "</ul>"

            f"<p><i>Version {v} &nbsp;·&nbsp; MIT Licence &nbsp;·&nbsp; "
            "<a href='https://github.com/Leem-y/novapad'>github.com/Leem-y/novapad</a></i></p>"
        )

    # ── Close event ───────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                self.open_file(path)

    def _install_system_tray(self) -> None:
        if not bool(self._settings.value("close_to_tray", True, bool)):
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(self)
        tray.setIcon(get_app_icon())
        tray.setToolTip("NovaPad")
        menu = QMenu()
        act_show = QAction("Show NovaPad", self)
        act_show.triggered.connect(self._restore_from_tray)
        act_quit = QAction("Quit NovaPad", self)
        act_quit.triggered.connect(self._quit_from_tray_menu)
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_quit)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self._tray = tray
        try:
            QApplication.instance().setQuitOnLastWindowClosed(False)
        except Exception:
            pass

    def _restore_from_tray(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(0, self._apply_dwm_titlebar)

    def _quit_from_tray_menu(self) -> None:
        self._quit_requested = True
        self.close()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore_from_tray()

    def closeEvent(self, event):
        for i in range(self._tabs.count() - 1, -1, -1):
            e = self._tabs.editor_at(i)
            if e and e.document().isModified():
                name  = (os.path.basename(e.file_path)
                         if e.file_path else self._tabs.tabText(i).lstrip("* "))
                reply = themed_question(
                    self, "Unsaved Changes",
                    f'Save changes to "{name}"?',
                    btn_yes="Save", btn_no="Discard", btn_cancel="Cancel"
                )
                if reply == "Save":
                    self.save_file(editor=e)
                elif reply == "Cancel" or reply is None:
                    self._quit_requested = False
                    event.ignore()
                    return

        # Exit distraction-free before saving so we never persist fullscreen state
        if getattr(self, "_distraction_free", False):
            self._distraction_free = False
            if getattr(self, "_was_maximized", False):
                self.showMaximized()
            else:
                self.showNormal()
            self.menuBar().setVisible(True)
            self.statusBar().setVisible(True)
            self._toolbar.setVisible(True)
        # Save geometry only when in normal/maximized state
        self._settings.setValue("win_maximized", self.isMaximized())
        if not self.isFullScreen():
            if not self.isMaximized():
                self._settings.setValue("win_w", self.width())
                self._settings.setValue("win_h", self.height())
                self._settings.setValue("win_x", self.x())
                self._settings.setValue("win_y", self.y())

        use_tray = (
            bool(self._settings.value("close_to_tray", True, bool))
            and self._tray is not None
            and not self._quit_requested
        )
        if use_tray:
            try:
                if self._session is not None:
                    self._session.save(self, clean=False)
            except Exception:
                pass
            self.hide()
            event.ignore()
            return

        # Real quit: drop tray icon, unregister global hotkeys, then exit the app.
        try:
            if self._tray is not None:
                self._tray.hide()
        except Exception:
            pass
        try:
            self._sig_hotkeys.clear()
            QApplication.instance().removeNativeEventFilter(self._sig_hotkeys)
        except Exception:
            pass
        self._quit_requested = False
        event.accept()
        QTimer.singleShot(0, lambda: QApplication.instance().quit())
