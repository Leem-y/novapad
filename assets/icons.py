"""
assets/icons.py  –  NovaPad Icon System
========================================
All icons are stored as SVG strings and rendered to QPixmap/QIcon at
runtime via Qt's built-in SVG renderer.  No external files required for
the bundled app; PyInstaller will include this module automatically.

Each icon is a 16×16 (or 24×24 for the app logo) Feather-style SVG.
`get_icon(name, color, size)` returns a QIcon ready for toolbar / menus.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QByteArray, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer

# ─────────────────────────────────────────────────────────────────────────────
# RAW SVG DATA  (Feather Icons – MIT licence)
# ─────────────────────────────────────────────────────────────────────────────

_SVG: dict[str, str] = {
    # ── File ops ──────────────────────────────────────────────────────────
    "new_file": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="12" y1="18" x2="12" y2="12"/>'
        '<line x1="9" y1="15" x2="15" y2="15"/>'
        '</svg>'
    ),
    "open_file": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
        '</svg>'
    ),
    "save": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
        '<polyline points="17 21 17 13 7 13 7 21"/>'
        '<polyline points="7 3 7 8 15 8"/>'
        '</svg>'
    ),
    # ── Edit ops ──────────────────────────────────────────────────────────
    "undo": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="9 14 4 9 9 4"/>'
        '<path d="M20 20v-7a4 4 0 0 0-4-4H4"/>'
        '</svg>'
    ),
    "redo": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="15 14 20 9 15 4"/>'
        '<path d="M4 20v-7a4 4 0 0 1 4-4h12"/>'
        '</svg>'
    ),
    "cut": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="6" cy="20" r="2"/><circle cx="6" cy="4" r="2"/>'
        '<line x1="6" y1="6" x2="6" y2="18"/>'
        '<line x1="21" y1="4" x2="6" y2="4"/>'
        '<line x1="21" y1="20" x2="6" y2="20"/>'
        '</svg>'
    ),
    "copy": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
        '</svg>'
    ),
    "paste": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
        '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>'
        '</svg>'
    ),
    # ── Search ────────────────────────────────────────────────────────────
    "search": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="11" cy="11" r="8"/>'
        '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
        '</svg>'
    ),
    "replace": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="17 1 21 5 17 9"/>'
        '<path d="M3 11V9a4 4 0 0 1 4-4h14"/>'
        '<polyline points="7 23 3 19 7 15"/>'
        '<path d="M21 13v2a4 4 0 0 1-4 4H3"/>'
        '</svg>'
    ),
    # ── View ──────────────────────────────────────────────────────────────
    "moon": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
        '</svg>'
    ),
    "sun": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="5"/>'
        '<line x1="12" y1="1" x2="12" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="23"/>'
        '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>'
        '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
        '<line x1="1" y1="12" x2="3" y2="12"/>'
        '<line x1="21" y1="12" x2="23" y2="12"/>'
        '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>'
        '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
        '</svg>'
    ),
    "wrap": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="3" y1="6" x2="21" y2="6"/>'
        '<path d="M3 12h15a3 3 0 0 1 0 6h-4"/>'
        '<polyline points="10 15 7 18 10 21"/>'
        '</svg>'
    ),
    "hash": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="4" y1="9" x2="20" y2="9"/>'
        '<line x1="4" y1="15" x2="20" y2="15"/>'
        '<line x1="10" y1="3" x2="8" y2="21"/>'
        '<line x1="16" y1="3" x2="14" y2="21"/>'
        '</svg>'
    ),
    "zoom_in": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="11" cy="11" r="8"/>'
        '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
        '<line x1="11" y1="8" x2="11" y2="14"/>'
        '<line x1="8" y1="11" x2="14" y2="11"/>'
        '</svg>'
    ),
    "zoom_out": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="11" cy="11" r="8"/>'
        '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
        '<line x1="8" y1="11" x2="14" y2="11"/>'
        '</svg>'
    ),
    # ── UI chrome ─────────────────────────────────────────────────────────
    "close": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="18" y1="6" x2="6" y2="18"/>'
        '<line x1="6" y1="6" x2="18" y2="18"/>'
        '</svg>'
    ),
    "arrow_up": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="18 15 12 9 6 15"/>'
        '</svg>'
    ),
    "arrow_down": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="6 9 12 15 18 9"/>'
        '</svg>'
    ),
    "theme": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="13.5" cy="6.5" r=".5" fill="{color}"/>'
        '<circle cx="17.5" cy="10.5" r=".5" fill="{color}"/>'
        '<circle cx="8.5" cy="7.5" r=".5" fill="{color}"/>'
        '<circle cx="6.5" cy="12.5" r=".5" fill="{color}"/>'
        '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>'
        '</svg>'
    ),
    "clock": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="12 6 12 12 16 14"/>'
        '</svg>'
    ),
    "eye": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>'
        '<circle cx="12" cy="12" r="3"/>'
        '</svg>'
    ),
    "eye_off": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>'
        '<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>'
        '<line x1="1" y1="1" x2="23" y2="23"/>'
        '</svg>'
    ),
    # ── App logo (32×32, used for window icon) ────────────────────────────
    "app_logo": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<defs>'
        '<linearGradient id="g1" x1="0%%" y1="0%%" x2="100%%" y2="100%%">'
        '<stop offset="0%%" style="stop-color:{bg_dark}"/>'
        '<stop offset="100%%" style="stop-color:{bg_mid}"/>'
        '</linearGradient>'
        '</defs>'
        '<rect width="32" height="32" rx="7" fill="url(#g1)"/>'
        '<path d="M22.5 17.8A8 8 0 1 1 14.2 9.5a5.8 5.8 0 0 0 8.3 8.3z"'
        ' fill="{fg}"/>'
        '<circle cx="23" cy="10" r="1.3" fill="{accent}" opacity="0.9"/>'
        '<circle cx="26" cy="14.5" r="0.9" fill="{accent2}" opacity="0.8"/>'
        '<circle cx="21" cy="7.5" r="0.7" fill="{accent3}" opacity="0.7"/>'
        '</svg>'
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# ICON CACHE  (avoid re-rendering the same icon every frame)
# ─────────────────────────────────────────────────────────────────────────────

_cache: dict[tuple, QIcon] = {}


def get_icon(name: str, color: str = "#5A5A6E", size: int = 16) -> QIcon:
    """
    Return a QIcon for *name* rendered at *size*×*size* in *color*.

    The result is cached so repeated calls are instant.
    Falls back to an empty QIcon if the name is unknown.
    """
    key = (name, color, size)
    if key in _cache:
        return _cache[key]

    svg_tmpl = _SVG.get(name)
    if not svg_tmpl:
        return QIcon()

    svg_data = svg_tmpl.replace("{color}", color).encode("utf-8")

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(QByteArray(svg_data))
    painter  = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()

    icon = QIcon(pixmap)
    _cache[key] = icon
    return icon


def get_app_icon() -> QIcon:
    """Return the multi-resolution app icon tinted with the current theme."""""
    try:
        from ui.theme import ThemeManager
        t       = ThemeManager.current()
        accent  = t["accent"]
        # Derive a darker shade and a secondary accent from the theme
        from PyQt6.QtGui import QColor as _QC
        a = _QC(accent)
        # bg_dark: darken the toolbar bg
        bg  = _QC(t["bg_toolbar"])
        bg_dark = bg.darker(140).name()
        bg_mid  = bg.darker(110).name()
        # accent2/3: lighter variants
        accent2 = a.lighter(130).name()
        accent3 = a.lighter(160).name()
        fg      = t["fg_primary"]
    except Exception:
        accent = "#0A84FF"; accent2 = "#818cf8"; accent3 = "#f0abfc"
        bg_dark = "#1a1a2e"; bg_mid = "#0f3460"; fg = "#e2e8f0"

    svg_template = _SVG["app_logo"]
    svg_data = svg_template.format(
        accent=accent, accent2=accent2, accent3=accent3,
        bg_dark=bg_dark, bg_mid=bg_mid, fg=fg
    ).encode("utf-8")

    icon = QIcon()
    renderer = QSvgRenderer(QByteArray(svg_data))
    # Standard sizes used by Windows taskbar at 100%–200% DPI
    for sz in (16, 24, 32, 40, 48, 64, 128, 256):
        px = QPixmap(sz, sz)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(p)
        p.end()
        icon.addPixmap(px)
    # Add 2× high-DPI variants so Windows uses crisp rendering at 125%–200% scaling
    for logical_sz in (16, 24, 32, 48):
        physical_sz = logical_sz * 2
        px2 = QPixmap(physical_sz, physical_sz)
        px2.setDevicePixelRatio(2.0)
        px2.fill(Qt.GlobalColor.transparent)
        p2 = QPainter(px2)
        p2.setRenderHint(QPainter.RenderHint.Antialiasing)
        p2.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(p2)
        p2.end()
        icon.addPixmap(px2)
    return icon


def toolbar_color(dark: bool = True) -> str:
    """Return the icon stroke color from the current theme."""""
    try:
        from ui.theme import ThemeManager
        return ThemeManager.current()["fg_secondary"]
    except Exception:
        return "#C8CBD0" if dark else "#4A4A5A"
