# ui/minimap.py -- NovaPad Minimap
#
# Rendering model:
#   - Cache = full document rendered at SCALE px/line with indent-aware text.
#   - paintEvent uses two modes:
#       * Short doc  (cache_h <= panel_h): draw at natural size from top.
#       * Long doc   (cache_h >  panel_h): scale entire cache to fit panel.
#   - Viewport box tracks scroll position proportionally in both modes.
#   - Height is synced to editor viewport height via _sync_height().

from __future__ import annotations
from PyQt6.QtCore    import Qt, QRect, QTimer
from PyQt6.QtGui     import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget, QSizePolicy
from ui.theme import ThemeManager


class Minimap(QWidget):

    WIDTH = 140   # panel width in pixels
    SCALE = 2     # px per line in the cache

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._editor              = None
        self._cache: QPixmap | None = None
        self._cache_dirty         = True
        self._n_lines             = 0
        self._cache_w             = self.WIDTH
        self._search_lines: list[int] = []
        self._dragging            = False
        self._drag_offset         = 0   # click offset within the viewport box
        self._minimap_offset      = 0   # cache rows hidden above the panel
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._rebuild_cache)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_editor(self, editor):
        if self._editor:
            try:
                self._editor.document().contentsChanged.disconnect(self._on_content)
                self._editor.verticalScrollBar().valueChanged.disconnect(self.update)
            except RuntimeError:
                pass
        self._editor = editor
        if editor:
            editor.document().contentsChanged.connect(self._on_content)
            editor.verticalScrollBar().valueChanged.connect(self.update)
            self._sync_height()
        self._invalidate()

    def set_dark(self, dark=True): self._invalidate()
    def set_theme(self, name=""):  self._invalidate()

    def set_search_lines(self, block_numbers: list[int]):
        self._search_lines = block_numbers
        self.update()

    def _sync_height(self):
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    # ── Cache ──────────────────────────────────────────────────────────────────

    def _on_content(self):
        self._invalidate()

    def _invalidate(self):
        self._cache_dirty = True
        self._timer.start(150)

    def _rebuild_cache(self):
        self._cache_dirty = False
        if not self._editor:
            self._cache = None
            self.update()
            return

        doc     = self._editor.document()
        n_lines = max(1, doc.blockCount())
        self._n_lines = n_lines

        t  = ThemeManager.current()
        bg = QColor(t["bg_editor"])

        # Scale: compress the full editor viewport width into the minimap width.
        # drawContents renders the document at its natural size; we scale the
        # painter so the result fits exactly in WIDTH pixels horizontally.
        vp_w   = max(1, self._editor.viewport().width())
        scale  = self.WIDTH / vp_w
        doc_h  = max(1.0, doc.size().height())
        cache_h = max(1, int(doc_h * scale))

        self._cache_w = self.WIDTH
        self._doc_scale = scale   # used by paintEvent for search ticks

        from PyQt6.QtCore import QRectF
        px = QPixmap(self.WIDTH, cache_h)
        px.fill(bg)

        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
        p.scale(scale, scale)
        doc.drawContents(p, QRectF(0, 0, vp_w, doc_h))
        p.end()

        self._cache = px
        self.update()

    # ── Paint ──────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        t  = ThemeManager.current()
        p  = QPainter(self)
        p.fillRect(self.rect(), QColor(t["bg_editor"]))

        if not self._editor:
            p.setPen(QColor(t["fg_muted"]))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Content")
            p.end()
            return

        if self._cache_dirty or self._cache is None:
            self._rebuild_cache()
        if self._cache is None:
            p.end()
            return

        pw      = self.WIDTH
        ph      = self.height()
        cache_h = self._cache.height()
        n       = self._n_lines

        vsb      = self._editor.verticalScrollBar()
        vsb_max  = vsb.maximum()
        vsb_val  = vsb.value()
        vsb_page = vsb.pageStep()
        total    = max(1, vsb_max + vsb_page)

        visible_ratio = vsb_page / total
        scroll_ratio  = vsb_val  / total

        # Position of the viewport box inside the full cache (in cache pixels)
        box_h_cache   = max(6, int(visible_ratio * cache_h))
        box_top_cache = int(scroll_ratio * cache_h)

        # ── Compute minimap scroll offset (VS Code style) ─────────────────
        if cache_h <= ph:
            # Whole document fits: pin to top, no scrolling needed
            self._minimap_offset = 0
        else:
            # Slide the minimap window so the viewport box stays centered
            offset = box_top_cache - (ph - box_h_cache) // 2
            self._minimap_offset = max(0, min(cache_h - ph, offset))

        # ── Draw the visible slice of the cache at 1:1 scale ─────────────
        src_h = min(ph, cache_h - self._minimap_offset)
        src   = QRect(0, self._minimap_offset, self._cache_w, src_h)
        dst   = QRect(0, 0, pw, src_h)
        p.drawPixmap(dst, self._cache, src)

        # ── Viewport box (panel coordinates) ─────────────────────────────
        box_top = box_top_cache - self._minimap_offset
        box_h   = min(box_h_cache, ph - box_top)

        from PyQt6.QtCore import QRectF
        fill = QColor(t["fg_secondary"]); fill.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.drawRoundedRect(QRectF(0, box_top, pw, box_h), 4, 4)

        # ── Search highlight bands (full-width, translucent) ─────────────
        if self._search_lines and n > 0:
            hl_color = QColor(t["accent"]); hl_color.setAlpha(80)
            tick     = QColor(t["accent"]); tick.setAlpha(220)
            doc      = self._editor.document()
            scale    = getattr(self, '_doc_scale', 1.0)
            for bn in self._search_lines[:2000]:
                block = doc.findBlockByNumber(bn)
                if block.isValid():
                    block_y = block.layout().position().y()
                    ty = int(block_y * scale) - self._minimap_offset
                else:
                    ty = int((bn / n) * cache_h) - self._minimap_offset
                if 0 <= ty < ph:
                    line_h = max(2, int(2 * scale) + 1)
                    p.fillRect(0, ty, pw, line_h, hl_color)
                    p.fillRect(pw - 3, ty, 3, max(2, ph // 200 + 1), tick)

        # ── Bookmark indicators ───────────────────────────────────────────
        bm_mgr = getattr(self._editor, '_bookmark_manager', None)
        if bm_mgr is not None and n > 0:
            bm_lines = bm_mgr.bookmarks_for(self._editor)
            if bm_lines:
                doc   = self._editor.document()
                scale = getattr(self, '_doc_scale', 1.0)
                bm_color = QColor(t["accent"])
                bm_color.setAlpha(220)
                tick_h = max(2, ph // 150 + 2)
                for bn in bm_lines:
                    block = doc.findBlockByNumber(bn)
                    if block.isValid():
                        ty = int(block.layout().position().y() * scale) - self._minimap_offset
                    else:
                        ty = int((bn / n) * cache_h) - self._minimap_offset
                    if 0 <= ty < ph:
                        p.fillRect(0, ty, 3, tick_h, bm_color)

        p.end()

    # ── Mouse ──────────────────────────────────────────────────────────────────

    def _box_top_panel(self) -> int:
        """Return the current viewport box top in panel coordinates."""
        if not self._editor or not self._cache:
            return 0
        cache_h  = self._cache.height()
        vsb      = self._editor.verticalScrollBar()
        vsb_max  = vsb.maximum()
        vsb_page = vsb.pageStep()
        total    = max(1, vsb_max + vsb_page)
        scroll_ratio  = vsb.value() / total
        box_top_cache = int(scroll_ratio * cache_h)
        return box_top_cache - self._minimap_offset

    def _scroll_to_y(self, y: int):
        """Scroll so the viewport box top aligns with panel y."""
        if not self._editor:
            return
        cache_h  = self._cache.height() if self._cache else self.height()
        vsb      = self._editor.verticalScrollBar()
        vsb_max  = vsb.maximum()
        vsb_page = vsb.pageStep()
        total    = max(1, vsb_max + vsb_page)

        cache_y = y + self._minimap_offset
        ratio   = max(0.0, min(1.0, cache_y / cache_h))
        vsb.setValue(int(ratio * total))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            # Compute where inside the box the user clicked so dragging
            # preserves that relative position instead of snapping the box top.
            click_y  = event.pos().y()
            box_top  = self._box_top_panel()
            self._drag_offset = click_y - box_top
            self._scroll_to_y(click_y - self._drag_offset)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._scroll_to_y(event.pos().y() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._drag_offset = 0
