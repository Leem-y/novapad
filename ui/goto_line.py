# ui/goto_line.py -- NovaPad Go-to-Line bar
#
# A small inline widget that appears above the status bar on Ctrl+G.
# User types a number, presses Enter to jump, Esc to dismiss.
# The target line is briefly highlighted in the gutter.

from __future__ import annotations

from PyQt6.QtCore    import Qt, QTimer, pyqtSignal
from PyQt6.QtGui     import QColor, QIntValidator, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QWidget,
)


class GotoLineBar(QWidget):
    """
    Inline go-to-line widget.
    Show with show_bar(), hide with hide_bar().
    """

    closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("GotoLineBar")
        self.setFixedHeight(40)
        self._editor = None
        self._flash_selections: list = []
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 5, 10, 5)
        lay.setSpacing(8)

        lbl = QLabel("Go to line:")
        lbl.setStyleSheet("font-size: 12px;")
        lay.addWidget(lbl)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Line number…")
        self._input.setFixedWidth(120)
        self._input.setValidator(QIntValidator(1, 999999))
        self._input.returnPressed.connect(self._jump)
        lay.addWidget(self._input)

        self._lbl_info = QLabel("")
        self._lbl_info.setStyleSheet("color: #8E8E93; font-size: 11px;")
        lay.addWidget(self._lbl_info)

        lay.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(56)
        btn_close.clicked.connect(self.hide_bar)
        lay.addWidget(btn_close)

    # -- Public API ----------------------------------------------------------

    def set_editor(self, editor):
        self._editor = editor

    def show_bar(self):
        self.setVisible(True)
        if self._editor:
            doc   = self._editor.document()
            count = doc.blockCount()
            self._input.setValidator(QIntValidator(1, count))
            self._lbl_info.setText(f"(1 – {count})")
        self._input.selectAll()
        self._input.setFocus()

    def hide_bar(self):
        self._clear_flash()
        self.setVisible(False)
        self.closed.emit()
        if self._editor:
            self._editor.setFocus()

    # -- Jump logic ----------------------------------------------------------

    def _jump(self):
        if not self._editor:
            return
        text = self._input.text().strip()
        if not text:
            return

        target = int(text) - 1          # 0-based block number
        doc    = self._editor.document()
        count  = doc.blockCount()

        if target < 0 or target >= count:
            self._lbl_info.setText(f"  Line {text} out of range (1–{count})")
            self._lbl_info.setStyleSheet("color: #FF453A; font-size: 11px;")
            return

        block  = doc.findBlockByNumber(target)
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        self._editor.setTextCursor(cursor)
        self._editor.ensureCursorVisible()

        # Brief flash highlight on the target line
        self._flash_line(block)
        self.hide_bar()

    def _flash_line(self, block):
        """Highlight the target line for 700 ms then clear."""
        from PyQt6.QtGui import QTextFormat
        self._clear_flash()
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor("#0A84FF44"))
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = QTextCursor(block)
        sel.cursor.clearSelection()
        self._flash_selections = [sel]
        existing = self._editor.extraSelections()
        self._editor.setExtraSelections(existing + self._flash_selections)
        QTimer.singleShot(700, self._clear_flash)

    def _clear_flash(self):
        if self._editor and self._flash_selections:
            existing = self._editor.extraSelections()
            cleaned  = [s for s in existing if s not in self._flash_selections]
            self._editor.setExtraSelections(cleaned)
        self._flash_selections = []

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_bar()
        else:
            super().keyPressEvent(event)
