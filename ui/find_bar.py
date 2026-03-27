# ui/find_bar.py -- NovaPad Find & Replace Bar

from __future__ import annotations

from PyQt6.QtCore    import Qt, QTimer, pyqtSignal
from PyQt6.QtGui     import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from assets.icons import get_icon, toolbar_color
from ui.theme    import ThemeManager
from core.editor import _is_timestamp_block


class _CloseBtn(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, e):
        from PyQt6.QtGui import QPainter, QPen, QColor
        from ui.theme import ThemeManager
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = QColor(ThemeManager.current()["fg_muted"])
        pen = QPen(col)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        pad = 4
        p.drawLine(pad,    pad,    16-pad, 16-pad)
        p.drawLine(16-pad, pad,    pad,    16-pad)


class FindBar(QWidget):

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FindBar")
        self._editor = None
        self._match_selections = []
        self._build()

    def _build(self):
        dark = ThemeManager.is_dark()
        ic   = lambda name: get_icon(name, toolbar_color(dark), 13)
        ss_icon = "QPushButton{padding:1px;min-width:0;min-height:0;border-radius:4px;}"
        ss_btn  = "QPushButton{padding:2px 6px;min-width:0;min-height:0;font-size:11px;border-radius:4px;}"
        ss_cb   = "QCheckBox{spacing:3px;font-size:11px;}"

        # Grid: col 0 = close btn, col 1 = input (stretches), col 2 = controls
        grid = QGridLayout(self)
        grid.setContentsMargins(6, 4, 6, 4)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(1, 1)

        # ── Row 0: Find ──────────────────────────────────────────────────
        self._btn_close = _CloseBtn()
        self._btn_close.setToolTip("Close  (Esc)")
        self._btn_close.clicked.connect(self.hide_bar)
        grid.addWidget(self._btn_close, 0, 0, Qt.AlignmentFlag.AlignVCenter)

        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("Search...")
        self._find_input.textChanged.connect(self._on_text_changed)
        self._find_input.returnPressed.connect(self.find_next)
        grid.addWidget(self._find_input, 0, 1)

        # Right side of find row: nav + checkboxes + count
        r0 = QHBoxLayout()
        r0.setSpacing(3)
        r0.setContentsMargins(0, 0, 0, 0)

        self._btn_prev = QPushButton()
        self._btn_prev.setIcon(ic("arrow_up"))
        self._btn_prev.setFixedSize(20, 18)
        self._btn_prev.setStyleSheet(ss_icon)
        self._btn_prev.setToolTip("Previous  (Shift+F3)")
        self._btn_prev.clicked.connect(self.find_prev)
        r0.addWidget(self._btn_prev)

        self._btn_next = QPushButton()
        self._btn_next.setIcon(ic("arrow_down"))
        self._btn_next.setFixedSize(20, 18)
        self._btn_next.setStyleSheet(ss_icon)
        self._btn_next.setToolTip("Next  (F3)")
        self._btn_next.clicked.connect(self.find_next)
        r0.addWidget(self._btn_next)

        r0.addSpacing(4)

        self._cb_case = QCheckBox("Aa")
        self._cb_case.setStyleSheet(ss_cb)
        self._cb_case.setToolTip("Match case")
        self._cb_case.stateChanged.connect(self._on_text_changed)
        r0.addWidget(self._cb_case)

        self._cb_word = QCheckBox("\\b")
        self._cb_word.setStyleSheet(ss_cb)
        self._cb_word.setToolTip("Whole word")
        self._cb_word.stateChanged.connect(self._on_text_changed)
        r0.addWidget(self._cb_word)

        self._cb_regex = QCheckBox(".*")
        self._cb_regex.setStyleSheet(ss_cb)
        self._cb_regex.setToolTip("Regular expression")
        self._cb_regex.stateChanged.connect(self._on_text_changed)
        r0.addWidget(self._cb_regex)

        r0.addSpacing(4)

        self._lbl_count = QLabel("")
        self._lbl_count.setFixedWidth(88)
        self._lbl_count.setStyleSheet("color:#8E8E93;font-size:11px;")
        r0.addWidget(self._lbl_count)

        r0w = QWidget()
        r0w.setLayout(r0)
        grid.addWidget(r0w, 0, 2)

        # ── Row 1: Replace ───────────────────────────────────────────────
        # col 0 is empty (aligns with close btn space above)
        # col 1 = replace input (same column as find input → same width guaranteed)
        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("Replace...")
        self._replace_input.returnPressed.connect(self.replace_one)
        grid.addWidget(self._replace_input, 1, 1)

        r1 = QHBoxLayout()
        r1.setSpacing(3)
        r1.setContentsMargins(0, 0, 0, 0)

        self._btn_replace = QPushButton("Replace")
        self._btn_replace.setStyleSheet(ss_btn)
        self._btn_replace.clicked.connect(self.replace_one)
        r1.addWidget(self._btn_replace)

        self._btn_replace_all = QPushButton("Replace All")
        self._btn_replace_all.setStyleSheet(ss_btn)
        self._btn_replace_all.clicked.connect(self.replace_all)
        r1.addWidget(self._btn_replace_all)

        r1.addStretch()

        r1w = QWidget()
        r1w.setLayout(r1)
        grid.addWidget(r1w, 1, 2)

        self.setFixedHeight(60)
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtGui import QColor as _QColor
        _shadow = QGraphicsDropShadowEffect(self)
        _shadow.setBlurRadius(16)
        _shadow.setOffset(0, -4)
        _shadow.setColor(_QColor(0, 0, 0, 80))
        self.setGraphicsEffect(_shadow)
        self._apply_theme()

    def _apply_theme(self):
        t   = ThemeManager.current()
        bg  = t["bg_toolbar"]
        fg  = t["fg_primary"]
        fg2 = t["fg_secondary"]
        fg_m= t["fg_muted"]
        brd = t["border"]
        bgi = t["bg_input"]
        acc = t["accent"]
        hov = t["bg_hover"]
        self.setStyleSheet(f"""
            FindBar {{
                background: {bg};
                border-top: 1px solid {brd};
            }}
            QLineEdit {{
                background: {bgi};
                color: {fg};
                border: 1px solid {brd};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 12px;
                selection-background-color: {acc};
            }}
            QLineEdit:focus {{
                border-color: {acc};
            }}
            QCheckBox {{
                color: {fg2};
                font-size: 11px;
                spacing: 4px;
            }}
            QCheckBox::indicator {{
                width: 12px;
                height: 12px;
                border: 1px solid {brd};
                border-radius: 2px;
                background: {bgi};
            }}
            QCheckBox::indicator:checked {{
                background: {acc};
                border-color: {acc};
            }}
            QPushButton {{
                background: transparent;
                color: {fg2};
                border: 1px solid {brd};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                min-width: 0;
                min-height: 0;
            }}
            QPushButton:hover {{
                background: {hov};
            }}
        """)
        self._lbl_count.setStyleSheet(f"color: {fg_m}; font-size: 11px;")

    def set_editor(self, editor):
        if self._editor is not None:
            self._clear_highlights()
        self._editor = editor

    def show_bar(self, replace=False):
        self.setVisible(True)
        if self._editor:
            sel = self._editor.textCursor().selectedText()
            if sel and "\u2029" not in sel:
                self._find_input.setText(sel)
        self._find_input.selectAll()
        self._find_input.setFocus()
        self._update_highlights()

    def hide_bar(self):
        self._clear_highlights()
        # Clear minimap and scrollbar overlay search ticks
        minimap = getattr(self, "_minimap", None)
        if minimap:
            minimap.set_search_lines([])
        overlay = getattr(self, "_scrollbar_overlay", None)
        if overlay:
            overlay.clear()
        self.setVisible(False)
        self.closed.emit()
        if self._editor:
            self._editor.setFocus()

    def refresh_icons(self):
        dark = ThemeManager.is_dark()
        ic = lambda name: get_icon(name, toolbar_color(dark), 13)
        self._btn_prev.setIcon(ic("arrow_up"))
        self._btn_next.setIcon(ic("arrow_down"))

    def find_next(self): self._find(True)
    def find_prev(self): self._find(False)

    def _find_non_ts(self, start_cursor, flags):
        """Find next match skipping timestamp blocks. Returns null cursor if none found."""
        doc = self._editor.document()
        q = self._query()
        cursor = start_cursor
        while True:
            found = doc.find(q, cursor, flags)
            if found.isNull():
                return found
            if not _is_timestamp_block(found.block()):
                return found
            cursor = found

    def _find(self, forward):
        if not self._editor or not self._query():
            return
        try:
            flags = self._flags(forward)
            doc = self._editor.document()
            found = self._find_non_ts(self._editor.textCursor(), flags)
            if found.isNull():
                # Wrap around
                c = QTextCursor(doc)
                c.movePosition(QTextCursor.MoveOperation.Start if forward
                               else QTextCursor.MoveOperation.End)
                found = self._find_non_ts(c, flags)
                if not found.isNull():
                    self._editor.setTextCursor(found)
                    self._lbl_count.setText("Wrapped")
                    self._lbl_count.setStyleSheet("color:#FF9500;font-size:11px;")
                    QTimer.singleShot(1200, self._update_highlights)
            else:
                self._editor.setTextCursor(found)
                self._update_highlights()
        except Exception:
            pass

    def _flags(self, forward=True):
        f = QTextDocument.FindFlag(0)
        if self._cb_case.isChecked():
            f |= QTextDocument.FindFlag.FindCaseSensitively
        if self._cb_word.isChecked():
            f |= QTextDocument.FindFlag.FindWholeWords
        if self._cb_regex.isChecked():
            f |= QTextDocument.FindFlag.FindRegularExpression
        if not forward:
            f |= QTextDocument.FindFlag.FindBackward
        return f

    def _query(self): return self._find_input.text()

    def replace_one(self):
        if not self._editor or not self._query(): return
        cursor = self._editor.textCursor()
        q, repl = self._query(), self._replace_input.text()
        sel = cursor.selectedText()
        in_ts = _is_timestamp_block(cursor.block())
        if not in_ts and \
           ((self._cb_case.isChecked() and sel == q) or
            (not self._cb_case.isChecked() and sel.lower() == q.lower())):
            cursor.beginEditBlock()
            cursor.insertText(repl)
            cursor.endEditBlock()
        self.find_next()
        self._editor.setFocus()

    def replace_all(self):
        if not self._editor or not self._query(): return
        q, repl = self._query(), self._replace_input.text()
        doc = self._editor.document()
        flags = QTextDocument.FindFlag(0)
        if self._cb_case.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self._cb_regex.isChecked():
            flags |= QTextDocument.FindFlag.FindRegularExpression
        count = 0
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.beginEditBlock()
        while True:
            found = doc.find(q, cursor, flags)
            if found.isNull(): break
            if _is_timestamp_block(found.block()):
                cursor = found
                continue
            found.insertText(repl)
            cursor = found
            count += 1
        cursor.endEditBlock()
        if count:
            self._lbl_count.setText(f"Replaced {count}")
            self._lbl_count.setStyleSheet("color:#30D158;font-size:11px;")
        else:
            self._lbl_count.setText("No matches")
            self._lbl_count.setStyleSheet("color:#FF453A;font-size:11px;")
        self._clear_highlights()
        self._editor.setFocus()

    def _on_text_changed(self, *_): self._update_highlights()

    def _update_highlights(self):
        if not self._editor: return
        self._clear_highlights()
        q = self._query()
        if not q:
            self._lbl_count.setText("")
            return
        try:
            colors = ThemeManager.find_colors()
            mfmt = QTextCharFormat()
            mfmt.setBackground(QColor(colors["match_bg"]))
            mfmt.setForeground(QColor(colors["match_fg"]))
            doc = self._editor.document()
            flags = QTextDocument.FindFlag(0)
            if self._cb_case.isChecked():
                flags |= QTextDocument.FindFlag.FindCaseSensitively
            if self._cb_regex.isChecked():
                flags |= QTextDocument.FindFlag.FindRegularExpression
            cur_sel = self._editor.textCursor()
            cs, ce = cur_sel.selectionStart(), cur_sel.selectionEnd()
            count, sels = 0, []
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            while True:
                found = doc.find(q, cursor, flags)
                if found.isNull(): break
                cursor = found
                if _is_timestamp_block(found.block()):
                    continue
                count += 1
                sel = QTextEdit.ExtraSelection()
                if found.selectionStart() == cs and found.selectionEnd() == ce:
                    sel.format.setBackground(QColor(colors["cur_bg"]))
                    sel.format.setForeground(QColor(colors["cur_fg"]))
                else:
                    sel.format = mfmt
                sel.cursor = found
                sels.append(sel)
            self._match_selections = sels
            self._editor.setExtraSelections(self._editor.extraSelections() + sels)
            if count == 0:
                self._lbl_count.setText("No matches")
                self._lbl_count.setStyleSheet("color:#FF453A;font-size:11px;")
            else:
                self._lbl_count.setText(f"{count} match{'es' if count!=1 else ''}")
                self._lbl_count.setStyleSheet("color:#8E8E93;font-size:11px;")
        except Exception:
            self._lbl_count.setText("Invalid pattern")
            self._lbl_count.setStyleSheet("color:#FF453A;font-size:11px;")
        # Emit block numbers for minimap tick marks
        self._emit_search_blocks()

    def _emit_search_blocks(self):
        """Collect block numbers of search matches and notify any connected minimap."""
        if not self._editor:
            return
        minimap = getattr(self, "_minimap", None)
        if minimap is None:
            return
        q = self._query()
        if not q:
            minimap.set_search_lines([])
            return
        try:
            doc   = self._editor.document()
            flags = QTextDocument.FindFlag(0)
            if self._cb_case.isChecked():
                flags |= QTextDocument.FindFlag.FindCaseSensitively
            if self._cb_regex.isChecked():
                flags |= QTextDocument.FindFlag.FindRegularExpression
            blocks = []
            cur = QTextCursor(doc)
            cur.movePosition(QTextCursor.MoveOperation.Start)
            while len(blocks) < 2000:
                found = doc.find(q, cur, flags)
                if found.isNull():
                    break
                cur = found
                if _is_timestamp_block(found.block()):
                    continue
                blocks.append(found.block().blockNumber())
            minimap.set_search_lines(blocks)
        except Exception:
            pass
        # Also update scrollbar overlay
        overlay = getattr(self, "_scrollbar_overlay", None)
        if overlay and self._editor:
            n = self._editor.document().blockCount()
            if blocks:
                overlay.set_search_lines(blocks, n)
            else:
                overlay.clear()

    def set_minimap(self, minimap):
        """Wire the minimap so find highlights appear as tick marks."""
        self._minimap = minimap

    def set_scrollbar_overlay(self, overlay):
        """Wire the scrollbar overlay for tick marks on the scrollbar."""
        self._scrollbar_overlay = overlay

    def _clear_highlights(self):
        if not self._editor: return
        self._editor.setExtraSelections(
            [s for s in self._editor.extraSelections()
             if s not in self._match_selections])
        self._match_selections = []

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_bar()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._find_input.hasFocus():
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.find_prev()
            else:
                self.find_next()
        else:
            super().keyPressEvent(event)
