"""
ui/theme.py  –  NovaPad Theme System
=====================================
Two complete QSS stylesheets (Light + Dark) with a clean, modern aesthetic.
Uses `ThemeManager.apply(app, dark)` to swap themes at runtime.
"""

from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui     import QColor, QPalette


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN DICTIONARIES
# ─────────────────────────────────────────────────────────────────────────────

LIGHT = dict(
    bg_app           = "#F2F2F7",
    bg_window        = "#FFFFFF",
    bg_toolbar       = "#EBEBEB",
    bg_tab_bar       = "#DEDEDE",
    bg_tab_active    = "#FFFFFF",
    bg_tab_inactive  = "#D4D4D8",
    bg_editor        = "#FFFFFF",
    bg_statusbar     = "#EBEBEB",
    bg_menu          = "#FFFFFF",
    bg_hover         = "#D1D1D6",
    bg_pressed       = "#C7C7CC",
    bg_input         = "#FFFFFF",
    bg_button        = "#E5E5EA",
    accent           = "#007AFF",
    accent_hover     = "#0063CC",
    fg_primary       = "#1C1C1E",
    fg_secondary     = "#636366",
    fg_muted         = "#AEAEB2",
    fg_tab_active    = "#1C1C1E",
    fg_tab_inactive  = "#6E6E73",
    border           = "#D1D1D6",
    border_input     = "#C7C7CC",
    scrollbar_bg     = "#F2F2F7",
    scrollbar_handle = "#C7C7CC",
    separator        = "#D1D1D6",
    sel_bg           = "#007AFF",
    sel_fg           = "#FFFFFF",
    find_match_bg    = "#FFDF80",
    find_match_fg    = "#1C1C1E",
    find_cur_bg      = "#FF9500",
    find_cur_fg      = "#FFFFFF",
)

DARK = dict(
    bg_app           = "#1C1C1E",
    bg_window        = "#1C1C1E",
    bg_toolbar       = "#2C2C2E",
    bg_tab_bar       = "#252528",
    bg_tab_active    = "#1C1C1E",
    bg_tab_inactive  = "#2C2C2E",
    bg_editor        = "#1E1E1E",
    bg_statusbar     = "#111113",
    bg_menu          = "#2C2C2E",
    bg_hover         = "#3A3A3C",
    bg_pressed       = "#48484A",
    bg_input         = "#2C2C2E",
    bg_button        = "#3A3A3C",
    accent           = "#0A84FF",
    accent_hover     = "#409CFF",
    fg_primary       = "#F2F2F7",
    fg_secondary     = "#AEAEB2",
    fg_muted         = "#636366",
    fg_tab_active    = "#F2F2F7",
    fg_tab_inactive  = "#98989D",
    border           = "#3A3A3C",
    border_input     = "#48484A",
    scrollbar_bg     = "#1C1C1E",
    scrollbar_handle = "#48484A",
    separator        = "#38383A",
    sel_bg           = "#0A84FF",
    sel_fg           = "#FFFFFF",
    find_match_bg    = "#513B00",
    find_match_fg    = "#FFE066",
    find_cur_bg      = "#FF9500",
    find_cur_fg      = "#FFFFFF",
)


# ─────────────────────────────────────────────────────────────────────────────
# QSS TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

_QSS = """
/* ── Global ─────────────────────────────────────────────────────── */
QWidget {{
    background-color: {bg_app};
    color: {fg_primary};
    font-family: -apple-system, "Segoe UI Variable", "Segoe UI", "SF Pro Text",
                 "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: {sel_bg};
    selection-color: {sel_fg};
    outline: none;
    border: none;
}}
QMainWindow {{ background-color: {bg_window}; }}

/* ── Menu Bar ────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {bg_toolbar};
    color: {fg_primary};
    border-bottom: 1px solid {border};
    padding: 1px 4px;
    spacing: 2px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 5px 10px;
    border-radius: 5px;
}}
QMenuBar::item:selected, QMenuBar::item:pressed {{
    background-color: {bg_hover};
}}

/* ── Menus ───────────────────────────────────────────────────────── */
QMenu {{
    background-color: {bg_menu};
    color: {fg_primary};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 5px 0;
}}
QMenu::item {{
    padding: 6px 28px 6px 20px;
    border-radius: 5px;
    margin: 1px 5px;
}}
QMenu::item:selected {{ background-color: {accent}; color: #FFFFFF; }}
QMenu::item:disabled {{ color: {fg_muted}; }}
QMenu::separator {{
    height: 1px;
    background: {separator};
    margin: 4px 10px;
}}

/* ── Toolbar ─────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {bg_toolbar};
    border: none;
    border-bottom: 1px solid {border};
    padding: 3px 6px;
    spacing: 2px;
}}
QToolBar::separator {{
    width: 1px;
    background: {separator};
    margin: 4px 3px;
}}
QToolButton {{
    background: transparent;
    color: {fg_primary};
    border: none;
    border-radius: 6px;
    padding: 5px 7px;
    font-size: 12px;
    min-width: 28px;
    min-height: 28px;
}}
QToolButton:hover  {{ background-color: {bg_hover}; }}
QToolButton:pressed {{ background-color: {bg_pressed}; }}
QToolButton:checked {{ background-color: {bg_pressed}; color: {accent}; }}

/* ── Tabs ────────────────────────────────────────────────────────── */
QTabWidget::pane {{ border: none; background: {bg_editor}; }}
QTabWidget::tab-bar {{ left: 0; }}
QTabBar {{
    background: {bg_tab_bar};
    border-bottom: 1px solid {border};
}}
QTabBar::tab {{
    background: {bg_tab_inactive};
    color: {fg_tab_inactive};
    border: none;
    border-right: 1px solid {border};
    padding: 7px 16px 7px 14px;
    min-width: 100px;
    max-width: 220px;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {bg_tab_active};
    color: {fg_tab_active};
    font-weight: 500;
    border-bottom: 2px solid {accent};
}}
QTabBar::tab:hover:!selected {{ background: {bg_hover}; color: {fg_primary}; }}
QTabBar::close-button {{ subcontrol-position: right; padding: 2px; }}

/* ── Editor ──────────────────────────────────────────────────────── */
QPlainTextEdit {{
    background-color: {bg_editor};
    color: {fg_primary};
    border: none;
    padding: 6px 2px 6px 2px;
    selection-background-color: {sel_bg};
    selection-color: {sel_fg};
}}

/* ── Scrollbars ──────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {scrollbar_bg};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {scrollbar_handle};
    border-radius: 4px;
    min-height: 24px;
    margin: 1px;
}}
QScrollBar::handle:vertical:hover {{ background: {fg_muted}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {scrollbar_bg};
    height: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {scrollbar_handle};
    border-radius: 4px;
    min-width: 24px;
    margin: 1px;
}}
QScrollBar::handle:horizontal:hover {{ background: {fg_muted}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Status Bar ──────────────────────────────────────────────────── */
QStatusBar {{
    background: {bg_statusbar};
    color: {fg_secondary};
    border-top: 1px solid {border};
    font-size: 11px;
    padding: 1px 8px;
}}
QStatusBar::item {{ border: none; }}

/* ── Find Bar ────────────────────────────────────────────────────── */
QWidget#FindBar {{
    background-color: {bg_toolbar};
    border-top: 1px solid {border};
}}

/* ── Line Edit ───────────────────────────────────────────────────── */
QLineEdit {{
    background: {bg_input};
    color: {fg_primary};
    border: 1.5px solid {border_input};
    border-radius: 6px;
    padding: 4px 9px;
    font-size: 13px;
    selection-background-color: {sel_bg};
}}
QLineEdit:focus {{ border-color: {accent}; }}
QLineEdit:disabled {{ color: {fg_muted}; background: {bg_app}; }}

/* ── Push Buttons ────────────────────────────────────────────────── */
QPushButton {{
    background: {bg_button};
    color: {fg_primary};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
    min-height: 26px;
}}
QPushButton:hover   {{ background: {bg_hover}; }}
QPushButton:pressed {{ background: {bg_pressed}; }}
QPushButton#primary {{
    background: {accent}; color: #FFFFFF; border-color: {accent_hover};
}}
QPushButton#primary:hover {{ background: {accent_hover}; }}

/* ── Checkboxes ──────────────────────────────────────────────────── */
QCheckBox {{ color: {fg_primary}; spacing: 6px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 1.5px solid {border_input};
    border-radius: 4px;
    background: {bg_input};
}}
QCheckBox::indicator:checked {{
    background: {accent}; border-color: {accent};
}}

/* ── Combo Box ───────────────────────────────────────────────────── */
QComboBox {{
    background: {bg_button}; color: {fg_primary};
    border: 1px solid {border}; border-radius: 6px;
    padding: 4px 10px; min-width: 80px;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {bg_menu}; color: {fg_primary};
    border: 1px solid {border}; border-radius: 6px;
    selection-background-color: {accent};
    selection-color: #FFFFFF; padding: 4px;
}}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {{ background: transparent; color: {fg_primary}; }}

/* ── Dialog / MsgBox ─────────────────────────────────────────────── */
QDialog {{ background: {bg_window}; }}
QMessageBox {{ background: {bg_window}; }}
"""


# ─────────────────────────────────────────────────────────────────────────────
# THEME MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class ThemeManager:
    _dark: bool = False

    @classmethod
    def apply(cls, app: QApplication, dark: bool):
        cls._dark = dark
        tokens    = DARK if dark else LIGHT
        app.setStyleSheet(_QSS.format(**tokens))
        cls._set_palette(app, tokens, dark)

    @staticmethod
    def _set_palette(app: QApplication, t: dict, dark: bool):
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window,          QColor(t["bg_window"]))
        p.setColor(QPalette.ColorRole.WindowText,      QColor(t["fg_primary"]))
        p.setColor(QPalette.ColorRole.Base,            QColor(t["bg_editor"]))
        p.setColor(QPalette.ColorRole.AlternateBase,   QColor(t["bg_toolbar"]))
        p.setColor(QPalette.ColorRole.Text,            QColor(t["fg_primary"]))
        p.setColor(QPalette.ColorRole.Button,          QColor(t["bg_button"]))
        p.setColor(QPalette.ColorRole.ButtonText,      QColor(t["fg_primary"]))
        p.setColor(QPalette.ColorRole.Highlight,       QColor(t["accent"]))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(t["sel_fg"]))
        p.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["fg_muted"]))
        p.setColor(QPalette.ColorRole.Link,            QColor(t["accent"]))
        app.setPalette(p)

    @classmethod
    def is_dark(cls) -> bool:
        return cls._dark

    @classmethod
    def find_colors(cls) -> dict[str, str]:
        t = DARK if cls._dark else LIGHT
        return {
            "match_bg":  t["find_match_bg"],
            "match_fg":  t["find_match_fg"],
            "cur_bg":    t["find_cur_bg"],
            "cur_fg":    t["find_cur_fg"],
        }
