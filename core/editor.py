# core/editor.py -- NovaPad Editor Widget (v5)
#
# Base class: QTextEdit (not QPlainTextEdit).
# QTextEdit supports rich text natively AND QSyntaxHighlighter.
# The line-number gutter uses QTextDocument.documentLayout() block iteration,
# which is available on QTextEdit via the same underlying QTextDocument API.
#
# TWO MODES per tab, auto-detected from extension and user-toggleable:
#
#   CODE mode  -- monospace font, syntax highlighting active,
#                 B/I/U toolbar buttons disabled, saves as plain text
#
#   RICH mode  -- proportional or any font, formatting toolbar active,
#                 syntax highlighting disabled, saves as HTML for .html
#                 files, plain text for everything else

from __future__ import annotations
import os

from PyQt6.QtCore    import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui     import (
    QColor, QFont, QFontMetrics, QPainter,
    QTextBlockFormat, QTextBlockUserData,
    QTextCharFormat, QTextCursor, QTextFormat, QKeyEvent, QWheelEvent,
)
from PyQt6.QtWidgets import QTextEdit, QWidget

from core.highlighter import NovaPadHighlighter


# ---------------------------------------------------------------------------
# Language / mode tables
# ---------------------------------------------------------------------------

_CODE_EXTS = {
    ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".mjs",
    ".json", ".xml", ".svg", ".css", ".scss", ".less",
    ".c", ".cpp", ".h", ".cs", ".java", ".rb", ".go",
    ".rs", ".php", ".sh", ".bash", ".toml", ".yaml", ".yml",
    ".lua", ".luau",
}

_EXT_TO_LANG = {
    ".py": "python", ".pyw": "python",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "javascript", ".tsx": "javascript", ".mjs": "javascript",
    ".json": "json",
    ".html": "html", ".htm": "html",
    ".xml": "xml", ".svg": "xml",
    ".css": "css", ".scss": "css", ".less": "css",
    ".lua": "lua", ".luau": "lua",
}


def _detect_mode(path: str) -> str:
    ext = os.path.splitext(path)[1].lower() if path else ""
    return "code" if ext in _CODE_EXTS else "rich"


def _detect_language(path: str) -> str:
    ext = os.path.splitext(path)[1].lower() if path else ""
    return _EXT_TO_LANG.get(ext, "plain")


def _sniff_language(content: str) -> str:
    """
    Detect language from content when no file extension is available.
    Checks the first non-empty line for common patterns.
    """
    if not content.strip():
        return "plain"
    first = ""
    for line in content.splitlines():
        s = line.strip()
        if s:
            first = s
            break
    # Lua: local, function, end, --, require
    import re
    if re.search(r'^(?:local|function|--)|\bend\b|\brequire\s*\(', first):
        return "lua"
    # Python: def, class, import, #
    if re.search(r'^(?:def |class |import |from |#)', first):
        return "python"
    # JavaScript
    if re.search(r'^(?:const |let |var |function |//|import |export )', first):
        return "javascript"
    # JSON
    if first.startswith(('{', '[')):
        return "json"
    return "plain" 


# ---------------------------------------------------------------------------
# Timestamp block marker
# ---------------------------------------------------------------------------

class _TimestampData(QTextBlockUserData):
    """Marker attached to QTextBlock to flag it as a read-only timestamp line."""
    pass

_TIMESTAMP_MARKER = _TimestampData  # used for isinstance checks


# Sentinel prefix written to disk so timestamps survive save/reload.
# Chosen to be invisible in normal text and never typed by a user.
_TS_SENTINEL = chr(0xE000) + "NOVAPAD_TS" + chr(0xE000)


# Sentinel prefix written to disk so timestamps survive save/reload.
# Uses Unicode private-use area (U+E000) -- never typed by a user,
# invisible in normal editors, safe in UTF-8 files.
_TS_SENTINEL = chr(0xE000) + "NOVAPAD_TS" + chr(0xE000)


def _is_timestamp_block(block) -> bool:
    """Return True if this QTextBlock is a protected timestamp line."""
    return isinstance(block.userData(), _TimestampData)


# ---------------------------------------------------------------------------
# Line number gutter
# ---------------------------------------------------------------------------

class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


# ---------------------------------------------------------------------------
# CodeEditor
# ---------------------------------------------------------------------------

class CodeEditor(QTextEdit):
    """
    Dual-mode (code / rich text) editor widget.

    Signals
    -------
    modification_changed(bool)   -- from QTextDocument
    cursor_format_changed()      -- cursor moved; toolbar should re-read state
    mode_changed(str)            -- 'code' or 'rich'
    """

    modification_changed  = pyqtSignal(bool)
    cursor_format_changed = pyqtSignal()
    mode_changed          = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._file_path:      str | None = None
        self._language:       str        = "plain"
        self._mode:           str        = "rich"
        self._dark_mode:      bool       = False
        self._show_line_nums: bool        = True
        self._tab_width:      int        = 4

        self._line_num_area = LineNumberArea(self)
        self._bookmark_manager = None  # set by MainWindow
        self._highlighter   = NovaPadHighlighter(self.document(), "plain", False)

        self._setup_font()
        self._setup_editor()
        self._connect_signals()

    # -- Setup ---------------------------------------------------------------

    def _setup_font(self):
        for name, size in [
            ("JetBrains Mono", 11), ("Cascadia Code", 11),
            ("Cascadia Mono",  11), ("Consolas", 11), ("Courier New", 11),
        ]:
            f = QFont(name, size)
            f.setFixedPitch(True)
            if f.exactMatch():
                break
        f.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        f.setStyleStrategy(
            QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality
        )
        self._code_font = f
        self.setFont(f)
        self._update_tab_stop()

    def _setup_editor(self):
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFrameShape(QTextEdit.Shape.NoFrame)
        self.setAcceptRichText(True)
        self.update_line_number_area_width()

    def _connect_signals(self):
        self.document().contentsChanged.connect(self._on_contents_changed)
        self.document().blockCountChanged.connect(self._on_block_count_changed)
        self.document().modificationChanged.connect(self.modification_changed)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        # QTextEdit has no updateRequest signal -- drive gutter repaints manually
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._on_cursor_changed()

    # -- Font / tab ----------------------------------------------------------

    def _update_tab_stop(self):
        self.setTabStopDistance(
            self._tab_width * QFontMetrics(self.font()).horizontalAdvance(" ")
        )

    def setFont(self, font: QFont):
        super().setFont(font)
        self._update_tab_stop()

    # -- file_path -----------------------------------------------------------

    @property
    def file_path(self) -> str | None:
        return self._file_path

    @file_path.setter
    def file_path(self, path: str | None):
        self._file_path = path
        if path:
            lang = _detect_language(path)
            if lang != self._language:
                self._language = lang
                if self._mode == "code":
                    self._highlighter.set_language(lang)
            new_mode = _detect_mode(path)
            if new_mode != self._mode:
                self.set_mode(new_mode)

    @property
    def language(self) -> str:
        return self._language

    # -- Mode ----------------------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str):
        if mode == self._mode:
            return
        self._mode = mode
        if mode == "code":
            plain = self.toPlainText()
            self.setAcceptRichText(False)
            self.setPlainText(plain)
            self.setFont(self._code_font)
            self._update_tab_stop()
            # If no file extension, try to sniff language from content
            lang = self._language
            if lang == "plain" and plain.strip():
                sniffed = _sniff_language(plain)
                if sniffed != "plain":
                    self._language = sniffed
                    lang = sniffed
            self._highlighter.set_language(lang)
            self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        else:
            self.setAcceptRichText(True)
            self._highlighter.set_language("plain")
        self.mode_changed.emit(mode)

    def is_rich_mode(self) -> bool:
        return self._mode == "rich"

    # -- Theme ---------------------------------------------------------------

    def set_dark_mode(self, dark: bool):
        if dark == self._dark_mode:
            return
        self._dark_mode = dark
        self._highlighter.set_dark_mode(dark)
        self._highlight_current_line()

    # -- Word wrap -----------------------------------------------------------

    def set_word_wrap(self, on: bool):
        self.setLineWrapMode(
            QTextEdit.LineWrapMode.WidgetWidth if on
            else QTextEdit.LineWrapMode.NoWrap
        )

    # -- Line numbers --------------------------------------------------------

    def line_number_area_width(self) -> int:
        if not self._show_line_nums:
            return 0
        # Count only real (non-timestamp) blocks for width calculation
        doc   = self.document()
        block = doc.begin()
        real  = 0
        while block.isValid():
            if not _is_timestamp_block(block):
                real += 1
            block = block.next()
        digits = max(3, len(str(max(1, real))))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def toggle_line_numbers(self, visible: bool):
        self._show_line_nums = visible
        self._line_num_area.setVisible(visible)
        self.update_line_number_area_width()

    def update_line_number_area_width(self, _: int = 0):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_num_area.setGeometry(
            QRect(cr.left(), cr.top(),
                  self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_num_area)

        if self._dark_mode:
            bg, fg, cur, sep = (
                QColor("#1C1F26"), QColor("#4B5263"),
                QColor("#ABB2BF"), QColor("#2A2D35"),
            )
        else:
            bg, fg, cur, sep = (
                QColor("#F3F4F6"), QColor("#9CA3AF"),
                QColor("#374151"), QColor("#E5E7EB"),
            )

        painter.fillRect(event.rect(), bg)
        painter.setPen(sep)
        painter.drawLine(
            self._line_num_area.width() - 1, event.rect().top(),
            self._line_num_area.width() - 1, event.rect().bottom(),
        )

        doc       = self.document()
        layout    = doc.documentLayout()
        scroll_y  = self.verticalScrollBar().value()
        line_h    = self.fontMetrics().height()
        cur_block = self.textCursor().blockNumber()

        # Find the last block that has content or is the cursor's block
        # so we don't show line numbers for trailing empty lines.
        last_meaningful = 0
        b = doc.begin()
        bn = 0
        while b.isValid():
            if b.text().strip() or bn == cur_block:
                last_meaningful = bn
            b = b.next()
            bn += 1

        block     = doc.begin()
        block_num = 0   # Qt block index (includes timestamp blocks)
        line_num  = 0   # visible line counter (skips timestamp blocks)

        painter.setFont(self.font())

        while block.isValid():
            rect = layout.blockBoundingRect(block)
            top  = int(rect.top()) - scroll_y
            if top > event.rect().bottom():
                break
            bot = top + int(rect.height())
            if bot >= event.rect().top():
                if _is_timestamp_block(block):
                    # Show em-dash in gutter — not a real line
                    ts_color = QColor("#3A3A3C" if self._dark_mode else "#C7C7CC")
                    painter.setPen(ts_color)
                    painter.drawText(
                        0, top, self._line_num_area.width() - 8, line_h,
                        Qt.AlignmentFlag.AlignRight, "—",
                    )
                else:
                    # Only draw number for blocks at or before last meaningful
                    if block_num <= last_meaningful:
                        painter.setPen(cur if block_num == cur_block else fg)
                        painter.drawText(
                            0, top, self._line_num_area.width() - 8, line_h,
                            Qt.AlignmentFlag.AlignRight, str(line_num + 1),
                        )
                    # Bookmark dot
                    if (self._bookmark_manager and
                            self._bookmark_manager.has_bookmark(self, block_num)):
                        dot_color = QColor("#0A84FF")
                        painter.setBrush(dot_color)
                        painter.setPen(Qt.PenStyle.NoPen)
                        dot_x = 3
                        dot_y = top + (line_h - 6) // 2
                        painter.drawEllipse(dot_x, dot_y, 6, 6)
                        painter.setPen(cur if block_num == cur_block else fg)
                        painter.setBrush(Qt.BrushStyle.NoBrush)
            if not _is_timestamp_block(block):
                line_num += 1
            block     = block.next()
            block_num += 1

    # -- Current-line highlight ----------------------------------------------

    def _highlight_current_line(self):
        sels = []
        if not self.isReadOnly():
            # Don't highlight timestamp lines — they have their own background
            if not _is_timestamp_block(self.textCursor().block()):
                sel   = QTextEdit.ExtraSelection()
                color = QColor("#2C313A") if self._dark_mode else QColor("#EAF0FB")
                sel.format.setBackground(color)
                sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                sel.cursor = self.textCursor()
                sel.cursor.clearSelection()
                sels.append(sel)
        self.setExtraSelections(sels)

    # -- Rich text formatting API --------------------------------------------

    def _merge(self, fmt: QTextCharFormat):
        """Apply format to selection; also set as default for future typing."""
        cursor = self.textCursor()
        cursor.mergeCharFormat(fmt)
        self.mergeCurrentCharFormat(fmt)
        self.setTextCursor(cursor)

    def toggle_bold(self):
        if self._mode != "rich":
            return
        fmt = QTextCharFormat()
        is_bold = (self.textCursor().charFormat().fontWeight()
                   >= QFont.Weight.Bold)
        fmt.setFontWeight(
            QFont.Weight.Normal if is_bold else QFont.Weight.Bold
        )
        self._merge(fmt)
        self.cursor_format_changed.emit()

    def toggle_italic(self):
        if self._mode != "rich":
            return
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.textCursor().charFormat().fontItalic())
        self._merge(fmt)
        self.cursor_format_changed.emit()

    def toggle_underline(self):
        if self._mode != "rich":
            return
        fmt = QTextCharFormat()
        fmt.setFontUnderline(
            not self.textCursor().charFormat().fontUnderline()
        )
        self._merge(fmt)
        self.cursor_format_changed.emit()

    def set_font_family(self, family: str):
        fmt = QTextCharFormat()
        fmt.setFontFamilies([family])
        self._merge(fmt)

    def set_font_size(self, size: float):
        if size > 0:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(size)
            self._merge(fmt)

    # -- Format state (read by formatting toolbar) ---------------------------

    @property
    def current_bold(self) -> bool:
        return (self.textCursor().charFormat().fontWeight()
                >= QFont.Weight.Bold)

    @property
    def current_italic(self) -> bool:
        return self.textCursor().charFormat().fontItalic()

    @property
    def current_underline(self) -> bool:
        return self.textCursor().charFormat().fontUnderline()

    @property
    def current_font_family(self) -> str:
        fams = self.textCursor().charFormat().fontFamilies()
        return fams[0] if fams else self.font().family()

    @property
    def current_font_size(self) -> float:
        sz = self.textCursor().charFormat().fontPointSize()
        return sz if sz > 0 else float(self.font().pointSize())

    # -- Content I/O ---------------------------------------------------------

    def load_content(self, content: str, path: str | None = None):
        """
        Load content as plain text always — no rich text rendering.
        Restores any sentinel timestamp lines as tagged blocks.
        """
        # Check if file contains any timestamp sentinels
        if _TS_SENTINEL in content:
            # Load line by line, restoring timestamp blocks
            self.clear()
            lines = content.split("\n")
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            first = True
            for line in lines:
                if not first:
                    cursor.insertBlock()
                first = False
                if line.startswith(_TS_SENTINEL):
                    # Restore as a tagged timestamp block
                    display = line[len(_TS_SENTINEL):]
                    cursor.insertText(display)
                    block = cursor.block()
                    block.setUserData(_TimestampData())
                    char_fmt = QTextCharFormat()
                    char_fmt.setForeground(QColor("#6B7280"))
                    char_fmt.setFontItalic(True)
                    sel = QTextCursor(block)
                    sel.select(QTextCursor.SelectionType.BlockUnderCursor)
                    sel.setCharFormat(char_fmt)
                else:
                    cursor.insertText(line)
        else:
            self.setPlainText(content)

        self.document().setModified(False)

    def get_content_for_save(self, path: str | None = None) -> str:
        """
        Serialize document to string for saving.

        - Timestamp blocks are written with the _TS_SENTINEL prefix so they
          survive save/reload as protected lines.
        - HTML saves use toHtml() (rich formatting preserved).
        """
        ext = os.path.splitext(path)[1].lower() if path else ""
        # Always save as plain text regardless of extension
        # Walk blocks: timestamp lines get sentinel prefix, others plain text
        doc   = self.document()
        block = doc.begin()
        lines = []
        while block.isValid():
            if _is_timestamp_block(block):
                lines.append(_TS_SENTINEL + block.text())
            else:
                lines.append(block.text())
            block = block.next()
        return "\n".join(lines)

    def get_plain_export(self) -> str:
        """
        Export document as pure plain text with all timestamp lines removed.
        Use this for copy-all, print, or explicit plain-text export.
        """
        doc   = self.document()
        block = doc.begin()
        lines = []
        while block.isValid():
            if not _is_timestamp_block(block):
                lines.append(block.text())
            block = block.next()
        return "\n".join(lines)

    # -- Timestamp insertion -------------------------------------------------

    def insert_timestamp(self):
        """
        Insert a styled, read-only timestamp line at the current position.
        Format: 3:54 PM  March 25 2026  (local time, 12-hour, no brackets)
        The line is excluded from plain-text export.
        """
        import datetime
        now = datetime.datetime.now().astimezone()   # local timezone-aware
        # 12-hour time (no leading zero on Windows needs %-I, use lstrip trick)
        time_part = now.strftime("%I:%M %p").lstrip("0")
        date_part = now.strftime("%B %d %Y").replace(" 0", " ")
        ts = f"{time_part}  {date_part}" 

        cursor = self.textCursor()
        cursor.beginEditBlock()

        # Move to end of current line before inserting
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)

        # Insert newline + timestamp text
        cursor.insertBlock()
        ts_block_pos = cursor.position()
        cursor.insertText(ts)

        # Tag the block as a timestamp
        ts_block = cursor.block()
        ts_block.setUserData(_TimestampData())

        # Grey italic text only — no background
        char_fmt = QTextCharFormat()
        char_fmt.setForeground(QColor("#6B7280"))
        char_fmt.setFontItalic(True)

        # Select the entire timestamp text and apply formatting
        sel = QTextCursor(ts_block)
        sel.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        sel.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        sel.setCharFormat(char_fmt)

        # Insert a new empty line below the timestamp
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertBlock()

        # Reset char format on the new line to completely plain.
        # Use setCharFormat (replaces, not merges) so no italic/grey bleeds in.
        plain_fmt = QTextCharFormat()
        plain_fmt.setFontItalic(False)
        plain_fmt.setFontWeight(400)
        # Clear foreground so it inherits editor default
        cursor.setCharFormat(plain_fmt)

        cursor.endEditBlock()
        self.setTextCursor(cursor)
        # Reset the widget-level "current" char format so next typed char is plain
        self.setCurrentCharFormat(plain_fmt)

    # -- Keyboard ------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        key  = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)

        # ── Timestamp line protection ─────────────────────────────────────
        # If cursor is on a timestamp block, block all editing keystrokes.
        # Navigation keys (arrows, Home, End, Page) are allowed through.
        cursor = self.textCursor()
        if _is_timestamp_block(cursor.block()):
            NAV_KEYS = {
                Qt.Key.Key_Left, Qt.Key.Key_Right,
                Qt.Key.Key_Up,   Qt.Key.Key_Down,
                Qt.Key.Key_Home, Qt.Key.Key_End,
                Qt.Key.Key_PageUp, Qt.Key.Key_PageDown,
            }
            if key not in NAV_KEYS:
                # Jump cursor past the timestamp block instead of editing it
                cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                self.setTextCursor(cursor)
                return
        # ─────────────────────────────────────────────────────────────────

        # ── Backspace on line after timestamp → delete the timestamp ──────
        # If cursor is at column 0 of a line and the previous block is a
        # timestamp, Backspace deletes the timestamp block instead of merging.
        if key == Qt.Key.Key_Backspace:
            c = self.textCursor()
            if c.columnNumber() == 0 and not c.hasSelection():
                prev = c.block().previous()
                if prev.isValid() and _is_timestamp_block(prev):
                    self._delete_timestamp_block(prev)
                    return
        # ─────────────────────────────────────────────────────────────────

        # Rich-mode shortcuts (Ctrl+B/I/U) only when NOT in code mode
        if self._mode == "rich" and ctrl:
            if key == Qt.Key.Key_B:
                self.toggle_bold(); return
            if key == Qt.Key.Key_I:
                self.toggle_italic(); return
            if key == Qt.Key.Key_U:
                self.toggle_underline(); return

        # Tab -> spaces
        if key == Qt.Key.Key_Tab and not (mods & Qt.KeyboardModifier.ShiftModifier):
            cursor = self.textCursor()
            if cursor.hasSelection():
                self._indent_selection(cursor, True)
            else:
                cursor.insertText(" " * self._tab_width)
            return

        # Shift+Tab -> un-indent
        if key == Qt.Key.Key_Backtab:
            self._indent_selection(self.textCursor(), False)
            return

        # Treat Shift+Enter the same as plain Enter (no soft line breaks)
        if (key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and (mods & Qt.KeyboardModifier.ShiftModifier)):
            # Strip the Shift modifier so Qt inserts a normal block break
            from PyQt6.QtGui import QKeyEvent as _QKE
            plain_event = _QKE(
                event.type(), key,
                Qt.KeyboardModifier.NoModifier,
                event.text(),
            )
            super().keyPressEvent(plain_event)
            return

        super().keyPressEvent(event)

    def _delete_timestamp_block(self, block):
        """Remove a timestamp block cleanly, preserving undo history."""
        cursor = QTextCursor(block)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        # removeSelectedText leaves an empty block; delete it too
        cursor.deleteChar()
        cursor.endEditBlock()
        self.setTextCursor(self.textCursor())  # refresh

    def _indent_selection(self, cursor: QTextCursor, indent: bool):
        doc     = self.document()
        b_start = doc.findBlock(cursor.selectionStart())
        b_end   = doc.findBlock(cursor.selectionEnd())
        cursor.beginEditBlock()
        block = b_start
        while True:
            c = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            if indent:
                c.insertText(" " * self._tab_width)
            else:
                text   = block.text()
                spaces = len(text) - len(text.lstrip(" "))
                remove = min(spaces, self._tab_width)
                c.movePosition(
                    QTextCursor.MoveOperation.Right,
                    QTextCursor.MoveMode.KeepAnchor, remove,
                )
                c.removeSelectedText()
            if block == b_end:
                break
            block = block.next()
        cursor.endEditBlock()

    # -- Smooth scrolling ----------------------------------------------------

    def wheelEvent(self, event: QWheelEvent):
        """Smooth scrolling: multiply delta for a more natural feel."""
        delta = event.angleDelta().y()
        if delta != 0:
            sb = self.verticalScrollBar()
            # 3 lines per notch feels natural; standard is ~1-2
            pixels_per_notch = self.fontMetrics().height() * 3
            steps = -delta / 120 * pixels_per_notch / self.fontMetrics().height()
            sb.setValue(int(sb.value() + steps * self.fontMetrics().height()))
            event.accept()
        else:
            super().wheelEvent(event)

    # -- Slots ---------------------------------------------------------------

    def _on_contents_changed(self):
        self.update_line_number_area_width()
        self._line_num_area.update()

    def _on_block_count_changed(self, _=None):
        self.update_line_number_area_width()
        self._line_num_area.update()

    def _on_scroll(self, _=None):
        self._line_num_area.update()

    def _on_cursor_changed(self):
        self._highlight_current_line()
        self._line_num_area.update()
        self.cursor_format_changed.emit()
        # If cursor landed on a timestamp block via mouse click,
        # push it to the next editable line automatically.
        self._guard_timestamp_cursor()
        # If cursor is on a normal block but has inherited timestamp formatting,
        # clear it so typing doesn't come out grey/italic.
        if not _is_timestamp_block(self.textCursor().block()):
            fmt = self.currentCharFormat()
            if fmt.fontItalic() or fmt.foreground().color() == QColor("#6B7280"):
                clean = QTextCharFormat()
                clean.setFontItalic(False)
                clean.setFontWeight(400)
                self.setCurrentCharFormat(clean)

    def _guard_timestamp_cursor(self):
        """If cursor is on a timestamp block, move to the next line."""
        cursor = self.textCursor()
        block  = cursor.block()
        if not _is_timestamp_block(block):
            return
        # Move to next block; if at end of doc, insert a new block first
        next_block = block.next()
        if next_block.isValid():
            new_cursor = QTextCursor(next_block)
            new_cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        else:
            # Timestamp is the last block — append a new line
            new_cursor = QTextCursor(block)
            new_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            new_cursor.insertBlock()
            # Reset format on the new line
            plain_fmt = QTextCharFormat()
            new_cursor.setCharFormat(plain_fmt)
        # Block the signal temporarily to avoid re-entrancy
        self.cursorPositionChanged.disconnect(self._on_cursor_changed)
        self.setTextCursor(new_cursor)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        # Clear any inherited timestamp formatting from the current char format
        plain_fmt = QTextCharFormat()
        plain_fmt.setFontItalic(False)
        plain_fmt.setFontWeight(400)
        self.setCurrentCharFormat(plain_fmt)

    # -- Utilities -----------------------------------------------------------

    def cursor_position(self) -> tuple[int, int]:
        c = self.textCursor()
        return c.blockNumber() + 1, c.columnNumber() + 1
