# ui/theme_picker.py -- NovaPad Theme Picker  (v2)
# Rich per-theme swatches  +  crossfade transition overlay

from __future__ import annotations
from PyQt6.QtCore    import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui     import QColor, QPainter, QBrush, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
)
from ui.theme import THEMES, THEME_NAMES


# ─────────────────────────────────────────────────────────────────────────────
# Per-theme mini-editor preview swatch
# ─────────────────────────────────────────────────────────────────────────────

class ThemeSwatch(QWidget):
    """
    Tiny mock-editor: gutter, 4 syntax lines, cursor bar — real theme tokens.
    """
    W, H = 58, 38

    def __init__(self, theme_name: str, parent=None):
        super().__init__(parent)
        self._t = THEMES[theme_name]
        self.setFixedSize(self.W, self.H)

    def paintEvent(self, _):
        t  = self._t
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg     = QColor(t["bg_editor"])
        gut_fg = QColor(t["fg_muted"])
        accent = QColor(t["accent"])
        fg1    = QColor(t["fg_primary"])
        fg2    = QColor(t["fg_secondary"])
        fg3    = QColor(t["fg_muted"])
        sel    = QColor(t["sel_bg"]); sel.setAlpha(80)
        brd    = QColor(t["border"])
        cur_c  = QColor(t["fg_primary"])
        W, H   = self.W, self.H
        GUT    = 10

        # Background
        p.fillRect(0, 0, W, H, bg)

        # Gutter (same bg, just numbers)
        p.setPen(gut_fg)
        f = p.font(); f.setPointSize(4); f.setFamily("Segoe UI"); p.setFont(f)
        for i, n in enumerate([1, 2, 3, 4]):
            p.drawText(0, 5 + i * 8, GUT - 2, 6,
                       Qt.AlignmentFlag.AlignRight, str(n))

        # Subtle gutter line
        p.setPen(brd)
        p.drawLine(GUT, 0, GUT, H)

        # Selection highlight on row 0
        p.fillRect(GUT + 2, 4, W - GUT - 4, 7, sel)

        # Syntax lines: keyword, string, comment, plain
        p.setPen(Qt.PenStyle.NoPen)
        for col, w, y in [
            (accent, 22, 5),
            (fg2,    30, 13),
            (fg3,    18, 21),
            (fg1,    26, 29),
        ]:
            c = QColor(col); c.setAlpha(200)
            p.setBrush(QBrush(c))
            p.drawRoundedRect(GUT + 3, y, w, 4, 2, 2)

        # Cursor
        p.fillRect(GUT + 3 + 22, 4, 1, 7, cur_c)

        # Border
        p.setPen(brd)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(0, 0, W - 1, H - 1, 5, 5)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# Crossfade overlay
# ─────────────────────────────────────────────────────────────────────────────

class ThemeTransitionOverlay(QWidget):
    """
    Grabs a screenshot before theme switch, overlays it, fades it out.
    Result: smooth crossfade instead of instant snap.
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._px = QPixmap()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def capture(self):
        win = self.parent()
        self._px = win.grab()
        self.resize(win.size())
        self.raise_()
        self.show()

    def paintEvent(self, _):
        if not self._px.isNull():
            QPainter(self).drawPixmap(0, 0, self._px)

    def fade_out(self, duration_ms: int = 300):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setDuration(duration_ms)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._cleanup)
        anim.start()
        self._anim = anim

    def _cleanup(self):
        self.hide()
        self.setGraphicsEffect(None)
        self._px = QPixmap()


# ─────────────────────────────────────────────────────────────────────────────
# One row in the picker
# ─────────────────────────────────────────────────────────────────────────────

class _ThemeRow(QWidget):
    clicked = pyqtSignal()

    def __init__(self, name, is_active, acc, fg, hov, parent=None):
        super().__init__(parent)
        self._hov_color = hov
        self._hovered   = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(46)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 3, 6, 3)
        lay.setSpacing(8)

        lay.addWidget(ThemeSwatch(name))

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color:{acc if is_active else fg}; "
            f"font-size:11px; font-weight:{'600' if is_active else '400'}; "
            f"background:transparent; border:none;"
        )
        lay.addWidget(name_lbl, 1)

        if is_active:
            dot = QLabel("◆")
            dot.setStyleSheet(
                f"color:{acc}; font-size:7px; background:transparent; border:none;"
            )
            lay.addWidget(dot)

    def enterEvent(self, e):
        self._hovered = True; self.update()

    def leaveEvent(self, e):
        self._hovered = False; self.update()

    def paintEvent(self, e):
        if self._hovered:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            c = QColor(self._hov_color); c.setAlpha(160)
            p.setBrush(c)
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        super().paintEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


# ─────────────────────────────────────────────────────────────────────────────
# Theme picker dialog
# ─────────────────────────────────────────────────────────────────────────────

class ThemePicker(QDialog):

    def __init__(self, current: str, apply_fn, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._apply_fn = apply_fn
        self._current  = current
        self._build(current)

    def _build(self, current: str):
        from ui.theme import ThemeManager
        t   = ThemeManager.current()
        bg  = t["bg_menu"]
        brd = t["border"]
        fg1 = t["fg_primary"]
        fg2 = t["fg_muted"]
        acc = t["accent"]
        hov = t["bg_hover"]

        container = QWidget(self)
        container.setObjectName("picker")
        container.setStyleSheet(f"""
            QWidget#picker {{
                background: {bg};
                border: 1px solid {brd};
                border-radius: 12px;
            }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                width: 4px; background: transparent; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {brd}; border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        main_lay = QVBoxLayout(container)
        main_lay.setContentsMargins(12, 10, 12, 12)
        main_lay.setSpacing(8)

        # Title row
        title_row = QHBoxLayout()
        tl = QLabel("Theme")
        tl.setStyleSheet(
            f"color:{fg1}; font-weight:700; font-size:13px; "
            f"background:transparent; border:none;"
        )
        title_row.addWidget(tl)
        title_row.addStretch()
        chip = QLabel(f"  {current}  ")
        chip.setStyleSheet(
            f"color:{acc}; font-size:10px; font-weight:600; "
            f"background:transparent; border:1px solid {acc}; "
            f"border-radius:8px; padding:1px 4px;"
        )
        title_row.addWidget(chip)
        main_lay.addLayout(title_row)

        # Two columns
        cols = QHBoxLayout()
        cols.setSpacing(10)
        main_lay.addLayout(cols)

        dark_names  = [n for n in THEME_NAMES if THEMES[n].get("is_dark", True)]
        light_names = [n for n in THEME_NAMES if not THEMES[n].get("is_dark", True)]

        for section, names in [("Dark", dark_names), ("Light", light_names)]:
            col_w = QWidget()
            col_w.setStyleSheet("background:transparent;")
            col_l = QVBoxLayout(col_w)
            col_l.setContentsMargins(0, 0, 0, 0)
            col_l.setSpacing(4)

            sec_l = QLabel(section.upper())
            sec_l.setStyleSheet(
                f"color:{fg2}; font-size:9px; font-weight:700; "
                f"letter-spacing:1.5px; background:transparent; border:none;"
            )
            col_l.addWidget(sec_l)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setFixedHeight(360)
            scroll.setFixedWidth(205)

            content = QWidget()
            content.setStyleSheet("background:transparent;")
            c_lay = QVBoxLayout(content)
            c_lay.setContentsMargins(2, 2, 4, 2)
            c_lay.setSpacing(1)

            for name in names:
                row = _ThemeRow(name, name == current, acc, fg1, hov)
                row.clicked.connect(lambda n=name: self._select(n))
                c_lay.addWidget(row)

            c_lay.addStretch()
            scroll.setWidget(content)
            col_l.addWidget(scroll)
            cols.addWidget(col_w)

        self.adjustSize()

    def _select(self, name: str):
        self._apply_fn(name)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
