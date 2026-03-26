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

from PyQt6.QtCore    import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui     import (
    QColor, QMouseEvent, QPainter, QPainterPath, QPen, QBrush,
    QFocusEvent,
)
from PyQt6.QtWidgets import (
    QApplication, QLineEdit, QMessageBox, QTabBar, QTabWidget, QVBoxLayout, QWidget,
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

        fg = "#F2F2F7" if dark else "#1C1C1E"
        bg = "#2C2C2E" if dark else "#1C1C1E"
        self.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {bg};"
            f"  color: {fg};"
            f"  border: none;"
            f"  border-bottom: 1.5px solid #0A84FF;"
            f"  font-size: 12px;"
            f"  font-weight: 500;"
            f"  padding: 0px 6px;"
            f"}}"
        )
        self.setText(current_text)
        self.selectAll()

        # Size exactly to the tab, leaving room for the close button
        close_w = 16 + 6 + 4   # _CLOSE_SIZE + _CLOSE_MARGIN + padding
        self.setGeometry(
            tab_rect.left() + 1,
            tab_rect.top() + 2,
            tab_rect.width() - close_w - 2,
            tab_rect.height() - 4,
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
        # Read initial dark mode from QSettings so first paint is correct
        from PyQt6.QtCore import QSettings
        self._dark: bool = QSettings("NovaPad", "NovaPad").value("dark_mode", True, bool)
        self._rename_edit: TabRenameEdit | None = None
        self._rename_index: int = -1

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
        if self._dark:
            bar_bg      = QColor("#252528")
            tab_active  = QColor("#1C1C1E")
            tab_inactive= QColor("#2C2C2E")
            tab_hover   = QColor("#333336")
            fg_active   = QColor("#F2F2F7")
            fg_inactive = QColor("#98989D")
            accent      = QColor("#0A84FF")
            border_col  = QColor("#3A3A3C")
        else:
            bar_bg      = QColor("#DEDEDE")
            tab_active  = QColor("#FFFFFF")
            tab_inactive= QColor("#D4D4D8")
            tab_hover   = QColor("#E8E8EC")
            fg_active   = QColor("#1C1C1E")
            fg_inactive = QColor("#6E6E73")
            accent      = QColor("#007AFF")
            border_col  = QColor("#C7C7CC")

        radius  = 7   # top corner radius
        cur_idx = self.currentIndex()

        # Fill bar background
        painter.fillRect(event.rect(), bar_bg)

        # ── Draw tabs ─────────────────────────────────────────────────────
        for i in range(self.count()):
            tr      = self.tabRect(i)
            active  = (i == cur_idx)
            hovered = (i == self._hovered_close) # reuse for tab hover? no — use separate
            bg      = tab_active if active else tab_inactive

            # Build a path with rounded top corners only
            path = QPainterPath()
            r    = float(radius)
            l, t, w, h = float(tr.left()), float(tr.top()), float(tr.width()), float(tr.height())
            path.moveTo(l, t + h)          # bottom-left
            path.lineTo(l, t + r)
            path.quadTo(l, t, l + r, t)   # top-left rounded
            path.lineTo(l + w - r, t)
            path.quadTo(l + w, t, l + w, t + r)  # top-right rounded
            path.lineTo(l + w, t + h)      # bottom-right
            path.closeSubpath()

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg))
            painter.drawPath(path)

            # Active tab: bottom accent line
            if active:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(accent))
                painter.drawRect(
                    int(l) + 1, int(t + h) - 2,
                    int(w) - 2, 2
                )
            else:
                # Separator between inactive tabs
                painter.setPen(border_col)
                painter.drawLine(int(l + w) - 1, int(t) + 4,
                                 int(l + w) - 1, int(t + h) - 4)

            # Tab label
            text_color = fg_active if active else fg_inactive
            painter.setPen(text_color)
            font = painter.font()
            font.setPointSize(11)
            font.setWeight(600 if active else 400)
            painter.setFont(font)

            # Text rect: leave room for close button on the right
            text_rect = tr.adjusted(10, 0, -(self._CLOSE_SIZE + self._CLOSE_MARGIN + 4), 0)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self.tabText(i),
            )

            # Close button X (skip if tab is being renamed)
            if i != self._rename_index:
                cr      = self._close_rect(i)
                x_color = QColor("#7A7A7E" if self._dark else "#8E8E93")
                pen     = QPen(x_color)
                pen.setWidth(2)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                pad = 4
                painter.drawLine(cr.left()+pad, cr.top()+pad,
                                 cr.right()-pad, cr.bottom()-pad)
                painter.drawLine(cr.right()-pad, cr.top()+pad,
                                 cr.left()+pad, cr.bottom()-pad)

        # ── "+" button ────────────────────────────────────────────────────
        pr = self._plus_rect()
        if self._plus_hovered:
            plus_bg = QColor("#3A3A3C" if self._dark else "#D1D1D6")
            painter.setBrush(QBrush(plus_bg))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(pr.adjusted(3, 4, -3, -4), 6, 6)

        plus_color = QColor("#AEAEB2" if self._dark else "#636366")
        pen = QPen(plus_color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        cx, cy = pr.center().x(), pr.center().y()
        arm = 6
        painter.drawLine(cx-arm, cy, cx+arm, cy)
        painter.drawLine(cx, cy-arm, cx, cy+arm)



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

    def leaveEvent(self, event):
        self._hovered_close = -1
        self._plus_hovered  = False
        self.update()
        super().leaveEvent(event)

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
        self.setMovable(True)
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
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f'Save changes to "{name}"?',
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self._request_save(editor):
                    return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False

        self.removeTab(index)
        if self.count() == 0:
            self.new_tab()
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
