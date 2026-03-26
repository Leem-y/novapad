"""
ui/find_bar.py  –  NovaPad Find / Replace Bar
===============================================
A reliable, self-contained inline find/replace panel.

Root-cause fixes
----------------
1. NO shortcut bindings are registered here.  All shortcuts live in
   MainWindow via QAction, with Qt.ShortcutContext.WidgetWithChildrenShortcut
   to avoid the "Ambiguous shortcut overload: Ctrl+F" Qt warning.

2. Replace is implemented via a single QTextCursor.beginEditBlock() /
   endEditBlock() pair so undo/redo history is preserved correctly and
   cursor focus returns to the editor afterwards with the cursor positioned
   right after the last replacement.

3. All match highlighting uses QTextEdit.ExtraSelection objects stored in
   _match_selections; they are cleared before every new search so no stale
   highlights remain.

4. setFocus() is called on the editor after every replace so the user can
   keep typing immediately without clicking.
"""

from __future__ import annotations

from PyQt6.QtCore    import Qt, pyqtSignal
from PyQt6.QtGui     import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QTextEdit, QWidget,
)

from assets.icons import get_icon, toolbar_color
from ui.theme    import ThemeManager


class FindBar(QWidget):
    """
    Inline find/replace panel.

    Public API
    ----------
    set_editor(editor)          – attach to a CodeEditor instance
    show_bar(replace=False)     – make visible, pre-fill from selection
    hide_bar()                  – hide and return focus to editor
    find_next()                 – find next occurrence
    find_prev()                 – find previous occurrence
    """

    closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FindBar")
        self._editor            = None
        self._match_selections: list[QTextEdit.ExtraSelection] = []
        self._build_ui()

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setFixedHeight(46)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(6)

        dark = ThemeManager.is_dark()
        ic   = lambda name: get_icon(name, toolbar_color(dark), 14)

        # Close
        self._btn_close = QPushButton()
        self._btn_close.setIcon(ic("close"))
        self._btn_close.setFixedSize(26, 26)
        self._btn_close.setToolTip("Close  (Esc)")
        self._btn_close.clicked.connect(self.hide_bar)
        lay.addWidget(self._btn_close)

        # Find input
        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("Find…")
        self._find_input.setMinimumWidth(180)
        self._find_input.textChanged.connect(self._on_find_text_changed)
        self._find_input.returnPressed.connect(self.find_next)
        lay.addWidget(self._find_input)

        # Prev / Next
        self._btn_prev = QPushButton()
        self._btn_prev.setIcon(ic("arrow_up"))
        self._btn_prev.setFixedSize(30, 26)
        self._btn_prev.setToolTip("Previous match  (Shift+F3)")
        self._btn_prev.clicked.connect(self.find_prev)
        lay.addWidget(self._btn_prev)

        self._btn_next = QPushButton()
        self._btn_next.setIcon(ic("arrow_down"))
        self._btn_next.setFixedSize(30, 26)
        self._btn_next.setToolTip("Next match  (F3)")
        self._btn_next.clicked.connect(self.find_next)
        lay.addWidget(self._btn_next)

        # Case / Regex checkboxes
        self._cb_case = QCheckBox("Aa")
        self._cb_case.setToolTip("Match case")
        self._cb_case.stateChanged.connect(self._on_find_text_changed)
        lay.addWidget(self._cb_case)

        # Match count
        self._lbl_count = QLabel("")
        self._lbl_count.setFixedWidth(90)
        self._lbl_count.setStyleSheet("color: #8E8E93; font-size: 11px;")
        lay.addWidget(self._lbl_count)

        lay.addStretch(1)

        # ── Replace section ───────────────────────────────────────────
        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("Replace with…")
        self._replace_input.setMinimumWidth(160)
        self._replace_input.setVisible(False)
        lay.addWidget(self._replace_input)

        self._btn_replace = QPushButton("Replace")
        self._btn_replace.setVisible(False)
        self._btn_replace.clicked.connect(self.replace_one)
        lay.addWidget(self._btn_replace)

        self._btn_replace_all = QPushButton("All")
        self._btn_replace_all.setFixedWidth(40)
        self._btn_replace_all.setVisible(False)
        self._btn_replace_all.clicked.connect(self.replace_all)
        lay.addWidget(self._btn_replace_all)

        self._btn_toggle_replace = QPushButton("Replace")
        self._btn_toggle_replace.setCheckable(True)
        self._btn_toggle_replace.setFixedWidth(72)
        self._btn_toggle_replace.toggled.connect(self._toggle_replace_mode)
        lay.addWidget(self._btn_toggle_replace)

    # ── Public API ────────────────────────────────────────────────────────

    def set_editor(self, editor):
        """Detach from old editor, attach to new one."""
        if self._editor is not None:
            self._clear_highlights()
        self._editor = editor

    def show_bar(self, replace: bool = False):
        self.setVisible(True)
        self._btn_toggle_replace.setChecked(replace)
        # Pre-fill find field from current selection (single line only)
        if self._editor:
            sel = self._editor.textCursor().selectedText()
            if sel and "\u2029" not in sel:
                self._find_input.setText(sel)
        self._find_input.selectAll()
        self._find_input.setFocus()
        self._update_highlights()

    def hide_bar(self):
        self._clear_highlights()
        self.setVisible(False)
        self.closed.emit()
        if self._editor:
            self._editor.setFocus()

    def refresh_icons(self):
        """Call after theme change to re-colour icons."""
        dark = ThemeManager.is_dark()
        ic   = lambda name: get_icon(name, toolbar_color(dark), 14)
        self._btn_close.setIcon(ic("close"))
        self._btn_prev.setIcon(ic("arrow_up"))
        self._btn_next.setIcon(ic("arrow_down"))

    # ── Find ──────────────────────────────────────────────────────────────

    def find_next(self):
        self._find(forward=True)

    def find_prev(self):
        self._find(forward=False)

    def _find(self, forward: bool):
        if not self._editor or not self._query():
            return

        flags = self._get_flags(forward)
        found = self._editor.find(self._query(), flags)

        if not found:
            # Wrap-around: move cursor to start/end then try again
            cursor = self._editor.textCursor()
            if forward:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.End)
            self._editor.setTextCursor(cursor)
            self._editor.find(self._query(), flags)

        self._update_highlights()

    def _get_flags(self, forward: bool = True) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self._cb_case.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if not forward:
            flags |= QTextDocument.FindFlag.FindBackward
        return flags

    def _query(self) -> str:
        return self._find_input.text()

    # ── Replace ───────────────────────────────────────────────────────────

    def replace_one(self):
        """
        Replace the currently selected match (if it matches the query),
        then advance to the next.  Preserves undo/redo via edit block.
        """
        if not self._editor or not self._query():
            return

        cursor = self._editor.textCursor()
        q      = self._query()
        repl   = self._replace_input.text()
        sel    = cursor.selectedText()

        case_match = (
            (self._cb_case.isChecked()  and sel == q) or
            (not self._cb_case.isChecked() and sel.lower() == q.lower())
        )

        if case_match:
            cursor.beginEditBlock()
            cursor.insertText(repl)
            cursor.endEditBlock()

        # Advance to next match and keep focus in editor
        self.find_next()
        self._editor.setFocus()

    def replace_all(self):
        """
        Replace every occurrence in the document in a single edit block.
        The cursor is moved to the first match (or left where it was).
        Focus returns to the editor so typing can continue immediately.
        """
        if not self._editor or not self._query():
            return

        q    = self._query()
        repl = self._replace_input.text()
        doc  = self._editor.document()

        # Build find flags WITHOUT backward
        flags = QTextDocument.FindFlag(0)
        if self._cb_case.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively

        # Use a single edit block so the whole operation is one undo step
        # We walk the document with find() starting from position 0
        count  = 0
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        cursor.beginEditBlock()
        while True:
            found_cursor = doc.find(q, cursor, flags)
            if found_cursor.isNull():
                break
            found_cursor.insertText(repl)
            # Continue searching from the position just after the replacement
            cursor = found_cursor
            count += 1
        cursor.endEditBlock()

        # Update label and return focus
        if count:
            self._lbl_count.setText(f"Replaced {count}")
            self._lbl_count.setStyleSheet("color: #30D158; font-size: 11px;")
        else:
            self._lbl_count.setText("No matches")
            self._lbl_count.setStyleSheet("color: #FF453A; font-size: 11px;")

        self._clear_highlights()
        self._editor.setFocus()

    # ── Match highlighting ────────────────────────────────────────────────

    def _on_find_text_changed(self, *_):
        self._update_highlights()

    def _update_highlights(self):
        """Colour all matches in the document as ExtraSelections."""
        if not self._editor:
            return
        self._clear_highlights()
        q = self._query()
        if not q:
            self._lbl_count.setText("")
            return

        colors = ThemeManager.find_colors()
        match_fmt = QTextCharFormat()
        match_fmt.setBackground(QColor(colors["match_bg"]))
        match_fmt.setForeground(QColor(colors["match_fg"]))

        doc   = self._editor.document()
        flags = QTextDocument.FindFlag(0)
        if self._cb_case.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively

        cur_sel  = self._editor.textCursor()
        cur_start = cur_sel.selectionStart()
        cur_end   = cur_sel.selectionEnd()

        count   = 0
        sels    = []
        cursor  = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        while True:
            found = doc.find(q, cursor, flags)
            if found.isNull():
                break
            count += 1

            sel        = QTextEdit.ExtraSelection()
            # Highlight the current (active) match differently
            is_current = (found.selectionStart() == cur_start and
                          found.selectionEnd()   == cur_end)
            if is_current:
                sel.format.setBackground(QColor(colors["cur_bg"]))
                sel.format.setForeground(QColor(colors["cur_fg"]))
            else:
                sel.format = match_fmt
            sel.cursor = found
            sels.append(sel)
            cursor = found

        self._match_selections = sels
        # Merge with whatever the editor already has (e.g. current-line highlight)
        existing = self._editor.extraSelections()
        self._editor.setExtraSelections(existing + sels)

        # Update count label
        if count == 0:
            self._lbl_count.setText("No matches")
            self._lbl_count.setStyleSheet("color: #FF453A; font-size: 11px;")
        else:
            self._lbl_count.setText(f"{count} match{'es' if count != 1 else ''}")
            self._lbl_count.setStyleSheet("color: #8E8E93; font-size: 11px;")

    def _clear_highlights(self):
        """Remove all find-highlight extra selections from the editor."""
        if not self._editor:
            return
        existing = self._editor.extraSelections()
        cleaned  = [s for s in existing if s not in self._match_selections]
        self._editor.setExtraSelections(cleaned)
        self._match_selections = []

    # ── Replace mode toggle ───────────────────────────────────────────────

    def _toggle_replace_mode(self, checked: bool):
        self._replace_input.setVisible(checked)
        self._btn_replace.setVisible(checked)
        self._btn_replace_all.setVisible(checked)

    # ── Key handling ──────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_bar()
        else:
            super().keyPressEvent(event)
