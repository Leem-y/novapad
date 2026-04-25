# ui/scrollbar_overlay.py -- Tick marks on the vertical scrollbar for search results

from __future__ import annotations
from PyQt6.QtCore    import Qt, QRect, QEvent
from PyQt6.QtGui     import QColor, QPainter
from PyQt6.QtWidgets import QWidget
from ui.theme import ThemeManager


class ScrollbarOverlay(QWidget):
    """
    Transparent overlay drawn on top of the editor's vertical scrollbar.
    Paints accent-colored tick marks at search result line positions.
    Automatically tracks the scrollbar geometry.
    """

    def __init__(self, editor, parent=None):
        super().__init__(parent or editor)
        self._editor       = editor
        self._search_lines: list[int] = []
        self._n_lines      = 0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setVisible(False)
        # Track scrollbar geometry changes
        editor.verticalScrollBar().installEventFilter(self)

    def set_search_lines(self, block_numbers: list[int], n_total_lines: int):
        self._search_lines = block_numbers
        self._n_lines      = n_total_lines
        self._reposition()
        self.setVisible(bool(block_numbers))
        self.update()

    def clear(self):
        self._search_lines = []
        self.setVisible(False)
        self.update()

    def _reposition(self):
        """Resize and reposition to cover the vertical scrollbar exactly."""
        vsb = self._editor.verticalScrollBar()
        if not vsb.isVisible():
            self.setVisible(False)
            return
        # Map scrollbar geometry to the editor widget's coordinate space
        geo = vsb.geometry()
        # The scrollbar lives inside the editor's viewport frame —
        # we need to position relative to our parent (the editor widget)
        pos = vsb.mapTo(self._editor, vsb.rect().topLeft())
        self.setGeometry(pos.x(), pos.y(), geo.width(), geo.height())
        self.raise_()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move,
                             QEvent.Type.Show, QEvent.Type.Hide):
            self._reposition()
        return False

    def paintEvent(self, event):
        if not self._search_lines or self._n_lines < 1:
            return
        t   = ThemeManager.current()
        acc = QColor(t["accent"])
        acc.setAlpha(200)
        h   = self.height()
        w   = self.width()
        p   = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        for bn in self._search_lines:
            frac = bn / self._n_lines
            ty   = int(frac * h)
            # 3px wide full-width tick, 2px tall
            p.fillRect(0, ty, w, 2, acc)
        p.end()
