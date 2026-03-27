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

from PyQt6.QtCore    import Qt, QRect, QSize, QTimer, pyqtSignal
from PyQt6.QtGui     import (
    QColor, QFont, QFontMetrics, QPainter, QPen, QPalette,
    QTextBlockUserData,
    QTextCharFormat, QTextCursor, QTextFormat, QKeyEvent, QWheelEvent,
)
from PyQt6.QtWidgets import QTextEdit, QWidget

from core.highlighter import NovaPadHighlighter
from ui.theme import ThemeManager


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
    import re
    # Lua: local, function, end, --, require
    if re.search(r'^(?:local\b|function\b|--)|end|\brequire\s*\(', first):
        return "lua"
    # Python
    if re.search(r'^(?:def |class |import |from |#!?)', first):
        return "python"
    # JavaScript / TypeScript
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



def _make_combined_font(family: str, size: int, bold: bool, italic: bool, underline: bool):
    """
    Request the correct font sub-family for bold+italic by querying QFontDatabase.
    On Windows, 'Bold Italic' is a named sub-family that must be requested by name.
    """
    from PyQt6.QtGui import QFontDatabase
    # QFontDatabase is all static methods in PyQt6
    styles = QFontDatabase.styles(family)
    if bold and italic:
        want = ["Bold Italic", "BoldItalic", "Bold Oblique"]
    elif bold:
        want = ["Bold", "SemiBold", "Demibold"]
    elif italic:
        want = ["Italic", "Oblique"]
    else:
        want = ["Regular", "Normal", "Book", ""]
    chosen = None
    for w in want:
        for s in styles:
            if s.lower() == w.lower():
                chosen = s
                break
        if chosen:
            break
    if chosen:
        f = QFontDatabase.font(family, chosen, size)
    else:
        w = QFont.Weight.Bold if bold else QFont.Weight.Normal
        f = QFont(family, size, int(w), italic)
    f.setUnderline(underline)
    if chosen:
        f.setStyleName(chosen)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)
    return f

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
    zoom_step             = pyqtSignal(int)   # +1 zoom in, -1 zoom out

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
        # Apply rich font as the document default immediately on construction
        self._apply_rich_font_as_default()

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
        # Rich mode font: Segoe UI has genuine Bold/Italic/Bold Italic sub-families
        from PyQt6.QtGui import QFontDatabase as _FDB2
        rich_fam = "Segoe UI"
        for rf_name in ["Segoe UI", "Calibri", "Arial", "Helvetica"]:
            styles = _FDB2.styles(rf_name)
            has_bi = any("bold italic" in s.lower() for s in styles)
            if has_bi:
                rich_fam = rf_name
                break
        self._rich_font_family = rich_fam
        self._rich_font_size   = 12
        rf = _FDB2.font(rich_fam, "Regular", 12) if "Regular" in _FDB2.styles(rich_fam) else QFont(rich_fam, 12)
        rf.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)
        self._rich_font = rf
        self.setFont(f)
        self._update_tab_stop()

    def _setup_editor(self):
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFrameShape(QTextEdit.Shape.NoFrame)
        self.setAcceptRichText(True)
        # Always show horizontal scrollbar when content overflows
        from PyQt6.QtCore import Qt as _Qt
        self.setHorizontalScrollBarPolicy(_Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(_Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.update_line_number_area_width()

    def _connect_signals(self):
        self.document().contentsChanged.connect(self._on_contents_changed)
        self.document().blockCountChanged.connect(self._on_block_count_changed)
        self.document().modificationChanged.connect(self.modification_changed)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._on_cursor_changed()
        # Auto-sniff language for untitled files after a short delay
        self._sniff_timer    = None
        self._extra_cursors  = []          # list of QTextCursor objects
        self._cursor_blink_on = True
        # Use system cursor flash time; half-period for on/off toggle
        from PyQt6.QtWidgets import QApplication as _QApp
        flash = max(400, _QApp.cursorFlashTime())
        self._cursor_half    = flash // 2
        self._cursor_timer   = QTimer(self)
        self._cursor_timer.timeout.connect(self._on_cursor_blink)
        self._cursor_timer.start(self._cursor_half)
        # Hide native cursor - we draw it ourselves for sync
        self.setCursorWidth(0)
        # Initialise palette with current theme colors (updated again in set_dark_mode)
        self._apply_cursor_color()

    # -- Font / tab ----------------------------------------------------------

    def _apply_rich_font_as_default(self):
        """
        Set the rich font as the document default AND stamp it onto every
        existing character in the document so it applies immediately to all
        content — not just new text.
        """
        if not hasattr(self, "_rich_font") or self._mode != "rich":
            return
        # 1. Document-level default (affects display and new blocks)
        self.document().setDefaultFont(self._rich_font)
        self.setFont(self._rich_font)
        # 2. Walk every block: stamp blockCharFormat AND mergeCharFormat so
        #    both empty lines and lines with text render at the correct size.
        doc = self.document()
        rfmt = QTextCharFormat()
        rfmt.setFontFamilies([self._rich_font_family])
        rfmt.setFontPointSize(float(self._rich_font_size))
        block = doc.begin()
        while block.isValid():
            if not _is_timestamp_block(block):
                bc = QTextCursor(block)
                bc.setBlockCharFormat(rfmt)   # controls empty-line height
                bc.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                bc.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                QTextCursor.MoveMode.KeepAnchor)
                bc.mergeCharFormat(rfmt)      # controls typed-text font
            block = block.next()
        # 3. Set as current insertion format
        self.setCurrentCharFormat(rfmt)

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
            self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            self._apply_rich_font_as_default()
        self.mode_changed.emit(mode)

    def is_rich_mode(self) -> bool:
        return self._mode == "rich"

    # -- Theme ---------------------------------------------------------------

    def set_dark_mode(self, dark: bool):
        self._dark_mode = dark
        self._highlighter.set_dark_mode(dark)
        self._highlight_current_line()
        self._apply_cursor_color()

    def apply_theme(self):
        """Called on theme change to refresh all theme-dependent colors live."""
        self._apply_cursor_color()
        self._highlight_current_line()
        self._refresh_timestamp_colors()

    def _apply_cursor_color(self):
        """
        Sync palette with current theme, guaranteeing high-contrast selection.
        Uses WCAG contrast ratio logic: sel_bg vs sel_fg must have ratio >= 4.5.
        Falls back to white-on-accent or black-on-accent for blue/coloured themes.
        """
        t = ThemeManager.current()

        def _luma(c: QColor) -> float:
            """Relative luminance per WCAG 2.1."""
            def _lin(v):
                v = v / 255.0
                return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
            return 0.2126 * _lin(c.red()) + 0.7152 * _lin(c.green()) + 0.0722 * _lin(c.blue())

        def _contrast(c1: QColor, c2: QColor) -> float:
            l1, l2 = _luma(c1), _luma(c2)
            if l1 < l2: l1, l2 = l2, l1
            return (l1 + 0.05) / (l2 + 0.05)

        # Build a high-visibility selection background from the accent color.
        # Use the theme's sel_bg, but if its contrast with sel_fg is < 3.0,
        # derive a better pair: accent color at 70% opacity over editor bg.
        sel_bg = QColor(t["sel_bg"])
        sel_fg = QColor(t["sel_fg"])
        acc    = QColor(t["accent"])

        if _contrast(sel_bg, sel_fg) < 3.0:
            # Compose accent at 55% over editor background for the highlight
            bg_ed = QColor(t["bg_editor"])
            r = int(acc.red()   * 0.55 + bg_ed.red()   * 0.45)
            g = int(acc.green() * 0.55 + bg_ed.green()  * 0.45)
            b = int(acc.blue()  * 0.55 + bg_ed.blue()   * 0.45)
            sel_bg = QColor(r, g, b)
            # Choose white or black text based on sel_bg luminance
            sel_fg = QColor("#FFFFFF") if _luma(sel_bg) < 0.4 else QColor("#000000")

        # Final safety check: always ensure at least 4.5:1 ratio
        if _contrast(sel_bg, sel_fg) < 4.5:
            sel_fg = QColor("#FFFFFF") if _luma(sel_bg) < 0.5 else QColor("#000000")

        p = self.palette()
        p.setColor(QPalette.ColorRole.Text,            QColor(t["fg_primary"]))
        p.setColor(QPalette.ColorRole.Base,            QColor(t["bg_editor"]))
        p.setColor(QPalette.ColorRole.WindowText,      QColor(t["fg_primary"]))
        p.setColor(QPalette.ColorRole.Highlight,       sel_bg)
        p.setColor(QPalette.ColorRole.HighlightedText, sel_fg)
        self.setPalette(p)

    def _refresh_timestamp_colors(self):
        """Recolor all timestamp blocks to match the current theme gutter color."""
        t    = ThemeManager.current()
        col  = QColor(t["gutter_fg"])
        doc  = self.document()
        block = doc.begin()
        while block.isValid():
            if _is_timestamp_block(block):
                fmt = QTextCharFormat()
                fmt.setForeground(col)
                fmt.setFontItalic(True)
                cur = QTextCursor(block)
                cur.select(QTextCursor.SelectionType.BlockUnderCursor)
                cur.mergeCharFormat(fmt)
            block = block.next()

    # -- Word wrap -----------------------------------------------------------

    def set_word_wrap(self, on: bool):
        self.setLineWrapMode(
            QTextEdit.LineWrapMode.WidgetWidth if on
            else QTextEdit.LineWrapMode.NoWrap
        )
        from PyQt6.QtCore import Qt as _Qt
        self.setHorizontalScrollBarPolicy(
            _Qt.ScrollBarPolicy.ScrollBarAlwaysOff if on
            else _Qt.ScrollBarPolicy.ScrollBarAsNeeded
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

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._line_num_area.update()

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_num_area)

        t   = ThemeManager.current()
        # Gutter blends into editor background — same color, no separator
        bg  = QColor(t["bg_editor"])
        fg  = QColor(t["fg_muted"])       # dim numbers
        cur = QColor(t["fg_secondary"])   # current line number slightly brighter
        # No sep line — gutter is invisible, just floats on editor bg

        painter.fillRect(event.rect(), bg)

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
                if _is_timestamp_block(block) and block.isVisible():
                    from assets.icons import get_icon as _gi
                    _ts_color = QColor(t["fg_muted"])
                    _icon_px  = _gi("clock", _ts_color.name(), line_h).pixmap(line_h, line_h)
                    _gw       = self._line_num_area.width()
                    _ix       = _gw - 8 - line_h
                    _iy       = top + (int(rect.height()) - line_h) // 2
                    painter.drawPixmap(_ix, _iy, _icon_px)
                elif not _is_timestamp_block(block) and block.isVisible():
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
                        from PyQt6.QtCore import QRectF
                        dot_color = QColor(ThemeManager.current()["accent"])
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                        painter.setBrush(dot_color)
                        painter.setPen(Qt.PenStyle.NoPen)
                        dot_r  = 3.5
                        dot_cx = dot_r + 1.5
                        dot_cy = top + line_h / 2.0
                        painter.drawEllipse(QRectF(dot_cx - dot_r, dot_cy - dot_r,
                                                   dot_r * 2, dot_r * 2))
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                        painter.setPen(cur if block_num == cur_block else fg)
                        painter.setBrush(Qt.BrushStyle.NoBrush)
            if not _is_timestamp_block(block) and block.isVisible():
                line_num += 1
            block     = block.next()
            block_num += 1

    # -- Current-line highlight ----------------------------------------------

    def _highlight_current_line(self):
        sels = []
        if not self.isReadOnly():
            # Don't highlight timestamp lines - they have their own background
            if not _is_timestamp_block(self.textCursor().block()):
                sel   = QTextEdit.ExtraSelection()
                color = QColor(ThemeManager.current()["accent"]); color.setAlpha(80)
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

    # ── Bold / Italic / Underline toggling ────────────────────────────────────
    # Uses char-by-char walk over the selection so each character's existing
    # bold/italic/underline state is preserved when only one property changes.
    # Uses _make_combined_font() which queries QFontDatabase for the exact
    # named sub-family (e.g. "Bold Italic") so Windows renders the real face.
    # The toggle direction is determined from selectionEnd-1 (inside selection)
    # to avoid the Qt bug where charFormat() at selectionStart returns the char
    # BEFORE the selection.

    def _toggle_fmt(self, prop: str):
        cursor = self.textCursor()
        fam    = getattr(self, "_rich_font_family", "Segoe UI")
        sz     = getattr(self, "_rich_font_size",   12)

        if cursor.hasSelection():
            sel_start = cursor.selectionStart()
            sel_end   = cursor.selectionEnd()

            # Probe from inside selection to determine toggle direction
            probe = QTextCursor(self.document())
            probe.setPosition(sel_end - 1)
            probe.setPosition(sel_end, QTextCursor.MoveMode.KeepAnchor)
            ref = probe.charFormat()
            if prop == "bold":
                turn_on = ref.fontWeight() < QFont.Weight.Bold
            elif prop == "italic":
                turn_on = not ref.fontItalic()
            else:
                turn_on = not ref.fontUnderline()

            # Disconnect signal to prevent intermediate refreshes
            try:
                self.cursorPositionChanged.disconnect(self._on_cursor_changed)
            except RuntimeError:
                pass

            cursor.beginEditBlock()
            pos = sel_start
            while pos < sel_end:
                c = QTextCursor(self.document())
                c.setPosition(pos)
                c.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
                fmt  = c.charFormat()
                cur_bold  = fmt.fontWeight() >= QFont.Weight.Bold
                cur_ital  = fmt.fontItalic()
                cur_under = fmt.fontUnderline()
                new_bold  = turn_on   if prop == "bold"      else cur_bold
                new_ital  = turn_on   if prop == "italic"    else cur_ital
                new_under = turn_on   if prop == "underline" else cur_under
                # Use char's own family/size if set, else fall back to rich font
                char_fam  = (fmt.fontFamilies() or [fam])[0]
                char_sz   = fmt.fontPointSize() or sz
                new_font  = _make_combined_font(char_fam, int(char_sz),
                                                new_bold, new_ital, new_under)
                fmt.setFont(new_font)
                c.setCharFormat(fmt)
                pos += 1
            cursor.endEditBlock()

            # Restore selection
            cursor.setPosition(sel_start)
            cursor.setPosition(sel_end, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
            # Set currentCharFormat from inside selection so toolbar reads correctly
            inner = QTextCursor(self.document())
            inner.setPosition(sel_end - 1)
            inner.setPosition(sel_end, QTextCursor.MoveMode.KeepAnchor)
            self.setCurrentCharFormat(inner.charFormat())

            self.cursorPositionChanged.connect(self._on_cursor_changed)

        else:
            # No selection: update insertion format, preserving all 3 properties
            cur   = self.currentCharFormat()
            w     = cur.fontWeight() if cur.fontWeight() > 0 else QFont.Weight.Normal
            new_bold  = (not (w >= QFont.Weight.Bold)) if prop == "bold"      else (w >= QFont.Weight.Bold)
            new_ital  = (not cur.fontItalic())          if prop == "italic"    else cur.fontItalic()
            new_under = (not cur.fontUnderline())       if prop == "underline" else cur.fontUnderline()
            char_fam  = (cur.fontFamilies() or [fam])[0]
            char_sz   = cur.fontPointSize() or sz
            new_font  = _make_combined_font(char_fam, int(char_sz), new_bold, new_ital, new_under)
            new_fmt   = QTextCharFormat(cur)
            new_fmt.setFont(new_font)
            self.setCurrentCharFormat(new_fmt)

        self.cursor_format_changed.emit()

    def toggle_bold(self):
        if self._mode == "rich":
            self._toggle_fmt("bold")

    def toggle_italic(self):
        if self._mode == "rich":
            self._toggle_fmt("italic")

    def toggle_underline(self):
        if self._mode == "rich":
            self._toggle_fmt("underline")

    def insertFromMimeData(self, source):
        """Override paste to strip incoming formatting and apply rich font."""
        if self._mode == "rich" and source.hasText():
            # Insert as plain text then apply rich font — prevents pasted fonts
            # from overriding the editor's rich font
            cursor = self.textCursor()
            cursor.insertText(source.text())
            # Re-apply rich font to the just-pasted range
            end_pos   = cursor.position()
            start_pos = end_pos - len(source.text())
            if start_pos < end_pos:
                sel = QTextCursor(self.document())
                sel.setPosition(start_pos)
                sel.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                fmt = sel.charFormat()
                fmt.setFontFamilies([self._rich_font_family])
                fmt.setFontPointSize(self._rich_font_size)
                sel.mergeCharFormat(fmt)
            return
        super().insertFromMimeData(source)

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
        # Use currentCharFormat (reflects insertion state + selection) not charFormat()
        return self.currentCharFormat().fontWeight() >= QFont.Weight.Bold

    @property
    def current_italic(self) -> bool:
        return self.currentCharFormat().fontItalic()

    @property
    def current_underline(self) -> bool:
        return self.currentCharFormat().fontUnderline()

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
        Load content as plain text always - no rich text rendering.
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
        # Re-apply rich font as document default after any content load
        # (setPlainText resets the document but not setDefaultFont)
        self._apply_rich_font_as_default()

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
        Insert a styled, read-only timestamp line ABOVE the current line.
        Format: 3:54 PM  March 25 2026  (local time, 12-hour, no brackets)
        The cursor remains on the original line after insertion.
        The line is excluded from plain-text export.
        """
        import datetime
        now = datetime.datetime.now().astimezone()
        time_part = now.strftime("%I:%M %p").lstrip("0")
        date_part = now.strftime("%B %d %Y").replace(" 0", " ")
        ts = f"{time_part}  {date_part}"

        cursor = self.textCursor()
        saved_col = cursor.columnNumber()

        cursor.beginEditBlock()

        # Move to the very start of the current block.
        # Strategy: insertText(ts) + insertBlock() at StartOfBlock pushes the
        # current content down: Block N becomes the timestamp, Block N+1 becomes
        # the original content with the cursor at its start.
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        orig_block_num  = cursor.blockNumber()
        orig_was_empty  = cursor.block().text() == ""

        # Insert timestamp text at start of block, then split the block.
        # Result: Block N = ts text, Block N+1 = original content, cursor at N+1.
        cursor.insertText(ts)
        if orig_was_empty and cursor.block().next().isValid():
            # Original line was empty and a next line exists: just step to it.
            # Calling insertBlock() here would create a spurious empty artifact block.
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        else:
            cursor.insertBlock()

        # Tag Block N (now containing only the timestamp text) as a timestamp.
        ts_block = self.document().findBlockByNumber(orig_block_num)
        ts_block.setUserData(_TimestampData())

        # Apply timestamp formatting to Block N.
        char_fmt = QTextCharFormat()
        char_fmt.setForeground(QColor(ThemeManager.current()["gutter_fg"]))
        char_fmt.setFontItalic(True)
        ts_sel = QTextCursor(ts_block)
        ts_sel.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        ts_sel.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        ts_sel.setCharFormat(char_fmt)

        # cursor is at position 0 of Block N+1 (original content).
        # Restore the column the user was at before insertion.
        if saved_col > 0:
            line_len = max(0, cursor.block().length() - 1)  # excl. block separator
            cursor.movePosition(QTextCursor.MoveOperation.Right,
                                QTextCursor.MoveMode.MoveAnchor,
                                min(saved_col, line_len))

        # Ensure no timestamp formatting bleeds into the original content line.
        plain_fmt = QTextCharFormat()
        plain_fmt.setFontItalic(False)
        plain_fmt.setFontWeight(400)
        cursor.setCharFormat(plain_fmt)

        cursor.endEditBlock()
        self.setTextCursor(cursor)
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

        # ── Delete at end of line: block merge into a timestamp ───────────
        # Prevents "text\n[timestamp]" from becoming "texttime_entry".
        if key == Qt.Key.Key_Delete and not ctrl:
            c = self.textCursor()
            if not c.hasSelection() and c.atBlockEnd():
                nxt = c.block().next()
                if nxt.isValid() and _is_timestamp_block(nxt):
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
            from PyQt6.QtGui import QKeyEvent as _QKE
            plain_event = _QKE(
                event.type(), key,
                Qt.KeyboardModifier.NoModifier,
                event.text(),
            )
            super().keyPressEvent(plain_event)
            return

        # Auto-indent + auto-list continuation on Enter
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not ctrl:
            import re as _re
            cursor = self.textCursor()
            text   = cursor.block().text()
            indent = len(text) - len(text.lstrip())
            indent_s = text[:indent]
            stripped = text.lstrip()
            list_prefix = None
            if self._mode == "rich":
                m = _re.match(r"^(\d+)\.\s", stripped)
                if m:
                    next_num = int(m.group(1)) + 1
                    list_prefix = f"{next_num}. "
                elif _re.match(r"^[-*•]\s", stripped):
                    list_prefix = stripped[0] + " "
                # Empty list item — exit list
                if list_prefix:
                    content_after_marker = stripped[len(list_prefix):].strip()
                    if not content_after_marker:
                        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                            QTextCursor.MoveMode.KeepAnchor)
                        cursor.removeSelectedText()
                        self.setTextCursor(cursor)
                        return
            super().keyPressEvent(event)
            if list_prefix and self._mode == "rich":
                self.textCursor().insertText(indent_s + list_prefix)
            else:
                self.textCursor().insertText(indent_s)
            # Stamp blockCharFormat on the new empty block so line height
            # matches the current font size (which may be zoomed).
            # Use document().defaultFont() not _rich_font_size so zoom is respected.
            if self._mode == "rich" and hasattr(self, "_rich_font_family"):
                cur_size = self.document().defaultFont().pointSize()
                if cur_size < 1:
                    cur_size = self._rich_font_size
                rfmt = QTextCharFormat()
                rfmt.setFontFamilies([self._rich_font_family])
                rfmt.setFontPointSize(float(cur_size))
                tc = self.textCursor()
                tc.setBlockCharFormat(rfmt)
                self.mergeCurrentCharFormat(rfmt)
            return

        # Bracket / quote auto-close
        PAIRS = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
        if event.text() in PAIRS and not ctrl:
            close = PAIRS[event.text()]
            cursor = self.textCursor()
            if not cursor.hasSelection():
                super().keyPressEvent(event)
                self.textCursor().insertText(close)
                c = self.textCursor()
                c.movePosition(QTextCursor.MoveOperation.Left)
                self.setTextCursor(c)
                return
            else:
                # Wrap selection in the pair
                sel = cursor.selectedText()
                cursor.insertText(event.text() + sel + close)
                return

        # Skip over closing bracket if already there
        CLOSERS = {')', ']', '}'}
        if event.text() in CLOSERS and not ctrl:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                doc = self.document()
                next_char = doc.characterAt(cursor.position())
                if next_char == event.text():
                    cursor.movePosition(QTextCursor.MoveOperation.Right)
                    self.setTextCursor(cursor)
                    return

        # Alt+Up / Alt+Down -> move line; Ctrl+Alt+Up/Down -> add cursor
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)
        if alt and not ctrl and key == Qt.Key.Key_Up:
            self._move_line(-1); return
        if alt and not ctrl and key == Qt.Key.Key_Down:
            self._move_line(1); return
        if ctrl and alt and key == Qt.Key.Key_Up:
            self._add_cursor_above(); return
        if ctrl and alt and key == Qt.Key.Key_Down:
            self._add_cursor_below(); return

        # Ctrl+D -> duplicate line
        if key == Qt.Key.Key_D and ctrl:
            self._duplicate_line(); return

        # Ctrl+/ -> toggle comment
        if key == Qt.Key.Key_Slash and ctrl:
            self._toggle_comment(); return

        # Smart Home
        if key == Qt.Key.Key_Home and not ctrl:
            self._smart_home(mods); return

        # Escape -> clear extra cursors
        if key == Qt.Key.Key_Escape and self._extra_cursors:
            self._extra_cursors.clear()
            self.viewport().update()
            return

        # Multi-cursor: apply keystroke to ALL cursors (main + extra) manually
        if self._extra_cursors and not ctrl:
            ch = event.text()
            k  = event.key()
            self._extra_cursors = [c for c in self._extra_cursors if hasattr(c, 'position')]
            if ch or k in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
                # Collect all cursors including main, sort by position descending
                # so earlier inserts don't shift later positions
                main = self.textCursor()
                all_cursors = sorted(
                    self._extra_cursors + [main],
                    key=lambda x: x.position(), reverse=True
                )
                for c in all_cursors:
                    if k == Qt.Key.Key_Backspace:
                        c.deletePreviousChar()
                    elif k == Qt.Key.Key_Delete:
                        c.deleteChar()
                    elif ch:
                        c.insertText(ch)
                # Update main cursor position (it moved after insertText)
                self.setTextCursor(main)
                self.viewport().update()
                return  # Don't call super() - we handled everything

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

    # ── Multi-cursor ──────────────────────────────────────────────────────

    def mouseDoubleClickEvent(self, event):
        """Double-click on timestamp opens edit dialog."""
        if event.button() == Qt.MouseButton.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            if _is_timestamp_block(cursor.block()):
                self._edit_timestamp(cursor.block())
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def _edit_timestamp(self, block):
        """Open dialog to edit a timestamp block in-place."""
        import datetime
        old_text = block.text().strip()
        try:
            dt = datetime.datetime.strptime(old_text, "%I:%M %p  %B %d %Y")
        except Exception:
            try:
                dt = datetime.datetime.strptime(old_text, "%I:%M %p  %B %d %Y")
            except Exception:
                dt = datetime.datetime.now()
        from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QVBoxLayout,
                                        QHBoxLayout, QLabel, QDateTimeEdit, QFrame)
        from PyQt6.QtCore import QDateTime
        t   = ThemeManager.current()
        acc = t["accent"]
        dlg = QDialog(self)
        dlg.setWindowFlags(dlg.windowFlags() & ~__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.WindowType.WindowContextHelpButtonHint)
        dlg.setWindowTitle("Edit Timestamp")
        dlg.setMinimumWidth(340)
        dlg.setStyleSheet(f"""
            QDialog {{
                background: {t["bg_window"]};
                color: {t["fg_primary"]};
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }}
            QLabel {{
                color: {t["fg_secondary"]};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
                background: transparent;
                border: none;
                padding: 0;
            }}
            QDateTimeEdit {{
                background: {t["bg_input"]};
                color: {t["fg_primary"]};
                border: 1.5px solid {t["border"]};
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
                selection-background-color: {acc};
                selection-color: #FFFFFF;
            }}
            QDateTimeEdit:focus {{
                border-color: {acc};
            }}
            QDateTimeEdit::up-button, QDateTimeEdit::down-button {{
                background: {t["bg_hover"]};
                border: none;
                width: 16px;
                border-radius: 3px;
            }}
            QDialogButtonBox QPushButton {{
                background: {t["bg_button"]};
                color: {t["fg_primary"]};
                border: 1px solid {t["border"]};
                border-radius: 7px;
                padding: 6px 20px;
                font-size: 12px;
                font-weight: 500;
                min-width: 72px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background: {t["bg_hover"]};
                border-color: {acc};
            }}
            QDialogButtonBox QPushButton[text="OK"] {{
                background: {acc};
                color: #FFFFFF;
                border-color: {acc};
            }}
            QDialogButtonBox QPushButton[text="OK"]:hover {{
                background: {t["accent_hover"]};
            }}
            QFrame#sep {{
                background: {t["separator"]};
                border: none;
            }}
        """)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)

        # Header label
        hdr = QLabel("EDIT TIMESTAMP")
        hdr.setStyleSheet(f"color:{acc};font-size:10px;font-weight:700;letter-spacing:1.5px;")
        lay.addWidget(hdr)

        sep = QFrame(); sep.setObjectName("sep"); sep.setFixedHeight(1)
        lay.addWidget(sep)
        lay.addSpacing(4)

        lbl = QLabel("Date & Time")
        lay.addWidget(lbl)

        dte = QDateTimeEdit(dlg)
        dte.setDateTime(QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute))
        dte.setDisplayFormat("hh:mm AP  MMMM dd yyyy")
        dte.setCalendarPopup(True)
        lay.addWidget(dte)
        lay.addSpacing(6)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dlg)
        # Style OK button as accent
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("OK")
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        # Suppress cursor blink and disable typing while dialog is open
        self._cursor_timer.stop()
        self._cursor_blink_on = False
        self.setReadOnly(True)
        self.viewport().update()
        try:
            accepted = dlg.exec()
        finally:
            self.setReadOnly(False)
            self._cursor_blink_on = True
            self._cursor_timer.start(self._cursor_half)
            self.viewport().update()
        if accepted:
            qdt = dte.dateTime()
            new_dt = datetime.datetime(qdt.date().year(), qdt.date().month(),
                                       qdt.date().day(), qdt.time().hour(),
                                       qdt.time().minute())
            time_part = new_dt.strftime("%I:%M %p").lstrip("0")
            date_part = new_dt.strftime("%B %d %Y").replace(" 0", " ")
            new_text  = f"{time_part}  {date_part}"
            cur = QTextCursor(block)
            cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cur.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                             QTextCursor.MoveMode.KeepAnchor)
            cur.removeSelectedText()
            cur.insertText(new_text)
            block2 = cur.block()
            block2.setUserData(_TimestampData())
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(ThemeManager.current()["gutter_fg"]))
            fmt.setFontItalic(True)
            sel = QTextCursor(block2)
            sel.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            sel.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                             QTextCursor.MoveMode.KeepAnchor)
            sel.setCharFormat(fmt)

    def _handle_triple_click(self):
        """Select current line, cursor at end of that line (not next)."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)

    def mousePressEvent(self, event):
        """Alt+Click adds extra cursor. Triple-click selects line. Normal click clears."""
        from PyQt6.QtCore import QTime
        if event.button() == Qt.MouseButton.LeftButton:
            now  = QTime.currentTime()
            last = getattr(self, "_last_click_time", None)
            lpos = getattr(self, "_last_click_pos", None)
            cnt  = getattr(self, "_click_count", 0)
            pos  = event.pos()
            if (last and last.msecsTo(now) < 500 and lpos and
                    abs(pos.x()-lpos.x()) < 6 and abs(pos.y()-lpos.y()) < 6):
                cnt += 1
            else:
                cnt = 1
            self._click_count     = cnt
            self._last_click_time = now
            self._last_click_pos  = pos
            if cnt >= 3:
                self._handle_triple_click()
                self._click_count = 0
                event.accept()
                return

        if (event.button() == Qt.MouseButton.LeftButton and
                event.modifiers() & Qt.KeyboardModifier.AltModifier):
            clicked = self.cursorForPosition(event.pos())
            self._add_extra_cursor(clicked.position())
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            # Guard timestamp blocks: consume the click without moving the cursor.
            # _guard_timestamp_cursor redirects the cursor if it ever lands there.
            cursor = self.cursorForPosition(event.pos())
            block  = cursor.block()
            if block.userData() and isinstance(block.userData(), _TimestampData):
                event.accept()
                return
            # Clear extra cursors on normal click
            if self._extra_cursors:
                self._extra_cursors.clear()
                self.viewport().update()
        super().mousePressEvent(event)

    def _add_extra_cursor(self, pos: int):
        # Purge any stale non-cursor entries
        self._extra_cursors = [c for c in self._extra_cursors if hasattr(c, 'position')]
        if self.textCursor().position() == pos:
            return
        for ec in self._extra_cursors:
            if ec.position() == pos:
                return
        c = QTextCursor(self.document())
        c.setPosition(pos)
        self._extra_cursors.append(c)
        # Reset blink phase so new cursor appears immediately in sync
        self._cursor_blink_on = True
        self._cursor_timer.start(self._cursor_half)
        self.viewport().update()

    def _add_cursor_above(self):
        cursor = self.textCursor()
        block  = cursor.block().previous()
        if block.isValid():
            col = cursor.columnNumber()
            c   = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            c.movePosition(QTextCursor.MoveOperation.Right,
                           QTextCursor.MoveMode.MoveAnchor,
                           min(col, len(block.text())))
            self._add_extra_cursor(c.position())

    def _add_cursor_below(self):
        cursor = self.textCursor()
        block  = cursor.block().next()
        if block.isValid():
            col = cursor.columnNumber()
            c   = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            c.movePosition(QTextCursor.MoveOperation.Right,
                           QTextCursor.MoveMode.MoveAnchor,
                           min(col, len(block.text())))
            self._add_extra_cursor(c.position())

    def _update_cursor_overlays(self):
        """Trigger a repaint so paintEvent draws the blinking cursors."""
        existing = [s for s in self.extraSelections()
                    if not getattr(s, '_is_extra_cursor', False)]
        self.setExtraSelections(existing)
        self._cursor_blink_on = True
        self.viewport().update()

    def select_all_occurrences(self):
        """Select all occurrences of the current word/selection (Ctrl+Shift+L)."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            word = cursor.selectedText()
        else:
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText()
        if not word:
            return
        doc   = self.document()
        flags = QTextDocument.FindFlag(0)
        first = None
        cur   = QTextCursor(doc)
        cur.movePosition(QTextCursor.MoveOperation.Start)
        cursors = []
        while True:
            found = doc.find(word, cur, flags)
            if found.isNull():
                break
            cursors.append(found)
            cur = found
        if cursors:
            # Set first as main cursor, rest as extra selections
            self.setTextCursor(cursors[0])
            sels = []
            for c in cursors[1:]:
                sel = QTextEdit.ExtraSelection()
                sel.format.setBackground(QColor("#0A84FF50"))
                sel.cursor = c
                sels.append(sel)
            existing = [s for s in self.extraSelections()
                        if not getattr(s, '_is_extra_cursor', False)]
            self.setExtraSelections(existing + sels)

    # ── Word occurrence highlighting ───────────────────────────────────────

    def _highlight_word_occurrences(self):
        """When a word is selected, highlight all other occurrences subtly."""
        cursor = self.textCursor()
        # Remove old occurrence highlights
        existing = [s for s in self.extraSelections()
                    if not getattr(s, '_is_word_occurrence', False)]
        self.setExtraSelections(existing)

        if not cursor.hasSelection():
            return
        word = cursor.selectedText()
        if len(word) < 2 or '\n' in word or ' ' in word:
            return

        doc   = self.document()
        flags = QTextDocument.FindFlag(0)
        cur   = QTextCursor(doc)
        cur.movePosition(QTextCursor.MoveOperation.Start)
        sels  = []
        occ_fmt = QTextCharFormat()
        t = ThemeManager.current()
        occ_bg = QColor(t["sel_bg"]); occ_bg.setAlpha(60)
        occ_fmt.setBackground(occ_bg)

        sel_start = cursor.selectionStart()
        sel_end   = cursor.selectionEnd()

        while len(sels) < 500:   # cap at 500 to avoid lag
            found = doc.find(word, cur, flags)
            if found.isNull():
                break
            # Skip the currently selected occurrence
            if not (found.selectionStart() == sel_start and
                    found.selectionEnd()   == sel_end):
                sel = QTextEdit.ExtraSelection()
                sel.format  = occ_fmt
                sel.cursor  = found
                sel._is_word_occurrence = True
                sels.append(sel)
            cur = found

        existing = [s for s in self.extraSelections()
                    if not getattr(s, '_is_word_occurrence', False)]
        self.setExtraSelections(existing + sels)

    def paintEvent(self, event):
        """Override to draw custom cursors after Qt paints the document."""
        # Let QTextEdit paint everything normally
        super().paintEvent(event)

        # Now paint our cursors on top using the viewport
        if not self._cursor_blink_on:
            return
        col = QColor(ThemeManager.current()["cursor"])
        p   = QPainter(self.viewport())
        r   = self.cursorRect()
        p.fillRect(r.x(), r.top(), 2, r.height(), col)
        for c in self._extra_cursors:
            if hasattr(c, 'position'):
                r = self.cursorRect(c)
                p.fillRect(r.x(), r.top(), 2, r.height(), col)
        p.end()

    def createMimeDataFromSelection(self):
        """Return clipboard data with timestamp blocks stripped out."""
        mime = super().createMimeDataFromSelection()
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return mime
        # Rebuild plain text, skipping timestamp blocks entirely
        doc        = self.document()
        sel_start  = cursor.selectionStart()
        sel_end    = cursor.selectionEnd()
        parts      = []
        block      = doc.findBlock(sel_start)
        last_was_ts = False
        while block.isValid() and block.position() <= sel_end:
            if _is_timestamp_block(block) or not block.isVisible():
                last_was_ts = True
            else:
                b_start = block.position()
                c_start = max(sel_start, b_start) - b_start
                c_end   = min(sel_end, b_start + block.length() - 1) - b_start
                text    = block.text()[c_start:c_end]
                # Skip empty blocks immediately adjacent to a timestamp
                # (safety net for any remaining insertion artifacts)
                if last_was_ts and text == "":
                    pass
                else:
                    parts.append(text)
                last_was_ts = False
            block = block.next()
        from PyQt6.QtCore import QMimeData
        result = QMimeData()
        result.setText("\n".join(parts))
        return result

    def _on_cursor_blink(self):
        self._cursor_blink_on = not self._cursor_blink_on
        self.viewport().update()

    def _draw_cursors_unused(self):
        """Draw extra cursors to match the native cursor exactly."""
        if not self._extra_cursors or not self._cursor_blink_on:
            return
        # Match the native cursor color (white in dark mode, black in light)
        # Match native Qt cursor color as closely as possible
        cur_color = self.palette().color(self.palette().ColorRole.Text)
        p = QPainter(self.viewport())
        pen = QPen(cur_color)
        pen.setWidth(1)
        p.setPen(pen)
        for c in self._extra_cursors:
            if not hasattr(c, 'position'):
                continue
            r = self.cursorRect(c)
            # Draw same width as native cursor (typically 2px wide)
            p.fillRect(r.x(), r.top(), 1, r.height(), cur_color)
        p.end()

    def _move_line(self, direction: int):
        """Move the current line up (-1) or down (+1)."""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        text = cursor.selectedText()
        cursor.removeSelectedText()

        if direction == -1:
            # Move up: go to previous block end, select and remove that block's newline
            if not cursor.atStart():
                cursor.deletePreviousChar()  # remove newline above
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.insertText(text + "\n")
                # Reposition cursor on the moved line
                cursor.movePosition(QTextCursor.MoveOperation.Up)
        else:
            # Move down: remove current newline, go to end of next line, insert above
            if cursor.block().next().isValid():
                cursor.deleteChar()  # remove the newline
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                cursor.insertText("\n" + text)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _duplicate_line(self):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        text = cursor.selectedText()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertBlock()
        cursor.insertText(text)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _toggle_comment(self):
        """Insert or remove a line comment prefix based on the current language."""
        prefixes = {
            "python":     "# ",
            "javascript": "// ",
            "lua":        "-- ",
            "css":        "/* ",   # simplified
            "html":       "<!-- ", # simplified
        }
        prefix = prefixes.get(self._language, "# ")
        cursor = self.textCursor()
        doc    = self.document()

        # Operate on all selected lines, or just the current line
        if cursor.hasSelection():
            b_start = doc.findBlock(cursor.selectionStart())
            b_end   = doc.findBlock(cursor.selectionEnd())
        else:
            b_start = b_end = cursor.block()

        # Check if ALL selected lines are already commented
        block = b_start
        all_commented = True
        while block.isValid():
            if block.text().lstrip() and not block.text().lstrip().startswith(prefix.strip()):
                all_commented = False
                break
            if block == b_end:
                break
            block = block.next()

        cursor.beginEditBlock()
        block = b_start
        while True:
            c = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            text = block.text()
            if all_commented:
                # Remove comment prefix
                stripped = text.lstrip()
                spaces   = len(text) - len(stripped)
                if stripped.startswith(prefix.strip()):
                    c.movePosition(
                        QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.MoveAnchor, spaces
                    )
                    c.movePosition(
                        QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.KeepAnchor, len(prefix.strip())
                    )
                    # Remove trailing space too if present
                    sel = c.selectedText()
                    if not sel.endswith(" "):
                        pass
                    c.removeSelectedText()
                    # Remove one space after prefix if present
                    if c.block().text()[c.columnNumber():c.columnNumber()+1] == " ":
                        c.deleteChar()
            else:
                c.insertText(prefix)
            if block == b_end:
                break
            block = block.next()
        cursor.endEditBlock()

    def _smart_home(self, mods):
        """First press -> first non-whitespace; second press -> column 0."""
        cursor  = self.textCursor()
        text    = cursor.block().text()
        col     = cursor.columnNumber()
        first_non_ws = len(text) - len(text.lstrip())

        keep = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        mode = (QTextCursor.MoveMode.KeepAnchor if keep
                else QTextCursor.MoveMode.MoveAnchor)

        if col != first_non_ws:
            # Move to first non-whitespace
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, mode)
            cursor.movePosition(
                QTextCursor.MoveOperation.Right, mode, first_non_ws
            )
        else:
            # Already there - go to absolute start
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, mode)
        self.setTextCursor(cursor)

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
        """Smooth scrolling: 3 lines per scroll notch. Ctrl+wheel: low-sensitivity zoom."""
        ctrl  = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        delta = event.angleDelta().y()
        if ctrl and delta != 0:
            # Require 3 full notches (360°) per zoom step — much less sensitive than Ctrl+=
            self._zoom_accum = getattr(self, '_zoom_accum', 0) + delta
            if abs(self._zoom_accum) >= 360:
                self.zoom_step.emit(1 if self._zoom_accum > 0 else -1)
                self._zoom_accum = 0
            event.accept()
        elif delta != 0:
            sb        = self.verticalScrollBar()
            line_h    = self.fontMetrics().height()
            scroll_by = int(-delta / 120 * 3 * line_h)
            sb.setValue(sb.value() + scroll_by)
            event.accept()
        else:
            super().wheelEvent(event)

    # -- Slots ---------------------------------------------------------------

    def _on_contents_changed(self):
        self.update_line_number_area_width()
        self._line_num_area.update()
        # Auto-detect language for untitled files while typing
        if not self._file_path and self._language == "plain":
            from PyQt6.QtCore import QTimer as _QT
            if self._sniff_timer is None:
                self._sniff_timer = _QT(self)
                self._sniff_timer.setSingleShot(True)
                self._sniff_timer.timeout.connect(self._auto_sniff)
            self._sniff_timer.start(800)  # 800ms debounce

    def _auto_sniff(self):
        """Sniff language from content and switch to code mode if detected."""
        content = self.toPlainText()
        if not content.strip():
            return
        lang = _sniff_language(content)
        if lang != "plain" and lang != self._language:
            self._language = lang
            if self._mode == "rich":
                self.set_mode("code")
            else:
                self._highlighter.set_language(lang)

    def _on_block_count_changed(self, _=None):
        self.update_line_number_area_width()
        self._line_num_area.update()

    def _on_scroll(self, _=None):
        self._line_num_area.update()

    def _on_cursor_changed(self):
        self._highlight_current_line()
        self._line_num_area.update()
        self.cursor_format_changed.emit()
        # Push cursor off timestamp blocks
        self._guard_timestamp_cursor()
        # Don't touch char formats while a selection is active — setCurrentCharFormat
        # applies to selected text and would corrupt timestamp or document styling.
        if self.textCursor().hasSelection():
            return
        # Only clear format bleed from timestamp blocks (grey color).
        # NEVER clear italic/bold — those are intentional user formatting.
        if not _is_timestamp_block(self.textCursor().block()):
            fmt = self.currentCharFormat()
            if fmt.foreground().color() == QColor("#6B7280"):
                # Timestamp grey bled into a normal line — reset color only
                clean = QTextCharFormat(fmt)
                clean.clearForeground()
                self.setCurrentCharFormat(clean)
                return
        # Ensure rich font family is always set on the insertion format.
        # Preserve bold/italic/underline/size — only inject the family if missing.
        if self._mode == "rich" and hasattr(self, "_rich_font_family"):
            cur_fmt = self.currentCharFormat()
            fams = cur_fmt.fontFamilies()
            needs_family = not fams or fams[0] != self._rich_font_family
            needs_size   = not cur_fmt.fontPointSize()
            if needs_family or needs_size:
                rfmt = QTextCharFormat(cur_fmt)
                if needs_family:
                    rfmt.setFontFamilies([self._rich_font_family])
                if needs_size:
                    # Use current document default size so zoom is respected
                    doc_size = self.document().defaultFont().pointSize()
                    rfmt.setFontPointSize(float(doc_size if doc_size > 0 else self._rich_font_size))
                self.setCurrentCharFormat(rfmt)

    def _guard_timestamp_cursor(self):
        """
        If the cursor lands on a timestamp block, redirect it away.
        Never modifies the document — only moves the cursor.
        Prefer the block after the timestamp; fall back to the block before it.
        """
        cursor = self.textCursor()
        # Don't redirect during an active selection — let the user drag freely
        if cursor.hasSelection():
            return
        block  = cursor.block()
        if not _is_timestamp_block(block):
            return
        next_b = block.next()
        if next_b.isValid():
            target = QTextCursor(next_b)
            target.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        else:
            prev_b = block.previous()
            if not prev_b.isValid():
                return   # timestamp is the only block; can't move
            target = QTextCursor(prev_b)
            target.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        plain_fmt = QTextCharFormat()
        plain_fmt.setFontItalic(False)
        plain_fmt.setFontWeight(400)
        self.cursorPositionChanged.disconnect(self._on_cursor_changed)
        self.setTextCursor(target)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.setCurrentCharFormat(plain_fmt)

    # -- Utilities -----------------------------------------------------------

    def cursor_position(self) -> tuple[int, int]:
        c = self.textCursor()
        return c.blockNumber() + 1, c.columnNumber() + 1
