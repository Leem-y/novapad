from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from utils.signatures import SignatureItem


def _hotkey_label(mods: int, key: str) -> str:
    parts: list[str] = []
    if mods & 2:
        parts.append("Ctrl")
    if mods & 1:
        parts.append("Shift")
    if mods & 4:
        parts.append("Alt")
    if key:
        parts.append(key.upper())
    return "+".join(parts)


class HotkeyEdit(QLineEdit):
    """Captures a simple Ctrl/Shift/Alt + key string (A-Z, 0-9, F1-F24)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.mods = 0
        self.key = ""
        self.setPlaceholderText("Press hotkey…")

    def set_value(self, mods: int, key: str):
        self.mods = int(mods or 0)
        self.key = (key or "").upper()
        self.setText(_hotkey_label(self.mods, self.key))

    def keyPressEvent(self, e):
        k = e.key()
        mods = e.modifiers()
        m = 0
        if mods & Qt.KeyboardModifier.ShiftModifier:
            m |= 1
        if mods & Qt.KeyboardModifier.ControlModifier:
            m |= 2
        if mods & Qt.KeyboardModifier.AltModifier:
            m |= 4

        key = ""
        if Qt.Key.Key_A <= k <= Qt.Key.Key_Z:
            key = chr(ord("A") + (k - Qt.Key.Key_A))
        elif Qt.Key.Key_0 <= k <= Qt.Key.Key_9:
            key = chr(ord("0") + (k - Qt.Key.Key_0))
        elif Qt.Key.Key_F1 <= k <= Qt.Key.Key_F24:
            key = f"F{1 + (k - Qt.Key.Key_F1)}"
        elif k in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.set_value(0, "")
            return
        else:
            # ignore unsupported keys
            e.accept()
            return

        self.set_value(m, key)
        e.accept()

    def keyReleaseEvent(self, e):
        # Prevent key releases (especially modifier-only releases) from bubbling
        # into parent dialogs and triggering unrelated actions.
        e.accept()


class SignatureEditDialog(QDialog):
    def __init__(self, parent: QWidget, item: SignatureItem):
        super().__init__(parent)
        self.setWindowTitle("Edit Signature")
        self.setModal(True)
        self._item = item

        self._name = QLineEdit(self)
        self._name.setText(item.name)
        self._name.setMaxLength(80)

        self._hotkey = HotkeyEdit(self)
        self._hotkey.set_value(item.hotkey_mods, item.hotkey_key)

        self._text = QTextEdit(self)
        self._text.setPlainText(item.text)
        self._text.setMinimumHeight(160)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._text.setFont(mono)

        form = QFormLayout()
        form.addRow("Name", self._name)
        form.addRow("Hotkey", self._hotkey)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Text"))
        layout.addWidget(self._text)
        layout.addWidget(buttons)

    def result_item(self) -> SignatureItem:
        name = (self._name.text() or "Untitled").strip()
        text = self._text.toPlainText()
        return replace(
            self._item,
            name=name,
            text=text,
            hotkey_mods=int(self._hotkey.mods),
            hotkey_key=(self._hotkey.key or "").upper(),
        )


class SignatureManagerDialog(QDialog):
    items_changed = pyqtSignal()
    autopaste_changed = pyqtSignal(bool)

    def __init__(self, parent: QWidget, items: list[SignatureItem]):
        super().__init__(parent)
        self.setWindowTitle("Signature Manager")
        self.setModal(False)
        self.resize(760, 520)

        self._items: list[SignatureItem] = list(items)

        self._tabs = QTabWidget(self)
        self._tab_signatures = QWidget(self)
        self._tabs.addTab(self._tab_signatures, "Signature")

        self._toolbar = QToolBar(self)
        self._toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self._toolbar.setIconSize(self._toolbar.iconSize().expandedTo(self._toolbar.iconSize()))

        self._act_add = QAction("Add", self)
        self._act_edit = QAction("Edit", self)
        self._act_delete = QAction("Delete", self)
        self._act_autopaste = QAction("Auto Paste (Ctrl+V)", self)
        self._act_autopaste.setCheckable(True)
        self._act_autopaste.setToolTip(
            "When on, NovaPad sets the clipboard then sends a synthetic Ctrl+V to the focused app. "
            "Some apps block automated paste; turn off for clipboard-only, then press Ctrl+V yourself."
        )
        self._act_add.setShortcut(QKeySequence.StandardKey.New)
        self._act_edit.setShortcut(QKeySequence(Qt.Key.Key_Return))
        self._act_delete.setShortcut(QKeySequence.StandardKey.Delete)

        self._toolbar.addAction(self._act_add)
        self._toolbar.addAction(self._act_edit)
        self._toolbar.addAction(self._act_delete)
        self._toolbar.addSeparator()
        self._toolbar.addAction(self._act_autopaste)

        self._hotkey_status: dict[str, bool] = {}  # id -> registered?

        self._table = QTableWidget(self)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Name / Text", "Hotkey", "Status", "On"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setDefaultSectionSize(140)
        self._table.setSortingEnabled(False)
        self._table.setAlternatingRowColors(True)

        # Compact, “utility panel” feel
        self._table.setStyleSheet(
            """
            QTableWidget { gridline-color: rgba(0,0,0,40); }
            QHeaderView::section { padding: 4px 8px; }
            QTableWidget::item { padding: 4px 8px; }
            """
        )

        tab_layout = QVBoxLayout(self._tab_signatures)
        tab_layout.setContentsMargins(8, 8, 8, 8)
        tab_layout.addWidget(self._toolbar)
        tab_layout.addWidget(self._table, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_close = QPushButton("Close", self)
        btn_close.clicked.connect(self.close)
        bottom.addWidget(btn_close)

        root = QVBoxLayout(self)
        root.addWidget(self._tabs, 1)
        root.addLayout(bottom)

        self._act_add.triggered.connect(self._on_add)
        self._act_edit.triggered.connect(self._on_edit)
        self._act_delete.triggered.connect(self._on_delete)
        self._act_autopaste.toggled.connect(self.autopaste_changed.emit)
        self._table.itemDoubleClicked.connect(lambda *_: self._on_edit())

        self._rebuild()

    def set_autopaste_checked(self, on: bool):
        self._act_autopaste.blockSignals(True)
        try:
            self._act_autopaste.setChecked(bool(on))
        finally:
            self._act_autopaste.blockSignals(False)

    def items(self) -> list[SignatureItem]:
        return list(self._items)

    def selected_id(self) -> str | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row].id

    def _rebuild(self):
        self._table.setRowCount(len(self._items))
        for r, it in enumerate(self._items):
            preview = it.text.replace("\r\n", "\n").replace("\r", "\n").strip()
            if len(preview) > 90:
                preview = preview[:90].rstrip() + "…"
            name_text = f"{it.name}\n{preview}" if preview else it.name

            item0 = QTableWidgetItem(name_text)
            item1 = QTableWidgetItem(_hotkey_label(it.hotkey_mods, it.hotkey_key))
            ok = self._hotkey_status.get(it.id)
            if not (it.hotkey_key and it.hotkey_mods):
                status_txt = ""
            elif ok is True:
                status_txt = "Registered"
            elif ok is False:
                status_txt = "In use"
            else:
                status_txt = "—"
            item2 = QTableWidgetItem(status_txt)
            item3 = QTableWidgetItem("Yes" if it.enabled else "No")

            item0.setData(Qt.ItemDataRole.UserRole, it.id)
            item2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self._table.setItem(r, 0, item0)
            self._table.setItem(r, 1, item1)
            self._table.setItem(r, 2, item2)
            self._table.setItem(r, 3, item3)

        self._table.setColumnWidth(0, 470)
        self._table.setColumnWidth(1, 140)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 60)
        if self._items:
            self._table.selectRow(0)

    def set_hotkey_status(self, status_by_id: dict[str, bool]):
        self._hotkey_status = dict(status_by_id or {})
        self._rebuild()

    def _on_add(self):
        import uuid

        it = SignatureItem(id=uuid.uuid4().hex, name="New", text="", hotkey_mods=0, hotkey_key="", enabled=True)
        dlg = SignatureEditDialog(self, it)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._items.append(dlg.result_item())
            self._rebuild()
            self.items_changed.emit()

    def _on_edit(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._items):
            return
        it = self._items[row]
        dlg = SignatureEditDialog(self, it)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._items[row] = dlg.result_item()
            self._rebuild()
            self._table.selectRow(row)
            self.items_changed.emit()

    def _on_delete(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._items):
            return
        del self._items[row]
        self._rebuild()
        self.items_changed.emit()

