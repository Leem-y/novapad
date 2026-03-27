# ui/dialogs.py -- Themed replacement dialogs for NovaPad
# Replaces QMessageBox / QProgressDialog with fully themed versions.

from __future__ import annotations
from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)


def _qss(t: dict) -> str:
    return f"""
        QDialog {{
            background: {t['bg_window']};
            border: 1px solid {t['border']};
            border-radius: 12px;
        }}
        QLabel {{
            background: transparent;
            color: {t['fg_primary']};
            border: none;
        }}
        QPushButton {{
            background: {t['bg_button']};
            color: {t['fg_primary']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            padding: 6px 18px;
            font-size: 12px;
            font-weight: 500;
            min-width: 80px;
            min-height: 28px;
        }}
        QPushButton:hover   {{ background: {t['bg_hover']}; }}
        QPushButton:pressed {{ background: {t['bg_pressed']}; }}
        QPushButton#primary {{
            background: {t['accent']};
            color: #FFFFFF;
            border-color: {t['accent_hover']};
        }}
        QPushButton#primary:hover {{ background: {t['accent_hover']}; }}
        QProgressBar {{
            background: {t['bg_input']};
            border: 1px solid {t['border']};
            border-radius: 5px;
            height: 8px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background: {t['accent']};
            border-radius: 4px;
        }}
    """


class ThemedDialog(QDialog):
    """Base frameless themed dialog."""

    def __init__(self, parent=None, title: str = "NovaPad"):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        from ui.theme import ThemeManager
        self._t = ThemeManager.current()
        self.setStyleSheet(_qss(self._t))
        self._drag_pos = None

        # Outer layout (transparent, gives shadow space)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        # Inner card
        self._card = QWidget(self)
        self._card.setObjectName("card")
        self._card.setStyleSheet(f"""
            QWidget#card {{
                background: {self._t['bg_window']};
                border: 1px solid {self._t['border']};
                border-radius: 12px;
            }}
        """)
        outer.addWidget(self._card)

        self._inner = QVBoxLayout(self._card)
        self._inner.setContentsMargins(24, 20, 24, 20)
        self._inner.setSpacing(12)

        # Title bar row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color:{self._t['fg_primary']}; font-weight:700; "
            f"font-size:13px; background:transparent; border:none;"
        )
        title_row.addWidget(self._title_lbl)
        title_row.addStretch()

        # Close X
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self._t['fg_muted']};
                border: none;
                font-size: 13px;
                min-width: 0; min-height: 0;
                padding: 2px 6px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {self._t['bg_hover']};
                color: {self._t['fg_primary']};
            }}
        """)
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(close_btn)
        self._inner.addLayout(title_row)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{self._t['separator']}; border:none;")
        self._inner.addWidget(sep)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _btn_row(self, buttons: list[tuple[str, str, object]]) -> QHBoxLayout:
        """
        buttons: list of (label, object_name, callback)
        object_name='primary' for accent style.
        """
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()
        for label, obj_name, cb in buttons:
            b = QPushButton(label)
            if obj_name:
                b.setObjectName(obj_name)
                b.setStyleSheet(b.styleSheet())  # force re-eval
            b.clicked.connect(cb)
            row.addWidget(b)
        return row


class ThemedMessageBox(ThemedDialog):
    """Themed replacement for QMessageBox."""

    # Return values
    ACCEPTED = 1
    REJECTED = 0

    def __init__(self, parent, title: str, message: str,
                 buttons: list[tuple[str, str]] | None = None,
                 icon: str = "ℹ"):
        """
        buttons: list of (label, role) where role is 'primary'|'secondary'|'danger'
        Returns button label via .exec() → use .clicked_label
        """
        super().__init__(parent, title)
        self.clicked_label = None

        # Icon + message row
        body_row = QHBoxLayout()
        body_row.setSpacing(14)
        body_row.setContentsMargins(0, 4, 0, 4)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"font-size:28px; color:{self._t['accent']}; "
            f"background:transparent; border:none;"
        )
        icon_lbl.setFixedWidth(36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        body_row.addWidget(icon_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"color:{self._t['fg_primary']}; font-size:13px; "
            f"background:transparent; border:none; line-height:1.5;"
        )
        msg_lbl.setMinimumWidth(300)
        msg_lbl.setMaximumWidth(440)
        body_row.addWidget(msg_lbl, 1)
        self._inner.addLayout(body_row)
        self._inner.addSpacing(4)

        # Buttons
        if not buttons:
            buttons = [("OK", "primary")]

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        for label, role in buttons:
            b = QPushButton(label)
            if role == "primary":
                b.setObjectName("primary")
                b.setStyleSheet(f"""
                    QPushButton {{
                        background: {self._t['accent']};
                        color: #FFFFFF;
                        border: none;
                        border-radius: 8px;
                        padding: 6px 18px;
                        font-size: 12px;
                        font-weight: 600;
                        min-width: 80px;
                        min-height: 28px;
                    }}
                    QPushButton:hover {{ background: {self._t['accent_hover']}; }}
                """)
            elif role == "danger":
                b.setStyleSheet(f"""
                    QPushButton {{
                        background: #E53E3E;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 8px;
                        padding: 6px 18px;
                        font-size: 12px;
                        font-weight: 600;
                        min-width: 80px;
                        min-height: 28px;
                    }}
                    QPushButton:hover {{ background: #C53030; }}
                """)
            else:
                b.setStyleSheet(f"""
                    QPushButton {{
                        background: {self._t['bg_button']};
                        color: {self._t['fg_primary']};
                        border: 1px solid {self._t['border']};
                        border-radius: 8px;
                        padding: 6px 18px;
                        font-size: 12px;
                        font-weight: 500;
                        min-width: 80px;
                        min-height: 28px;
                    }}
                    QPushButton:hover {{ background: {self._t['bg_hover']}; }}
                """)
            b.clicked.connect(lambda checked, lbl=label: self._on_click(lbl))
            btn_row.addWidget(b)
        self._inner.addLayout(btn_row)
        self.adjustSize()

    def _on_click(self, label: str):
        self.clicked_label = label
        self.accept()


class ThemedProgressDialog(ThemedDialog):
    """Themed replacement for QProgressDialog."""

    def __init__(self, parent, title: str, message: str,
                 can_cancel: bool = True):
        super().__init__(parent, title)
        self._cancelled = False

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"color:{self._t['fg_secondary']}; font-size:12px; "
            f"background:transparent; border:none;"
        )
        self._inner.addWidget(msg_lbl)
        self._msg_lbl = msg_lbl

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(8)
        self._bar.setTextVisible(False)
        self._inner.addWidget(self._bar)

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setStyleSheet(
            f"color:{self._t['fg_muted']}; font-size:11px; "
            f"background:transparent; border:none;"
        )
        self._pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inner.addWidget(self._pct_lbl)

        if can_cancel:
            row = QHBoxLayout()
            row.addStretch()
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self._t['bg_button']};
                    color: {self._t['fg_primary']};
                    border: 1px solid {self._t['border']};
                    border-radius: 8px;
                    padding: 5px 16px;
                    font-size: 12px;
                    min-width: 70px;
                    min-height: 26px;
                }}
                QPushButton:hover {{ background: {self._t['bg_hover']}; }}
            """)
            cancel_btn.clicked.connect(self._cancel)
            row.addWidget(cancel_btn)
            self._inner.addLayout(row)

        self.setFixedWidth(380)
        self.adjustSize()

    def setValue(self, v: int):
        self._bar.setValue(v)
        self._pct_lbl.setText(f"{v}%")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def setLabelText(self, text: str):
        self._msg_lbl.setText(text)

    def wasCanceled(self) -> bool:
        return self._cancelled

    def _cancel(self):
        self._cancelled = True
        self.reject()


# ── Convenience wrappers matching QMessageBox API ────────────────────────────

def themed_info(parent, title: str, message: str):
    d = ThemedMessageBox(parent, title, message, [("OK", "primary")], "ℹ")
    d.exec()

def themed_error(parent, title: str, message: str):
    d = ThemedMessageBox(parent, title, message, [("OK", "primary")], "✕")
    d.exec()

def themed_question(parent, title: str, message: str,
                    btn_yes="Yes", btn_no="No", btn_cancel=None):
    """Returns the label of the clicked button."""
    buttons = [(btn_yes, "primary"), (btn_no, "")]
    if btn_cancel:
        buttons.append((btn_cancel, ""))
    d = ThemedMessageBox(parent, title, message, buttons, "?")
    d.exec()
    return d.clicked_label

def themed_update(parent, title: str, message: str):
    """Update dialog with 'Update Now' + 'Later'."""
    d = ThemedMessageBox(parent, title, message,
                         [("Update Now", "primary"), ("Later", "")], "⬆")
    d.exec()
    return d.clicked_label == "Update Now"
