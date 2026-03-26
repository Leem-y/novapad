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

from PyQt6.QtCore    import QSettings, Qt, QTimer
from PyQt6.QtGui     import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMainWindow,
    QMessageBox, QStatusBar, QToolBar, QVBoxLayout, QWidget,
)

from assets.icons    import get_app_icon, get_icon, toolbar_color
from core.editor     import CodeEditor
from core.tab_manager import TabManager
from ui.find_bar       import FindBar
from ui.format_toolbar import FormatToolbar
from ui.goto_line      import GotoLineBar
from ui.bookmarks      import BookmarkManager
from ui.theme        import ThemeManager

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


class MainWindow(QMainWindow):
    """NovaPad main window."""

    def __init__(self, session=None):
        super().__init__()
        self._session   = session
        self._settings  = QSettings("NovaPad", "NovaPad")
        self._dark_mode = self._settings.value("dark_mode",    True,  bool)
        self._word_wrap = self._settings.value("word_wrap",    False, bool)
        self._show_ln   = self._settings.value("line_numbers", True,  bool)
        self._auto_save = self._settings.value("auto_save",    True,  bool)

        self._setup_window()
        self._build_central()
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()
        self._build_shortcuts()

        # Apply initial theme
        ThemeManager.apply(QApplication.instance(), self._dark_mode)
        self._propagate_settings()

        # File-save autosave (saves files that have paths)
        if self._auto_save:
            t = QTimer(self)
            t.timeout.connect(self._auto_save_all)
            t.start(60_000)

        # Status refresh
        st = QTimer(self)
        st.timeout.connect(self._refresh_status)
        st.start(400)

    # ── Window ────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle("NovaPad")
        self.setWindowIcon(get_app_icon())
        w = self._settings.value("win_w", 1100, int)
        h = self._settings.value("win_h", 720,  int)
        self.resize(w, h)
        x = self._settings.value("win_x", -1, int)
        y = self._settings.value("win_y", -1, int)
        if x >= 0 and y >= 0:
            self.move(x, y)

    # ── Central area ──────────────────────────────────────────────────────

    def _build_central(self):
        container = QWidget(self)
        lay       = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._tabs    = TabManager(self)
        self._findbar = FindBar(self)
        self._findbar.setVisible(False)

        lay.addWidget(self._tabs)
        lay.addWidget(self._findbar)
        self.setCentralWidget(container)

        # Seed with one empty tab
        self._tabs.new_tab()

        self._tabs.tab_changed.connect(self._on_tab_changed)
        self._tabs.title_changed.connect(self._update_title)
        self._tabs.modification_changed.connect(lambda _: self._update_title())

        # Bookmark manager (shared across all tabs)
        self._bookmarks = BookmarkManager()

        # Go-to-line bar
        self._goto_bar = GotoLineBar(self)
        self._goto_bar.setVisible(False)
        lay.addWidget(self._goto_bar)

    # ── Menu bar ──────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        # ── File ──────────────────────────────────────────────────────
        fm = mb.addMenu("&File")
        self._act(fm, "&New Tab",          self.new_file,       "Ctrl+T")
        self._act(fm, "New Tab (&Alt)",    self.new_file,       "Ctrl+N")
        self._act(fm, "New &Window",       self.new_window,     "Ctrl+Shift+N")
        fm.addSeparator()
        self._act(fm, "&Open…",            self.open_file,      "Ctrl+O")
        fm.addSeparator()
        self._act(fm, "&Save",             lambda _: self.save_file(),    "Ctrl+S")
        self._act(fm, "Save &As…",         lambda _: self.save_file_as(), "Ctrl+Shift+S")
        self._act(fm, "Save Al&l",         self.save_all,       "Ctrl+Alt+S")
        fm.addSeparator()
        self._act(fm, "&Close Tab",        self._close_current,    "Ctrl+W")
        fm.addSeparator()
        self._act(fm, "Restore Last &Session", self._restore_session, None)
        fm.addSeparator()
        self._act(fm, "E&xit",             self.close,          "Alt+F4")

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
        self._act(em, "Insert &Timestamp", self.insert_timestamp, "F5")

        # ── View ──────────────────────────────────────────────────────
        vm = mb.addMenu("&View")
        self._act_dark = self._checkable_act(
            vm, "Dark &Mode", self.toggle_dark_mode,
            "Ctrl+Shift+D", self._dark_mode
        )
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
        self._act(vm, "Zoom &In",          self._zoom_in,       "Ctrl+=")
        self._act(vm, "Zoom &Out",         self._zoom_out,      "Ctrl+-")
        self._act(vm, "&Reset Zoom",       self._zoom_reset,    "Ctrl+0")

        # ── Format ────────────────────────────────────────────────────
        fmt = mb.addMenu("F&ormat")
        self._act(fmt, "&Indent Lines",    self._indent,        "Ctrl+]")
        self._act(fmt, "&Unindent Lines",  self._unindent,      "Ctrl+[")
        fmt.addSeparator()
        self._act(fmt, "&UPPERCASE",       lambda: self._case("upper"), "Ctrl+Shift+U")
        self._act(fmt, "&lowercase",       lambda: self._case("lower"), None)

        # ── Session ───────────────────────────────────────────────────
        sm = mb.addMenu("&Session")
        self._act(sm, "&Restore Last Session", self._restore_last_session, None)
        sm.addSeparator()
        self._act(sm, "&Save Session Now",     self._save_session_now,     None)

        # ── Navigate ──────────────────────────────────────────────────
        nm = mb.addMenu("&Navigate")
        self._act(nm, "&Go to Line…",        self.show_goto_line,      "Ctrl+G")
        nm.addSeparator()
        self._act(nm, "Toggle &Bookmark",     self.toggle_bookmark,      "Ctrl+F2")
        self._act(nm, "Next Bookmark",        self.goto_next_bookmark,   "F2")
        self._act(nm, "Previous Bookmark",    self.goto_prev_bookmark,   "Shift+F2")
        nm.addSeparator()
        self._act(nm, "Next Tab",             self._next_tab,            "Ctrl+Tab")
        self._act(nm, "Previous Tab",         self._prev_tab,            "Ctrl+Shift+Tab")

        # ── Help ──────────────────────────────────────────────────────
        hm = mb.addMenu("&Help")
        self._act(hm, "&About NovaPad…",   self._about,         "F1")

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
        dark = self._dark_mode
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
        btn("undo",      "Undo (Ctrl+Z)",          self._undo)
        btn("redo",      "Redo (Ctrl+Y)",          self._redo)
        self._toolbar.addSeparator()
        btn("cut",       "Cut (Ctrl+X)",           self._cut)
        btn("copy",      "Copy (Ctrl+C)",          self._copy)
        btn("paste",     "Paste (Ctrl+V)",         self._paste)
        self._toolbar.addSeparator()
        btn("search",    "Find (Ctrl+F)",          self.show_find)
        btn("replace",   "Find & Replace (Ctrl+H)",self.show_replace)
        btn("clock",     "Insert Timestamp (F5)",  self.insert_timestamp)
        self._toolbar.addSeparator()

        # Dark-mode toggle (checkable toolbar button)
        icon_name = "sun" if dark else "moon"
        self._tb_theme = QAction(ic(icon_name), "", self)
        self._tb_theme.setToolTip("Toggle Dark / Light Mode (Ctrl+Shift+D)")
        self._tb_theme.setCheckable(True)
        self._tb_theme.setChecked(dark)
        self._tb_theme.triggered.connect(self.toggle_dark_mode)
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
        self._lbl_words  = QLabel("Words: 0")
        self._lbl_lang   = QLabel("Plain Text")
        self._lbl_mod    = QLabel("")
        for lbl in (self._lbl_pos, self._lbl_words, self._lbl_lang, self._lbl_mod):
            sb.addPermanentWidget(lbl)

    def _refresh_status(self):
        e = self._tabs.current_editor()
        if not e:
            return
        ln, col = e.cursor_position()
        self._lbl_pos.setText(f"Ln {ln},  Col {col}")
        text  = e.toPlainText()
        words = len(text.split()) if text.strip() else 0
        self._lbl_words.setText(f"Words: {words}")
        lang  = e.language.replace("javascript", "JavaScript").capitalize()
        self._lbl_lang.setText(lang if lang != "Plain" else "Plain Text")
        self._lbl_mod.setText("  Modified" if e.document().isModified() else "")

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

        _sc("F3",           self._find_next_shortcut)
        _sc("Shift+F3",     self._find_prev_shortcut)
        _sc("Ctrl+Tab",     self._next_tab)
        _sc("Ctrl+Shift+Tab", self._prev_tab)

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

    def goto_next_bookmark(self):
        e = self._tabs.current_editor()
        if e:
            self._bookmarks.goto_next(e)

    def goto_prev_bookmark(self):
        e = self._tabs.current_editor()
        if e:
            self._bookmarks.goto_prev(e)

    # ── File operations ───────────────────────────────────────────────────

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
            QMessageBox.critical(self, "Error", str(err))
            return
        editor = self._tabs.new_tab(file_path=path, content="")
        editor.load_content(content, path)
        self._apply_settings_to(editor)
        editor._bookmark_manager = self._bookmarks
        if hasattr(self, "_fmt_toolbar"):
            self._fmt_toolbar.set_editor(editor)
        if hasattr(self, "_goto_bar"):
            self._goto_bar.set_editor(editor)
        self._update_title()

    def save_file(self, editor: CodeEditor | None = None) -> bool:
        if editor is None:
            editor = self._tabs.current_editor()
        if editor is None:
            return False
        if not editor.file_path:
            return self.save_file_as(editor=editor)
        return self._write(editor, editor.file_path)

    def save_file_as(self, editor: CodeEditor | None = None) -> bool:
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
            with open(path, "w", encoding="utf-8") as f:
                f.write(editor.get_content_for_save(path))
            editor.file_path = path
            editor.document().setModified(False)
            self._tabs.refresh_tab_title(editor)
            self._update_title()
            return True
        except OSError as err:
            QMessageBox.critical(self, "Save Error", str(err))
            return False

    def _auto_save_all(self):
        for e in self._tabs.all_editors():
            if e.file_path and e.document().isModified():
                self._write(e, e.file_path)

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
        e = self._tabs.current_editor()
        if e:
            e.insert_timestamp()

    # ── Find / Replace ────────────────────────────────────────────────────

    def show_find(self):
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
        if checked is None:
            checked = not self._dark_mode
        self._dark_mode = checked
        # Sync checkable actions that might be out of sync
        self._act_dark.blockSignals(True)
        self._act_dark.setChecked(checked)
        self._act_dark.blockSignals(False)

        ThemeManager.apply(QApplication.instance(), checked)
        self._tabs.set_dark_mode(checked)
        self._refresh_toolbar_icons()
        self._findbar.refresh_icons()
        self._settings.setValue("dark_mode", checked)

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
        e = self._tabs.current_editor()
        if not e:
            return
        if direction == 0:
            f = e.font(); f.setPointSize(11); e.setFont(f)
        else:
            e.zoomIn(2 * direction)

    # ── Format ────────────────────────────────────────────────────────────

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
        if c.hasSelection():
            t = c.selectedText()
            c.insertText(t.upper() if mode == "upper" else t.lower())

    # ── Settings propagation ──────────────────────────────────────────────

    def _propagate_settings(self):
        for e in self._tabs.all_editors():
            self._apply_settings_to(e)

    def _apply_settings_to(self, e: CodeEditor | None):
        if e:
            e.set_dark_mode(self._dark_mode)
            e.set_word_wrap(self._word_wrap)
            e.toggle_line_numbers(self._show_ln)

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
            # Attach bookmark manager so gutter can paint dots
            editor._bookmark_manager = self._bookmarks
            if hasattr(self, "_fmt_toolbar"):
                self._fmt_toolbar.set_editor(editor)
            if hasattr(self, "_goto_bar"):
                self._goto_bar.set_editor(editor)
        self._update_title()

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
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Session",
                    "No previous session data found.")

    def _save_session_now(self):
        if self._session:
            self._session.save(self, clean=False)
            self.statusBar().showMessage("Session saved.", 3000)

    # ── About ─────────────────────────────────────────────────────────────

    def _about(self):
        QMessageBox.about(
            self, "About NovaPad",
            "<h2>NovaPad 2.0</h2>"
            "<p>A modern, lightweight text editor built with PyQt6.</p>"
            "<ul>"
            "<li>VS Code-style syntax highlighting</li>"
            "<li>Tabbed multi-file editing</li>"
            "<li>Find &amp; Replace with match highlighting</li>"
            "<li>Line numbers &amp; current-line gutter</li>"
            "<li>Dark / Light themes</li>"
            "<li>Auto-save &amp; session restore</li>"
            "</ul>"
            "<p><i>Version 2.0.0 &nbsp;·&nbsp; MIT Licence</i></p>"
        )

    # ── Close event ───────────────────────────────────────────────────────

    def closeEvent(self, event):
        for i in range(self._tabs.count() - 1, -1, -1):
            e = self._tabs.editor_at(i)
            if e and e.document().isModified():
                name  = (os.path.basename(e.file_path)
                         if e.file_path else self._tabs.tabText(i).lstrip("* "))
                reply = QMessageBox.question(
                    self, "Unsaved Changes",
                    f'Save changes to "{name}"?',
                    QMessageBox.StandardButton.Save |
                    QMessageBox.StandardButton.Discard |
                    QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Save:
                    self.save_file(editor=e)
                elif reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return

        self._settings.setValue("win_w", self.width())
        self._settings.setValue("win_h", self.height())
        self._settings.setValue("win_x", self.x())
        self._settings.setValue("win_y", self.y())
        event.accept()
