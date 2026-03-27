"""
core/tab_manager.py  –  NovaPad Tab Manager  (v4)
==================================================
Custom QTabBar with:
  • "+" button at right end → new tab
  • Per-tab painted close "×" with red hover highlight
  • Inline tab renaming on double-click (QLineEdit overlay)
  • Crash-safe tab_label stored per-editor for session restore
"""

from __future__ import annotations
import os

from ui.theme import ThemeManager
from PyQt6.QtCore    import QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui     import (
    QColor, QMouseEvent, QPainter, QPainterPath, QPen, QBrush,
    QFocusEvent, QPixmap, QCursor,
)
from PyQt6.QtWidgets import (
    QApplication, QLineEdit, QTabBar, QTabWidget, QVBoxLayout, QWidget,
)

from core.editor import CodeEditor


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE TAB  (container widget)
# ─────────────────────────────────────────────────────────────────────────────

class EditorTab(QWidget):
    """Thin container so QTabWidget owns the editor lifecycle."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.editor    = CodeEditor(self)
        self.tab_label = ""          # base label (without * prefix)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.editor)


# ─────────────────────────────────────────────────────────────────────────────
# INLINE RENAME EDITOR  (QLineEdit overlaid on a tab)
# ─────────────────────────────────────────────────────────────────────────────

class TabRenameEdit(QLineEdit):
    """
    Inline rename field overlaid on the tab bar at the exact tab rect.
    Parented to the tab bar so it moves with it.  Fixed to the tab rect
    so it never grows beyond the tab width.
    """

    confirmed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, current_text: str, dark: bool, tab_rect, parent=None):
        super().__init__(parent)
        self._done = False

        t   = ThemeManager.current()
        fg  = t["fg_primary"]
        bg  = t["bg_input"]
        acc = t["accent"]   # underline matches active theme accent
        self.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {bg};"
            f"  color: {fg};"
            f"  border: none;"
            f"  border-bottom: 1.5px solid {acc};"
            f"  font-size: 12px;"
            f"  font-weight: 500;"
            f"  padding: 0px 6px;"
            f"}}"
        )
        self.setText(current_text)
        self.selectAll()

        # Centre the editor in the tab, leaving room for the close button
        close_w = 16 + 6 + 4
        edit_h  = min(22, tab_rect.height() - 4)
        edit_y  = tab_rect.top() + (tab_rect.height() - edit_h) // 2
        self.setGeometry(
            tab_rect.left() + 6,
            edit_y,
            tab_rect.width() - close_w - 10,
            edit_h,
        )
        self.show()

    def _emit_confirmed(self):
        if self._done:
            return
        self._done = True
        text = self.text().strip()
        if text:
            self.confirmed.emit(text)
        else:
            self.cancelled.emit()

    def _emit_cancelled(self):
        if self._done:
            return
        self._done = True
        self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._emit_confirmed()
        elif event.key() == Qt.Key.Key_Escape:
            self._emit_cancelled()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        self._emit_confirmed()
        super().focusOutEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM TAB BAR
# ─────────────────────────────────────────────────────────────────────────────

class NovaPadTabBar(QTabBar):
    """
    Signals
    -------
    new_tab_requested()
    close_tab_requested(int)
    rename_tab_requested(int, str)   – index, new label
    """

    new_tab_requested    = pyqtSignal()
    close_tab_requested  = pyqtSignal(int)
    rename_tab_requested = pyqtSignal(int, str)

    _CLOSE_SIZE   = 16
    _CLOSE_MARGIN = 6
    _PLUS_W       = 32

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._hovered_close: int  = -1
        self._plus_hovered:  bool = False
        # Read initial theme state
        self._dark: bool = ThemeManager.is_dark()
        self._rename_edit: TabRenameEdit | None = None
        self._rename_index: int = -1

        # Drag state
        self._drag_index:  int       = -1
        self._drag_start:  QPoint    = QPoint()
        self._drag_active: bool      = False
        self._drag_overlay: QWidget | None = None
        self._drag_offset:  QPoint   = QPoint()
        self._drag_insert:  int      = -1
        self._drag_hidden:  int      = -1
        # Per-tab animated x offsets: dict[index -> current_offset_px]
        self._tab_offsets: dict      = {}
        # Animation timer for smooth tab shifting
        self._shift_timer  = QTimer(self)
        self._shift_timer.setInterval(16)   # ~60fps
        self._shift_timer.timeout.connect(self._animate_shifts)
        # Target offsets (what we're animating toward)
        self._tab_targets: dict      = {}
        # Tabs animating in/out at fast speed: set of indices
        self._fast_anims:  set       = set()
        # Closing tabs waiting for animation to finish: dict[index -> callback]
        self._closing_tabs: dict     = {}

    # ── Theme ─────────────────────────────────────────────────────────────

    def set_dark(self, dark: bool):
        self._dark = dark
        self.update()

    # ── Geometry ──────────────────────────────────────────────────────────

    def _close_rect(self, index: int) -> QRect:
        tr = self.tabRect(index)
        sz = self._CLOSE_SIZE
        x  = tr.right() - sz - self._CLOSE_MARGIN
        y  = tr.top() + (tr.height() - sz) // 2
        return QRect(x, y, sz, sz)

    def _plus_rect(self) -> QRect:
        x = self.tabRect(self.count() - 1).right() + 2 if self.count() else 0
        h = self.height() or self._PLUS_W
        return QRect(x, 0, self._PLUS_W, h)

    def sizeHint(self) -> QSize:
        sh = super().sizeHint()
        return QSize(sh.width() + self._PLUS_W + 4, sh.height())

    def minimumSizeHint(self) -> QSize:
        msh = super().minimumSizeHint()
        return QSize(msh.width() + self._PLUS_W + 4, msh.height())

    def tabSizeHint(self, index: int) -> QSize:
        sh = super().tabSizeHint(index)
        return QSize(sh.width() + self._CLOSE_SIZE + self._CLOSE_MARGIN + 4,
                     sh.height())

    # ── Painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        # Call super() FIRST so Qt's internal drag-move system updates
        # tabRect() positions — this is what actually moves tabs during drag.
        # We then overdraw with our own styling, replacing Qt's default look.
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── Colours ──────────────────────────────────────────────────────
        t           = ThemeManager.current()
        bar_bg      = QColor(t["bg_tab_bar"])
        tab_active  = QColor(t["bg_tab_active"])
        tab_inactive= QColor(t["bg_tab_inactive"])
        tab_hover   = QColor(t["bg_hover"])
        fg_active   = QColor(t["fg_tab_active"])
        fg_inactive = QColor(t["fg_tab_inactive"])
        accent      = QColor(t["accent"])
        border_col  = QColor(t["border"])

        radius  = 7   # top corner radius
        cur_idx = self.currentIndex()

        # Fill bar background
        painter.fillRect(event.rect(), bar_bg)

        # ── Draw tabs ─────────────────────────────────────────────────────
        # Two-pass paint so sliding tabs appear UNDER their neighbours:
        #   1. Animating tabs (open/close) — bottom layer
        #   2. Static inactive tabs        — middle layer
        #   3. Active tab                  — top layer
        all_idx  = [i for i in range(self.count()) if i != self._drag_hidden]
        anim_set = self._fast_anims | set(self._closing_tabs.keys())
        draw_order = (
            [i for i in all_idx if i in anim_set] +
            [i for i in all_idx if i not in anim_set and i != cur_idx] +
            [i for i in all_idx if i not in anim_set and i == cur_idx]
        )
        for i in draw_order:
            tr_base = self.tabRect(i)
            # Apply animated shift offset
            dx  = int(self._tab_offsets.get(i, 0.0))
            tr  = tr_base.translated(dx, 0)
            active  = (i == cur_idx)
            hovered = (i == self._hovered_close)
            bg      = tab_active if active else tab_inactive

            # Build a path with rounded top corners only
            path = QPainterPath()
            r    = float(radius)
            bar_h = float(self.height())

            if active:
                # Active tab: full height + 2px overflow so it merges with editor below
                tl = float(tr.top()) + 2.0   # slight top inset so rounding looks good
                ht = bar_h - tl + 2.0        # extend 2px past bar bottom
                l2, w2 = float(tr.left()), float(tr.width()) - 1.0
                path.moveTo(l2, tl + ht)
                path.lineTo(l2, tl + r)
                path.quadTo(l2, tl, l2 + r, tl)
                path.lineTo(l2 + w2 - 1 - r, tl)
                path.quadTo(l2 + w2 - 1, tl, l2 + w2 - 1, tl + r)
                path.lineTo(l2 + w2 - 1, tl + ht)
                path.closeSubpath()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(bg))
                painter.drawPath(path)
                # Accent line — 2px at bottom of visible area
                painter.setBrush(QBrush(accent))
                painter.drawRect(int(l2) + 1, int(bar_h) - 2, int(w2) - 2, 2)
            else:
                # Inactive tab: vertically centred, slightly shorter
                inset_v = 4.0
                tl = float(tr.top()) + inset_v
                ht = bar_h - inset_v * 2
                l2, w2 = float(tr.left()), float(tr.width()) - 1.0
                path.moveTo(l2, tl + ht)
                path.lineTo(l2, tl + r)
                path.quadTo(l2, tl, l2 + r, tl)
                path.lineTo(l2 + w2 - r, tl)
                path.quadTo(l2 + w2, tl, l2 + w2, tl + r)
                path.lineTo(l2 + w2, tl + ht)
                path.closeSubpath()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(bg))
                painter.drawPath(path)
                # Separator — skip if this tab or the next is active (active tab covers it)
                next_is_active = (i + 1 == cur_idx)
                this_is_before_active = (i == cur_idx - 1)
                if not next_is_active:
                    painter.setPen(border_col)
                    painter.drawLine(int(l2 + w2) - 1, int(tl) + 4,
                                     int(l2 + w2) - 1, int(tl + ht) - 4)

            # Tab label
            text_color = fg_active if active else fg_inactive
            painter.setPen(text_color)
            font = painter.font()
            font.setFamily("Segoe UI")
            font.setPointSize(10)
            font.setWeight(500 if active else 400)
            painter.setFont(font)

            # Text rect: leave room for close button on the right
            text_rect = tr.adjusted(4, 0, -(self._CLOSE_SIZE + self._CLOSE_MARGIN + 4), 0)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                self.tabText(i),
            )

            # Close button × (skip if tab is being renamed)
            if i != self._rename_index:
                cr = self._close_rect(i)
                close_hovered = (i == self._hovered_close)
                # Hover background
                if close_hovered:
                    painter.setPen(Qt.PenStyle.NoPen)
                    hover_c = QColor(ThemeManager.current()["fg_muted"])
                    hover_c.setAlpha(40)
                    painter.setBrush(QBrush(hover_c))
                    painter.drawRoundedRect(cr, 4, 4)
                x_color = QColor(ThemeManager.current()[
                    "fg_secondary" if close_hovered else "fg_muted"])
                pen = QPen(x_color)
                pen.setWidth(2)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                pad = 5
                painter.drawLine(cr.left()+pad, cr.top()+pad,
                                 cr.right()-pad, cr.bottom()-pad)
                painter.drawLine(cr.right()-pad, cr.top()+pad,
                                 cr.left()+pad, cr.bottom()-pad)

        # ── "+" button ────────────────────────────────────────────────────
        pr = self._plus_rect()
        if self._plus_hovered:
            plus_bg = QColor(ThemeManager.current()["fg_muted"])
            plus_bg.setAlpha(30)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(plus_bg))
            btn_rect = pr.adjusted(4, 5, -4, -5)
            painter.drawRoundedRect(btn_rect, 5, 5)

        plus_color = QColor(ThemeManager.current()[
            "fg_secondary" if self._plus_hovered else "fg_muted"])
        pen = QPen(plus_color)
        pen.setWidthF(1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        cx, cy = pr.center().x(), pr.center().y()
        arm = 5
        painter.drawLine(cx - arm, cy, cx + arm, cy)
        painter.drawLine(cx, cy - arm, cx, cy + arm)

        # ── Bottom shadow (tab bar / editor separator depth) ──────────────
        from PyQt6.QtGui import QLinearGradient
        sh = QLinearGradient(0, self.height() - 5, 0, self.height())
        sh.setColorAt(0.0, QColor(0, 0, 0, 0))
        sh.setColorAt(1.0, QColor(0, 0, 0, 28))
        painter.fillRect(0, self.height() - 5, self.width(), 5, sh)

        painter.end()

    # ── Mouse events ──────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.pos()
        if self._plus_rect().contains(pos):
            self.new_tab_requested.emit()
            return
        for i in range(self.count()):
            if self._close_rect(i).contains(pos):
                self.close_tab_requested.emit(i)
                return
        # Record potential drag start
        if event.button() == Qt.MouseButton.LeftButton:
            for i in range(self.count()):
                if self.tabRect(i).contains(pos):
                    self._drag_index = i
                    self._drag_start = pos
                    tr = self.tabRect(i)
                    self._drag_offset = pos - tr.topLeft()
                    break
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Start inline rename on double-click of a tab."""
        pos = event.pos()
        for i in range(self.count()):
            tr = self.tabRect(i)
            # Only trigger on the label area (not the close button)
            if tr.contains(pos) and not self._close_rect(i).contains(pos):
                self._start_rename(i)
                return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.pos()

        # ── Drag handling ─────────────────────────────────────────────
        if (self._drag_index >= 0 and
                event.buttons() & Qt.MouseButton.LeftButton):
            if not self._drag_active:
                # Start drag after 4px threshold
                if (pos - self._drag_start).manhattanLength() >= 4:
                    self._start_drag(self._drag_index)
            if self._drag_active:
                self._update_drag(pos)
                return

        # ── Normal hover ──────────────────────────────────────────────
        prev_close         = self._hovered_close
        self._hovered_close = -1
        for i in range(self.count()):
            if self._close_rect(i).contains(pos):
                self._hovered_close = i
                break
        prev_plus          = self._plus_hovered
        self._plus_hovered  = self._plus_rect().contains(pos)
        if self._hovered_close != prev_close or self._plus_hovered != prev_plus:
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_active:
            self._finish_drag()
        self._drag_index  = -1
        self._drag_active = False
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._hovered_close = -1
        self._plus_hovered  = False
        self.update()
        super().leaveEvent(event)

    # ── Drag implementation ───────────────────────────────────────────────

    def _start_drag(self, index: int):
        """Lift the tab: render it into a floating overlay widget."""
        self._drag_active = True
        tr = self.tabRect(index)

        # Render this one tab into a pixmap
        t         = ThemeManager.current()
        px        = QPixmap(tr.size())
        px.fill(Qt.GlobalColor.transparent)
        p         = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw tab background with slight lift (shadow approximated by darker border)
        accent    = QColor(t["accent"])
        bg        = QColor(t["bg_tab_active"])
        fg        = QColor(t["fg_tab_active"])
        brd       = QColor(t["border"])
        radius    = 7.0
        w, h      = float(tr.width()), float(tr.height())

        path = QPainterPath()
        path.moveTo(0, h)
        path.lineTo(0, radius)
        path.quadTo(0, 0, radius, 0)
        path.lineTo(w - radius, 0)
        path.quadTo(w, 0, w, radius)
        path.lineTo(w, h)
        path.closeSubpath()

        # Drop shadow (drawn slightly offset)
        shadow = QColor(0, 0, 0, 60)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(shadow))
        shadow_path = QPainterPath(path)
        shadow_path.translate(0, 3)
        p.drawPath(shadow_path)

        p.setBrush(QBrush(bg))
        p.drawPath(path)

        # Accent line at bottom
        p.setBrush(QBrush(accent))
        p.drawRect(1, int(h) - 2, int(w) - 2, 2)

        # Label
        p.setPen(fg)
        font = p.font()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        font.setWeight(500)
        p.setFont(font)
        text_rect = QRect(4, 0, int(w) - self._CLOSE_SIZE - self._CLOSE_MARGIN - 8, int(h))
        p.drawText(text_rect,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                   self.tabText(index))
        p.end()

        # Create floating overlay label — parented to tab bar for correct coords
        from PyQt6.QtWidgets import QLabel
        overlay = QLabel(self)
        overlay.setPixmap(px)
        overlay.resize(tr.size())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.raise_()
        overlay.show()
        self._drag_overlay = overlay

        # Mark dragged tab as hidden visually via our paintEvent
        self._drag_hidden  = index
        self.update()

    def _update_drag(self, pos: QPoint):
        """Move overlay, compute insertion point, animate surrounding tabs."""
        src = self._drag_index
        if src < 0:
            return

        # Move overlay
        if self._drag_overlay:
            self._drag_overlay.move(pos.x() - self._drag_offset.x(), 0)

        # Dragged tab's centre x in bar coords
        drag_w   = self.tabRect(src).width()
        drag_cx  = pos.x() - self._drag_offset.x() + drag_w // 2

        # Find insertion index: which gap is the dragged centre nearest?
        insert = src
        for i in range(self.count()):
            if i == src:
                continue
            tr = self.tabRect(i)
            if i < src and drag_cx < tr.center().x():
                insert = i
                break
            elif i > src and drag_cx > tr.center().x():
                insert = i

        # Compute target offsets for each non-dragged tab
        new_targets = {}
        if insert != src:
            for i in range(self.count()):
                if i == src:
                    continue
                tw = self.tabRect(src).width()
                # Tabs that need to slide right: they're between insert and src (when dragging left)
                # Tabs that need to slide left: they're between src and insert (when dragging right)
                if insert < src:
                    # Dragging left: tabs from insert..src-1 shift right
                    if insert <= i < src:
                        new_targets[i] = tw
                    else:
                        new_targets[i] = 0
                else:
                    # Dragging right: tabs from src+1..insert shift left
                    if src < i <= insert:
                        new_targets[i] = -tw
                    else:
                        new_targets[i] = 0
        else:
            for i in range(self.count()):
                new_targets[i] = 0

        if new_targets != self._tab_targets:
            self._tab_targets = new_targets
            self._shift_timer.start()

        if insert != self._drag_insert:
            self._drag_insert = insert
            self.update()

    def _finish_drag(self):
        """Drop: snap tabs back, commit reorder, remove overlay."""
        self._shift_timer.stop()
        self._tab_offsets  = {}
        self._tab_targets  = {}

        if self._drag_overlay:
            self._drag_overlay.hide()
            self._drag_overlay.deleteLater()
            self._drag_overlay = None

        src = self._drag_index
        dst = self._drag_insert if self._drag_insert >= 0 else src
        self._drag_hidden = -1
        self._drag_insert = -1

        if src != dst and 0 <= src < self.count() and 0 <= dst < self.count():
            tw = self.parent()
            if hasattr(tw, '_move_tab'):
                tw._move_tab(src, dst)

        self.update()

    def _animate_shifts(self):
        """Lerp current offsets toward targets at ~60fps. Stop when settled."""
        SPEED_DRAG = 0.28   # drag-reorder shifts
        SPEED_FAST = 0.46   # open / close slide animations
        THRESHOLD  = 1.0    # px — snap to target below this distance

        done_closing = []

        for i in list(self._tab_targets.keys()):
            target = self._tab_targets[i]
            speed  = SPEED_FAST if i in self._fast_anims else SPEED_DRAG
            cur    = self._tab_offsets.get(i, 0.0)
            diff   = target - cur
            if abs(diff) < THRESHOLD:
                self._tab_offsets[i] = float(target)
                if i in self._closing_tabs:
                    done_closing.append(i)
                else:
                    # Open animation complete — clean up state
                    self._fast_anims.discard(i)
                    self._tab_offsets.pop(i, None)
                    self._tab_targets.pop(i, None)
            else:
                self._tab_offsets[i] = cur + diff * speed

        # Fire close callbacks after the loop (removeTab changes tab indices)
        for i in done_closing:
            cb = self._closing_tabs.pop(i, None)
            self._fast_anims.discard(i)
            self._tab_offsets.pop(i, None)
            self._tab_targets.pop(i, None)
            if cb:
                cb()

        if not self._tab_targets:
            self._shift_timer.stop()
        self.update()

    def animate_tab_in(self, idx: int):
        """Slide a newly-added tab in from the left."""
        tr = self.tabRect(idx)
        w  = tr.width() if tr.width() > 10 else 140
        self._tab_offsets[idx] = float(-w)
        self._tab_targets[idx] = 0.0
        self._fast_anims.add(idx)
        if not self._shift_timer.isActive():
            self._shift_timer.start()

    def animate_tab_out(self, idx: int, callback):
        """Slide tab out to the left, then invoke callback (e.g. removeTab)."""
        tr = self.tabRect(idx)
        w  = tr.width() if tr.width() > 10 else 140
        self._tab_offsets[idx] = 0.0
        self._tab_targets[idx] = float(-w)   # slide exactly behind the left neighbour
        self._closing_tabs[idx] = callback
        self._fast_anims.add(idx)
        if not self._shift_timer.isActive():
            self._shift_timer.start()

    # ── Inline rename ─────────────────────────────────────────────────────

    def _start_rename(self, index: int):
        """
        Overlay a QLineEdit over the tab at index, sized to the tab rect.
        No setTabButton — we just position an overlay widget.
        """
        self._cancel_rename()

        current   = self.tabText(index).lstrip("* ")
        tab_rect  = self.tabRect(index)
        edit      = TabRenameEdit(current, self._dark, tab_rect, self)
        self._rename_edit  = edit
        self._rename_index = index

        def on_confirmed(text, i=index):
            self._rename_edit  = None
            self._rename_index = -1
            try:
                edit.hide()
                edit.deleteLater()
            except RuntimeError:
                pass
            if 0 <= i < self.count():
                self.rename_tab_requested.emit(i, text)
            self.update()

        def on_cancelled():
            self._rename_edit  = None
            self._rename_index = -1
            try:
                edit.hide()
                edit.deleteLater()
            except RuntimeError:
                pass
            self.update()

        edit.confirmed.connect(on_confirmed)
        edit.cancelled.connect(on_cancelled)
        edit.setFocus()
        self.update()

    def _cancel_rename(self):
        """Safely cancel any in-progress rename."""
        edit = self._rename_edit
        self._rename_edit  = None
        self._rename_index = -1
        if edit is not None:
            try:
                edit.hide()
                edit.deleteLater()
            except RuntimeError:
                pass
        self.update()


# ─────────────────────────────────────────────────────────────────────────────
# TAB MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class TabManager(QTabWidget):
    """
    Signals
    -------
    tab_changed(CodeEditor | None)
    modification_changed(bool)
    title_changed(str)
    """

    tab_changed          = pyqtSignal(object)
    modification_changed = pyqtSignal(bool)
    title_changed        = pyqtSignal(str)

    _counter = 0

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._tab_bar = NovaPadTabBar(self)
        self.setTabBar(self._tab_bar)
        self.setTabsClosable(False)
        self.setMovable(False)
        self.setDocumentMode(True)

        self._tab_bar.new_tab_requested.connect(self.new_tab)
        self._tab_bar.close_tab_requested.connect(self.close_tab)
        self._tab_bar.rename_tab_requested.connect(self._on_rename)
        self.currentChanged.connect(self._on_current_changed)

    # ── Creating tabs ─────────────────────────────────────────────────────

    def new_tab(self, file_path: str | None = None,
                content: str = "",
                label_override: str | None = None) -> CodeEditor:
        """Open a new editor tab."""
        TabManager._counter += 1
        tab    = EditorTab(self)
        editor = tab.editor

        # Use load_content so HTML files are loaded correctly
        if content:
            editor.load_content(content, file_path)
        editor.document().setModified(False)

        if label_override:
            label = label_override
        elif file_path:
            label = os.path.basename(file_path)
        else:
            label = f"Untitled-{TabManager._counter}"

        tab.tab_label = label

        if file_path:
            editor.file_path = file_path

        idx = self.addTab(tab, label)
        self.setCurrentIndex(idx)

        # Slide tab button in from the left
        self._tab_bar.animate_tab_in(idx)

        # Fade the content in simultaneously
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        _effect = QGraphicsOpacityEffect(tab)
        tab.setGraphicsEffect(_effect)
        _anim = QPropertyAnimation(_effect, b"opacity", tab)
        _anim.setDuration(160)
        _anim.setStartValue(0.0)
        _anim.setEndValue(1.0)
        _anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        _anim.finished.connect(lambda: tab.setGraphicsEffect(None))
        _anim.start()

        editor.document().modificationChanged.connect(
            lambda modified, i=idx: self._on_mod_changed(i, modified)
        )

        return editor

    # ── Closing tabs ──────────────────────────────────────────────────────

    def close_tab(self, index: int) -> bool:
        editor = self.editor_at(index)
        if editor and editor.document().isModified():
            tab  = self.widget(index)
            name = tab.tab_label if isinstance(tab, EditorTab) else "this file"
            from ui.dialogs import themed_question
            reply = themed_question(
                self, "Unsaved Changes",
                f'Save changes to "{name}"?',
                btn_yes="Save", btn_no="Discard", btn_cancel="Cancel"
            )
            if reply == "Save":
                if not self._request_save(editor):
                    return False
            elif reply == "Cancel" or reply is None:
                return False

        def _do_remove(mgr=self, idx=index):
            mgr.removeTab(idx)
            if mgr.count() == 0:
                mgr.new_tab()

        self._tab_bar.animate_tab_out(index, _do_remove)
        return True

    def _request_save(self, editor: CodeEditor) -> bool:
        parent = self.parent()
        while parent:
            if hasattr(parent, "save_file"):
                return parent.save_file(editor=editor)
            parent = parent.parent()
        return False

    # ── Access helpers ────────────────────────────────────────────────────

    def current_editor(self) -> CodeEditor | None:
        w = self.currentWidget()
        return w.editor if isinstance(w, EditorTab) else None

    def editor_at(self, index: int) -> CodeEditor | None:
        w = self.widget(index)
        return w.editor if isinstance(w, EditorTab) else None

    def all_editors(self) -> list[CodeEditor]:
        return [
            self.widget(i).editor
            for i in range(self.count())
            if isinstance(self.widget(i), EditorTab)
        ]

    def index_of_editor(self, editor: CodeEditor) -> int:
        for i in range(self.count()):
            if self.editor_at(i) is editor:
                return i
        return -1

    def tab_label_at(self, index: int) -> str:
        w = self.widget(index)
        return w.tab_label if isinstance(w, EditorTab) else self.tabText(index)

    # ── Title / modification ──────────────────────────────────────────────

    def _on_mod_changed(self, index: int, modified: bool):
        if index < 0 or index >= self.count():
            return
        tab = self.widget(index)
        base  = tab.tab_label if isinstance(tab, EditorTab) else self.tabText(index)
        label = f"* {base}" if modified else base
        self.setTabText(index, label)
        if index == self.currentIndex():
            self.modification_changed.emit(modified)
            self.title_changed.emit(label)

    def _on_rename(self, index: int, new_label: str):
        """Apply a rename from the inline editor."""
        if index < 0 or index >= self.count():
            return
        tab = self.widget(index)
        if isinstance(tab, EditorTab):
            tab.tab_label = new_label
        modified = (self.editor_at(index).document().isModified()
                    if self.editor_at(index) else False)
        display = f"* {new_label}" if modified else new_label
        self.setTabText(index, display)
        if index == self.currentIndex():
            self.title_changed.emit(display)

    def refresh_tab_title(self, editor: CodeEditor):
        idx = self.index_of_editor(editor)
        if idx < 0:
            return
        tab  = self.widget(idx)
        base = (os.path.basename(editor.file_path)
                if editor.file_path else (tab.tab_label if isinstance(tab, EditorTab)
                                          else f"Untitled-{idx+1}"))
        if isinstance(tab, EditorTab):
            tab.tab_label = base
        modified = editor.document().isModified()
        self.setTabText(idx, f"* {base}" if modified else base)

    # ── Bulk propagation ──────────────────────────────────────────────────

    def _move_tab(self, src: int, dst: int):
        """Move tab from src index to dst index, preserving content."""""
        if src == dst or not (0 <= src < self.count()) or not (0 <= dst < self.count()):
            return
        # Grab content
        widget = self.widget(src)
        label  = self.tabText(src)
        # Remove and reinsert
        self.removeTab(src)
        actual_dst = dst if dst < src else dst  # removeTab shifts indices
        self.insertTab(actual_dst, widget, label)
        self.setCurrentIndex(actual_dst)

    def set_dark_mode(self, dark: bool):
        self._tab_bar.set_dark(dark)
        for e in self.all_editors():
            e.set_dark_mode(dark)

    def set_word_wrap(self, on: bool):
        for e in self.all_editors():
            e.set_word_wrap(on)

    def toggle_line_numbers(self, visible: bool):
        for e in self.all_editors():
            e.toggle_line_numbers(visible)

    # ── Internal slots ────────────────────────────────────────────────────

    def _on_current_changed(self, index: int):
        self.tab_changed.emit(self.editor_at(index))
