"""
core/highlighter.py  –  NovaPad Syntax Highlighter
====================================================
A production-quality QSyntaxHighlighter subclass modelled after VS Code's
colour scheme.  Uses a carefully ordered rule pipeline plus a block-state
machine so that multi-line strings and block comments are handled correctly.

Supported languages
-------------------
  python · javascript / typescript · json · html / xml · css · plain (none)

Design principles
-----------------
* Rules are applied in reverse-priority order (last wins), so the pipeline
  stays readable while more-specific rules override general ones.
* Multi-line constructs (triple-quoted strings, /* */ comments) are tracked
  with QSyntaxHighlighter's block-state integer.
* The highlighter holds NO reference back to the editor widget — it only
  knows about the QTextDocument.
* Dark/Light token palettes are swappable without rebuilding rules.
"""

from __future__ import annotations

import re
from enum import IntEnum, auto

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import (
    QColor, QFont, QSyntaxHighlighter,
    QTextCharFormat, QTextDocument,
)


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK STATES  (multi-line tracking)
# ─────────────────────────────────────────────────────────────────────────────

class State(IntEnum):
    NORMAL          = 0
    ML_DSTRING      = 1   # inside """..."""  (Python)
    ML_SSTRING      = 2   # inside '''...'''  (Python)
    ML_COMMENT      = 3   # inside /* ... */  (JS / CSS)
    ML_HTML_COMMENT = 4   # inside <!-- ... -->


# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTES  (VS Code Dark+ / Light+)
# ─────────────────────────────────────────────────────────────────────────────

DARK_PALETTE = {
    "keyword":    "#569CD6",   # blue
    "keyword2":   "#C586C0",   # pink (import/from/as/in/not/and/or)
    "builtin":    "#4EC9B0",   # teal
    "func_def":   "#DCDCAA",   # yellow
    "class_def":  "#4EC9B0",   # teal
    "decorator":  "#C586C0",   # pink
    "string":     "#CE9178",   # orange-brown
    "string_esc": "#D7BA7D",   # gold  (escape sequences)
    "comment":    "#6A9955",   # green
    "number":     "#B5CEA8",   # pale green
    "operator":   "#D4D4D4",   # white-grey
    "self_cls":   "#9CDCFE",   # light blue
    "tag":        "#4EC9B0",   # teal (HTML tags)
    "attr":       "#9CDCFE",   # light blue (HTML attrs)
    "at_rule":    "#C586C0",   # pink (@media, @import …)
    "property":   "#9CDCFE",   # CSS property names
    "selector":   "#D7BA7D",   # CSS selectors
    "json_key":   "#9CDCFE",   # JSON keys
    "constant":   "#569CD6",   # True/False/None
    "type_hint":  "#4EC9B0",
}

LIGHT_PALETTE = {
    "keyword":    "#0000FF",
    "keyword2":   "#AF00DB",
    "builtin":    "#267F99",
    "func_def":   "#795E26",
    "class_def":  "#267F99",
    "decorator":  "#AF00DB",
    "string":     "#A31515",
    "string_esc": "#EE0000",
    "comment":    "#008000",
    "number":     "#098658",
    "operator":   "#000000",
    "self_cls":   "#001080",
    "tag":        "#800000",
    "attr":       "#FF0000",
    "at_rule":    "#AF00DB",
    "property":   "#FF0000",
    "selector":   "#800000",
    "json_key":   "#0451A5",
    "constant":   "#0000FF",
    "type_hint":  "#267F99",
}


# ─────────────────────────────────────────────────────────────────────────────
# FORMAT FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


# ─────────────────────────────────────────────────────────────────────────────
# MAIN HIGHLIGHTER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class NovaPadHighlighter(QSyntaxHighlighter):
    """
    VS Code–style syntax highlighter for NovaPad.

    Usage
    -----
        h = NovaPadHighlighter(editor.document())
        h.set_language("python")
        h.set_dark_mode(True)
    """

    def __init__(self, document: QTextDocument, language: str = "plain",
                 dark: bool = True):
        super().__init__(document)
        self._language = language.lower()
        self._dark     = dark
        self._palette  = DARK_PALETTE if dark else LIGHT_PALETTE
        # Compiled rules: list of (QRegularExpression, token_key, group)
        self._rules:       list[tuple[QRegularExpression, str, int]] = []
        # Multi-line state data
        self._ml_open:     QRegularExpression | None = None
        self._ml_close:    QRegularExpression | None = None
        self._ml_state:    int = State.NORMAL
        self._ml_fmt_key:  str = "comment"

        self._rebuild()

    # ── Public API ────────────────────────────────────────────────────────

    def set_language(self, language: str):
        new_lang = language.lower()
        if new_lang != self._language:
            self._language = new_lang
            self._rebuild()
            self.rehighlight()

    def force_rehighlight(self):
        """Force a full rehighlight pass (e.g. after mode switch)."""
        self._rebuild()
        self.rehighlight()

    def set_dark_mode(self, dark: bool):
        if dark != self._dark:
            self._dark    = dark
            self._palette = DARK_PALETTE if dark else LIGHT_PALETTE
            self._rebuild()
            self.rehighlight()

    # ── Rule building ─────────────────────────────────────────────────────

    def _re(self, pattern: str) -> QRegularExpression:
        return QRegularExpression(pattern)

    def _rebuild(self):
        """Compile all rules for the current language."""
        self._rules       = []
        self._ml_open     = None
        self._ml_close    = None
        self._ml_state    = State.NORMAL
        self._ml_fmt_key  = "comment"

        lang = self._language
        if lang == "python":
            self._build_python()
        elif lang in ("javascript", "js", "typescript", "ts"):
            self._build_javascript()
        elif lang == "json":
            self._build_json()
        elif lang in ("html", "xml"):
            self._build_html()
        elif lang == "css":
            self._build_css()
        elif lang == "lua":
            self._build_lua()
        # plain → no rules

    def _add(self, pattern: str, token: str, group: int = 0):
        """Append a single-line rule."""
        self._rules.append((self._re(pattern), token, group))

    # ── Python rules ──────────────────────────────────────────────────────

    def _build_python(self):
        # Numbers (must come before operators)
        self._add(r'\b0[xX][0-9A-Fa-f]+\b',     "number")
        self._add(r'\b0[bB][01]+\b',              "number")
        self._add(r'\b\d+\.?\d*([eE][+-]?\d+)?\b',"number")

        # Strings (single-line only; triple-quoted handled by state machine)
        self._add(r'"(?:[^"\\]|\\.)*"',           "string")
        self._add(r"'(?:[^'\\]|\\.)*'",           "string")
        # f-strings
        self._add(r'f"(?:[^"\\]|\\.)*"',          "string")
        self._add(r"f'(?:[^'\\]|\\.)*'",          "string")

        # Escape sequences inside strings (applied over string colour)
        self._add(r'\\[\\\'\"abfnrtvx0-9uUN{}]', "string_esc")

        # Decorators
        self._add(r'@\w+',                        "decorator")

        # Type hints after :  or ->
        self._add(r'(?<=:\s)\b\w+\b',             "type_hint")
        self._add(r'(?<=->\s)\b\w+\b',            "type_hint")

        # Keywords (secondary – control-flow, logic)
        kw2 = r'\b(?:import|from|as|in|not|and|or|is|lambda|with|yield|global|nonlocal|del)\b'
        self._add(kw2,                            "keyword2")

        # Keywords (primary)
        kw = (r'\b(?:False|None|True|async|await|break|class|continue|def|elif|else|'
              r'except|finally|for|if|pass|raise|return|try|while)\b')
        self._add(kw,                             "keyword", 0)

        # Built-ins
        builtins = (r'\b(?:abs|all|any|bin|bool|callable|chr|dict|dir|divmod|enumerate|'
                    r'eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|'
                    r'hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|'
                    r'locals|map|max|memoryview|min|next|object|oct|open|ord|pow|print|'
                    r'property|range|repr|reversed|round|set|setattr|slice|sorted|'
                    r'staticmethod|str|sum|super|tuple|type|vars|zip)\b')
        self._add(builtins,                       "builtin")

        # self / cls
        self._add(r'\b(?:self|cls)\b',            "self_cls")

        # Function name after 'def'
        self._add(r'\bdef\s+(\w+)',               "func_def", 1)

        # Class name after 'class'
        self._add(r'\bclass\s+(\w+)',             "class_def", 1)

        # Single-line comment
        self._add(r'#[^\n]*',                     "comment")

        # ── Multi-line: triple double-quoted strings ───────────────────
        self._ml_open    = self._re(r'"""')
        self._ml_close   = self._re(r'"""')
        self._ml_state   = State.ML_DSTRING
        self._ml_fmt_key = "string"

    # ── JavaScript / TypeScript rules ─────────────────────────────────────

    def _build_javascript(self):
        self._add(r'\b0[xX][0-9A-Fa-f]+\b',       "number")
        self._add(r'\b\d+\.?\d*([eE][+-]?\d+)?\b', "number")

        # Template literals
        self._add(r'`(?:[^`\\]|\\.)*`',            "string")
        # Regular strings
        self._add(r'"(?:[^"\\]|\\.)*"',            "string")
        self._add(r"'(?:[^'\\]|\\.)*'",            "string")

        # JSX / HTML in JS (basic)
        self._add(r'</?\w[\w.:-]*',                "tag")

        # Keywords 2
        kw2 = (r'\b(?:import|export|from|as|in|instanceof|of|typeof|void|'
               r'delete|new|this|super|return|yield|await|async)\b')
        self._add(kw2,                             "keyword2")

        # Keywords 1
        kw = (r'\b(?:break|case|catch|class|const|continue|debugger|default|do|else|'
               r'extends|finally|for|function|if|let|null|static|switch|throw|'
               r'true|false|try|undefined|var|while|with)\b')
        self._add(kw,                              "keyword")

        # Built-ins / globals
        self._add(r'\b(?:console|Math|JSON|Object|Array|String|Number|Boolean|'
                  r'Promise|Error|Symbol|Map|Set|WeakMap|WeakSet|Date|RegExp|'
                  r'parseInt|parseFloat|isNaN|isFinite|encodeURI|decodeURI)\b',
                  "builtin")

        # Function declarations
        self._add(r'\bfunction\s+(\w+)',           "func_def", 1)
        # Arrow / const function patterns
        self._add(r'\bconst\s+(\w+)\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>',
                  "func_def", 1)

        # Regex literals (simplified, avoids division ambiguity)
        self._add(r'/(?![/*])(?:[^/\\\n]|\\.)+/[gimsuy]*', "string")

        # Single-line comment
        self._add(r'//[^\n]*',                     "comment")

        # Multi-line comment
        self._ml_open    = self._re(r'/\*')
        self._ml_close   = self._re(r'\*/')
        self._ml_state   = State.ML_COMMENT
        self._ml_fmt_key = "comment"

    # ── JSON rules ────────────────────────────────────────────────────────

    def _build_json(self):
        # JSON keys (must precede generic string rule)
        self._add(r'"(?:[^"\\]|\\.)*"\s*(?=:)',   "json_key")
        # String values
        self._add(r'"(?:[^"\\]|\\.)*"',            "string")
        # Numbers
        self._add(r'-?\b\d+\.?\d*([eE][+-]?\d+)?\b', "number")
        # Constants
        self._add(r'\b(?:true|false|null)\b',      "constant")

    # ── HTML / XML rules ──────────────────────────────────────────────────

    def _build_html(self):
        # Attribute values
        self._add(r'"[^"]*"',                      "string")
        self._add(r"'[^']*'",                      "string")

        # DOCTYPE
        self._add(r'<!DOCTYPE[^>]*>',              "keyword")

        # Tag names
        self._add(r'</?(\w[\w:-]*)',               "tag", 1)
        self._add(r'<\?(\w+)',                     "tag", 1)   # <?xml

        # Attribute names
        self._add(r'\b([\w:-]+)\s*=',              "attr", 1)

        # &entities;
        self._add(r'&\w+;',                        "keyword2")

        # Multi-line: HTML comment <!-- ... -->
        self._ml_open    = self._re(r'<!--')
        self._ml_close   = self._re(r'-->')
        self._ml_state   = State.ML_HTML_COMMENT
        self._ml_fmt_key = "comment"

    # ── CSS rules ─────────────────────────────────────────────────────────

    def _build_css(self):
        # String values
        self._add(r'"[^"]*"',                      "string")
        self._add(r"'[^']*'",                      "string")

        # Numbers with units
        self._add(r'-?\b\d+\.?\d*(?:px|em|rem|%|vh|vw|vmin|vmax|pt|cm|mm|s|ms|deg|fr)?\b',
                  "number")

        # At-rules
        self._add(r'@[\w-]+',                      "at_rule")

        # Pseudo-classes/elements
        self._add(r'::?[\w-]+',                    "keyword2")

        # Selectors (simplified: .class #id element)
        self._add(r'(?:^|[\s{,>+~])([.#]?[\w-]+)(?=\s*[{,])',
                  "selector", 1)

        # Property names (before the colon)
        self._add(r'[\w-]+(?=\s*:)',               "property")

        # Hex colours
        self._add(r'#[0-9A-Fa-f]{3,8}\b',         "number")

        # CSS functions
        self._add(r'(?:rgb|rgba|hsl|hsla|var|calc|linear-gradient|radial-gradient)'
                  r'\s*\(',                        "builtin")

        # Single-line comment
        self._add(r'//[^\n]*',                     "comment")

        # Multi-line comment
        self._ml_open    = self._re(r'/\*')
        self._ml_close   = self._re(r'\*/')
        self._ml_state   = State.ML_COMMENT
        self._ml_fmt_key = "comment"

    # ── Lua rules ─────────────────────────────────────────────────────────

    def _build_lua(self):
        # Numbers
        self._add(r'\b0[xX][0-9A-Fa-f]+\b',          "number")
        self._add(r'\b\d+\.?\d*([eE][+-]?\d+)?\b', "number")

        # Strings
        self._add(r'"(?:[^"\\]|\\.)*"',               "string")
        self._add(r"'(?:[^'\\]|\\.)*'",               "string")
        # Long strings [[ ... ]]
        self._add(r'\[\[.*?\]\]',                     "string")

        # Keywords
        kw = (r'\b(?:and|break|do|else|elseif|end|false|for|function|goto|'
              r'if|in|local|nil|not|or|repeat|return|then|true|until|while)\b')
        self._add(kw, "keyword", 0)

        # Built-in globals
        builtins = (r'\b(?:assert|collectgarbage|dofile|error|getmetatable|'
                    r'ipairs|load|loadfile|next|pairs|pcall|print|rawequal|'
                    r'rawget|rawlen|rawset|require|select|setmetatable|'
                    r'tonumber|tostring|type|xpcall|'
                    r'string|table|math|io|os|package|coroutine|utf8)\b')
        self._add(builtins, "builtin")

        # self equivalent
        self._add(r'\bself\b', "self_cls")

        # Function definition name
        self._add(r'\bfunction\s+([\w.:]+)', "func_def", 1)
        self._add(r'\blocal\s+function\s+(\w+)', "func_def", 1)

        # Single-line comment (--)
        self._add(r'--(?!\[\[)[^\n]*', "comment")

        # Multi-line comment --[[ ... ]]
        self._ml_open    = self._re(r'--\[\[')
        self._ml_close   = self._re(r'\]\]')
        self._ml_state   = State.ML_COMMENT
        self._ml_fmt_key = "comment"

    # ── Core: highlightBlock ──────────────────────────────────────────────

    def highlightBlock(self, text: str):
        """Called by Qt for every visible block.  Order matters."""

        # ── 1. Multi-line continuation from previous block ────────────
        prev_state = self.previousBlockState()

        if prev_state == self._ml_state and self._ml_close:
            # We're inside an unclosed multi-line construct
            end_match = self._ml_close.match(text)
            if end_match.hasMatch():
                length = end_match.capturedStart() + end_match.capturedLength()
                self.setFormat(0, length, _fmt(self._palette[self._ml_fmt_key], italic=True))
                self.setCurrentBlockState(State.NORMAL)
                start_offset = length
            else:
                # Entire block is still inside the construct
                self.setFormat(0, len(text), _fmt(self._palette[self._ml_fmt_key], italic=True))
                self.setCurrentBlockState(self._ml_state)
                return
        else:
            self.setCurrentBlockState(State.NORMAL)
            start_offset = 0

        # ── 2. Apply single-line rules (from start_offset onwards) ───
        for regex, token, group in self._rules:
            it = regex.globalMatch(text, start_offset)
            while it.hasNext():
                m = it.next()
                pos = m.capturedStart(group)
                length = m.capturedLength(group)
                if pos >= 0 and length > 0:
                    fmt = self._make_fmt(token)
                    self.setFormat(pos, length, fmt)

        # ── 3. Detect opening of a multi-line construct ───────────────
        if self._ml_open:
            idx = start_offset
            while True:
                open_match = self._ml_open.match(text, idx)
                if not open_match.hasMatch():
                    break

                open_start = open_match.capturedStart()

                # Is this position already coloured as a string/comment?
                # (i.e. the opening token is *inside* a line comment)
                # We skip that check here for simplicity; the ordering of
                # rules already handles most cases.

                close_match = self._ml_close.match(
                    text, open_start + open_match.capturedLength()
                )

                if close_match.hasMatch():
                    # Opened and closed on the same line
                    close_end = close_match.capturedStart() + close_match.capturedLength()
                    span = close_end - open_start
                    self.setFormat(open_start, span,
                                   _fmt(self._palette[self._ml_fmt_key], italic=True))
                    idx = close_end
                else:
                    # Opened but not closed – spans to end of block
                    span = len(text) - open_start
                    self.setFormat(open_start, span,
                                   _fmt(self._palette[self._ml_fmt_key], italic=True))
                    self.setCurrentBlockState(self._ml_state)
                    break

    def _make_fmt(self, token: str) -> QTextCharFormat:
        """Return a QTextCharFormat for the given token type."""
        color   = self._palette.get(token, "#D4D4D4")
        bold    = token in ("keyword", "keyword2", "func_def", "class_def")
        italic  = token in ("comment", "decorator")
        return _fmt(color, bold=bold, italic=italic)
