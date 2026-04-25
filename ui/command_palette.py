# ui/command_palette.py -- NovaPad Command Palette
#
# Ctrl+P opens a floating search box.
# Type to fuzzy-filter all menu actions. Enter to run. Esc to close.

from __future__ import annotations
import re
from PyQt6.QtCore    import Qt, QStringListModel, pyqtSignal
from PyQt6.QtGui     import QKeyEvent
from PyQt6.QtWidgets import (
    QCompleter, QDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QVBoxLayout, QWidget,
)


class CommandPalette(QDialog):
    """Floating command palette. Pass a list of (label, callable) pairs."""

    def __init__(self, commands: list[tuple[str, object]], parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._commands = commands
        self._build()
        self._filter("")

    def _build(self):
        from ui.theme import ThemeManager
        t = ThemeManager.current()
        bg    = t["bg_menu"]
        brd   = t["border"]
        inp   = t["bg_input"]
        fg    = t["fg_primary"]
        fg2   = t["fg_secondary"]
        acc   = t["accent"]
        hov   = t["bg_hover"]

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        container = QWidget(self)
        container.setObjectName("PaletteContainer")
        container.setStyleSheet(f"""
            QWidget#PaletteContainer {{
                background: {bg};
                border: 1px solid {brd};
                border-radius: 12px;
            }}
        """)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(8, 8, 8, 8)
        inner.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command…")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {inp};
                color: {fg};
                border: 1.5px solid {brd};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {acc}; }}
        """)
        self._input.textChanged.connect(self._filter)
        self._input.installEventFilter(self)
        inner.addWidget(self._input)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {fg};
                font-size: 13px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 10px;
                border-radius: 6px;
                color: {fg};
            }}
            QListWidget::item:selected {{
                background: {acc};
                color: #FFFFFF;
            }}
            QListWidget::item:hover:!selected {{
                background: {hov};
            }}
        """)
        self._list.itemActivated.connect(self._run_selected)
        self._list.setMaximumHeight(320)
        inner.addWidget(self._list)

        lay.addWidget(container)
        self.setFixedWidth(480)

    def _filter(self, text: str):
        self._list.clear()
        q = text.lower().strip()
        for label, fn in self._commands:
            if not q or self._fuzzy_match(q, label.lower()):
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, fn)
                self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    @staticmethod
    def _fuzzy_match(query: str, text: str) -> bool:
        idx = 0
        for ch in query:
            found = text.find(ch, idx)
            if found < 0:
                return False
            idx = found + 1
        return True

    def _run_selected(self, item=None):
        item = item or self._list.currentItem()
        if item:
            fn = item.data(Qt.ItemDataRole.UserRole)
            self.close()
            if callable(fn):
                fn()

    def eventFilter(self, obj, event):
        if obj is self._input and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Down:
                self._list.setFocus()
                return True
            if event.key() == Qt.Key.Key_Return:
                self._run_selected()
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.close()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._run_selected()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._input.setFocus()
        self._input.selectAll()
