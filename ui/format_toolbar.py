# ui/format_toolbar.py -- NovaPad Formatting Toolbar
# Bold / Italic / Underline only. No mode badge.

from __future__ import annotations

from PyQt6.QtCore    import QByteArray, QSignalBlocker, Qt
from PyQt6.QtGui     import QAction, QIcon, QPainter, QPixmap
from PyQt6.QtSvg     import QSvgRenderer
from PyQt6.QtWidgets import QToolBar, QWidget

from assets.icons import toolbar_color


def _svg_icon(svg: str, size: int = 18) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    r = QSvgRenderer(QByteArray(svg.encode()))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p)
    p.end()
    return QIcon(px)


def _make_icons(dark: bool):
    c = toolbar_color(dark)
    bold_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
        f'<text x="2" y="16" font-family="Georgia,serif" font-size="17"'
        f' font-weight="bold" fill="{c}">B</text></svg>'
    )
    italic_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
        f'<text x="4" y="16" font-family="Georgia,serif" font-size="17"'
        f' font-style="italic" fill="{c}">I</text></svg>'
    )
    # U letter + a short underline bar centred beneath it
    underline_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
        f'<text x="2" y="14" font-family="Georgia,serif" font-size="15"'
        f' fill="{c}">U</text>'
        f'<rect x="2" y="16.5" width="11" height="1.6" fill="{c}" rx="0.8"/>'
        f'</svg>'
    )
    return (
        _svg_icon(bold_svg),
        _svg_icon(italic_svg),
        _svg_icon(underline_svg),
    )


class FormatToolbar(QToolBar):

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Formatting", parent)
        self.setMovable(False)
        self.setFloatable(False)
        self._editor = None
        self._dark   = False
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
