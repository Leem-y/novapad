from __future__ import annotations

import datetime as _dt

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QCalendarWidget, QDialog, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ui.theme import ThemeManager


class DatePickerDialog(QDialog):
    """
    Small themed calendar popup for selecting a date.
    """

    def __init__(self, parent: QWidget | None = None, initial: _dt.date | None = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._selected: _dt.date | None = None
        self._build(initial or _dt.date.today())

    def _build(self, initial: _dt.date):
        t = ThemeManager.current()
        bg = t["bg_menu"]
        brd = t["border"]
        fg = t["fg_primary"]
        fg2 = t["fg_secondary"]
        acc = t["accent"]
        hov = t["bg_hover"]
        prs = t.get("bg_pressed", hov)

        container = QWidget(self)
        container.setObjectName("DatePickerContainer")
        container.setStyleSheet(f"""
            QWidget#DatePickerContainer {{
                background: {bg};
                border: 1px solid {brd};
                border-radius: 12px;
            }}
            QCalendarWidget QWidget {{
                background: {bg};
                color: {fg};
            }}
            QCalendarWidget QAbstractItemView {{
                selection-background-color: {acc};
                selection-color: #FFFFFF;
                background: {bg};
                color: {fg};
                outline: none;
            }}
            QCalendarWidget QAbstractItemView::item:hover {{
                background: {hov};
                border-radius: 6px;
            }}
            QCalendarWidget QToolButton {{
                color: {fg};
                background: transparent;
                border: none;
                padding: 6px 8px;
                border-radius: 8px;
            }}
            QCalendarWidget QToolButton:hover {{
                background: {hov};
            }}
            QCalendarWidget QToolButton:pressed {{
                background: {prs};
            }}
            QCalendarWidget QMenu {{
                background: {bg};
                color: {fg};
                border: 1px solid {brd};
                border-radius: 8px;
            }}
            QPushButton {{
                background: transparent;
                color: {fg2};
                border: 1px solid {brd};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                min-width: 84px;
            }}
            QPushButton:hover {{
                background: {hov};
            }}
            QPushButton#primary {{
                background: {acc};
                color: #FFFFFF;
                border-color: {acc};
                font-weight: 600;
            }}
            QPushButton#primary:hover {{
                background: {t.get('accent_hover', acc)};
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        lay = QVBoxLayout(container)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)

        cal = QCalendarWidget(container)
        cal.setAutoFillBackground(True)
        cal.setGridVisible(False)
        cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        cal.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        cal.setNavigationBarVisible(True)
        cal.setSelectedDate(QDate(initial.year, initial.month, initial.day))
        cal.clicked.connect(self._on_clicked)

        # Ensure the calendar honors the active theme even when Qt's global palette
        # (or platform defaults) would otherwise bleed through.
        pal = cal.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(bg))
        pal.setColor(QPalette.ColorRole.Base, QColor(bg))
        pal.setColor(QPalette.ColorRole.Button, QColor(bg))
        pal.setColor(QPalette.ColorRole.Text, QColor(fg))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(fg))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(fg))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(acc))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        cal.setPalette(pal)

        self._cal = cal
        lay.addWidget(cal)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton("Cancel", container)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        ok = QPushButton("Open", container)
        ok.setObjectName("primary")
        ok.clicked.connect(self._accept)
        btn_row.addWidget(ok)

        lay.addLayout(btn_row)
        self.adjustSize()

    def _on_clicked(self, qdate: QDate):
        self._selected = _dt.date(qdate.year(), qdate.month(), qdate.day())

    def _accept(self):
        qdate = self._cal.selectedDate()
        self._selected = _dt.date(qdate.year(), qdate.month(), qdate.day())
        self.accept()

    @property
    def selected_date(self) -> _dt.date | None:
        return self._selected


def pick_date(parent: QWidget | None = None, initial: _dt.date | None = None) -> _dt.date | None:
    dlg = DatePickerDialog(parent=parent, initial=initial)
    if dlg.exec():
        return dlg.selected_date
    return None

