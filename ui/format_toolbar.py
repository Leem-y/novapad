# ui/format_toolbar.py -- NovaPad Formatting Toolbar
# Bold / Italic / Underline — SVG path icons matching the Feather icon style.

from __future__ import annotations

from PyQt6.QtCore    import QByteArray, QSignalBlocker, Qt, QSize
from PyQt6.QtGui     import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg     import QSvgRenderer
from PyQt6.QtWidgets import QToolBar, QWidget

from assets.icons import toolbar_color


def _svg_icon(svg: str, size: int = 16) -> QIcon:
    """Render an SVG string to a QIcon at the given size."""
    # Render at 3× then scale down for crisp anti-aliased edges.
    hi = size * 3
    px_hi = QPixmap(hi, hi)
    px_hi.fill(Qt.GlobalColor.transparent)
    r = QSvgRenderer(QByteArray(svg.encode()))
    p = QPainter(px_hi)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    r.render(p)
    p.end()
    px = px_hi.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.SmoothTransformation)
    return QIcon(px)


def _make_icons(dark: bool, size: int = 16) -> tuple:
    """
    Generate B/I/U icons as SVG paths — same thin-stroke Feather style as all
    other toolbar icons. Stroke width 1.8, round caps, viewBox 24x24.
    """
    c = toolbar_color(dark)

    # Bold — standard Feather "bold" paths
    bold_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        f' stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M6 4h8a4 4 0 0 1 0 8H6z"/>'
        f'<path d="M6 12h9a4 4 0 0 1 0 8H6z"/>'
        f'</svg>'
    )

    # Italic — standard Feather "italic" paths
    italic_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        f' stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<line x1="19" y1="4" x2="10" y2="4"/>'
        f'<line x1="14" y1="20" x2="5" y2="20"/>'
        f'<line x1="15" y1="4" x2="9" y2="20"/>'
        f'</svg>'
    )

    # Underline — standard Feather "underline" paths
    underline_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        f' stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M6 3v7a6 6 0 0 0 12 0V3"/>'
        f'<line x1="4" y1="21" x2="20" y2="21"/>'
        f'</svg>'
    )

    return (
        _svg_icon(bold_svg, size),
        _svg_icon(italic_svg, size),
        _svg_icon(underline_svg, size),
    )


class FormatToolbar(QToolBar):

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Formatting", parent)
        self.setMovable(False)
        self.setFloatable(False)
        self._editor = None
        self._dark   = False
        self.setIconSize(QSize(16, 16))
        # Match the main toolbar's button style exactly
        self.setStyleSheet(
            "QToolBar { spacing: 1px; padding: 2px; }"
            "QToolButton { padding: 4px; border-radius: 4px; min-width: 24px; min-height: 24px; }"
            "QToolButton:hover { background: rgba(128,128,128,0.18); }"
            "QToolButton:checked { background: rgba(128,128,128,0.30); }"
        )
        self._build()

    def _build(self):
        self._act_bold = QAction(self)
        self._act_bold.setCheckable(True)
        self._act_bold.setToolTip("Bold  (Ctrl+B)")
        self._act_bold.triggered.connect(self._on_bold)
        self.addAction(self._act_bold)

        self._act_italic = QAction(self)
        self._act_italic.setCheckable(True)
        self._act_italic.setToolTip("Italic  (Ctrl+I)")
        self._act_italic.triggered.connect(self._on_italic)
        self.addAction(self._act_italic)

        self._act_underline = QAction(self)
        self._act_underline.setCheckable(True)
        self._act_underline.setToolTip("Underline  (Ctrl+U)")
        self._act_underline.triggered.connect(self._on_underline)
        self.addAction(self._act_underline)

        self._refresh_icons()

    def _refresh_icons(self):
        b, i, u = _make_icons(self._dark)
        self._act_bold.setIcon(b)
        self._act_italic.setIcon(i)
        self._act_underline.setIcon(u)

    # -- Public API ----------------------------------------------------------

    def set_editor(self, editor):
        if self._editor is not None:
            try:
                self._editor.cursor_format_changed.disconnect(self.refresh)
                self._editor.mode_changed.disconnect(self._on_mode_changed)
            except RuntimeError:
                pass
        self._editor = editor
        if editor is not None:
            editor.cursor_format_changed.connect(self.refresh)
            editor.mode_changed.connect(self._on_mode_changed)
        self.refresh()

    def set_dark(self, dark: bool):
        self._dark = dark
        self._refresh_icons()

    def refresh(self):
        if self._editor is None:
            self._set_enabled(False)
            return

        rich = self._editor.is_rich_mode()
        self._set_enabled(rich)

        if not rich:
            return

        with QSignalBlocker(self._act_bold), \
             QSignalBlocker(self._act_italic), \
             QSignalBlocker(self._act_underline):
            self._act_bold.setChecked(self._editor.current_bold)
            self._act_italic.setChecked(self._editor.current_italic)
            self._act_underline.setChecked(self._editor.current_underline)

    def _set_enabled(self, enabled: bool):
        for a in (self._act_bold, self._act_italic, self._act_underline):
            a.setEnabled(enabled)

    # -- Slots ---------------------------------------------------------------

    def _on_bold(self, _):
        if self._editor: self._editor.toggle_bold()

    def _on_italic(self, _):
        if self._editor: self._editor.toggle_italic()

    def _on_underline(self, _):
        if self._editor: self._editor.toggle_underline()

    def _on_mode_changed(self, mode: str):
        self.refresh()
