# ui/bookmarks.py -- NovaPad Bookmark System
#
# Bookmarks are stored per-document as a set of block numbers.
# The gutter in CodeEditor paints a small filled circle for bookmarked lines.
# Ctrl+F2 toggles a bookmark on the current line.
# F2 / Shift+F2 navigate to the next / previous bookmark.
#
# BookmarkManager is a standalone object kept on MainWindow.

from __future__ import annotations
from PyQt6.QtGui import QTextCursor


class BookmarkManager:
    """
    Manages bookmarks across all open editors.
    Bookmarks are stored as {editor_id: set_of_block_numbers}.
    """

    def __init__(self):
        # Maps id(editor) → set of block numbers (int)
        self._marks: dict[int, set[int]] = {}

    # -- Core API ------------------------------------------------------------

    def toggle(self, editor) -> bool:
        """Toggle bookmark on the cursor's current line. Returns new state."""
        key   = id(editor)
        line  = editor.textCursor().blockNumber()
        marks = self._marks.setdefault(key, set())
        if line in marks:
            marks.discard(line)
            editor._line_num_area.update()
            return False
        else:
            marks.add(line)
            editor._line_num_area.update()
            return True

    def has_bookmark(self, editor, block_number: int) -> bool:
        return block_number in self._marks.get(id(editor), set())

    def bookmarks_for(self, editor) -> set[int]:
        return set(self._marks.get(id(editor), set()))

    def clear(self, editor):
        self._marks.pop(id(editor), None)
        editor._line_num_area.update()

    def remove_editor(self, editor):
        self._marks.pop(id(editor), None)

    # -- Navigation ----------------------------------------------------------

    def goto_next(self, editor):
        """Jump cursor to the next bookmark after the current line."""
        marks = sorted(self._marks.get(id(editor), set()))
        if not marks:
            return
        cur = editor.textCursor().blockNumber()
        # Find first mark strictly after current line, wrapping around
        after = [m for m in marks if m > cur]
        target = after[0] if after else marks[0]
        self._jump(editor, target)

    def goto_prev(self, editor):
        """Jump cursor to the previous bookmark before the current line."""
        marks = sorted(self._marks.get(id(editor), set()))
        if not marks:
            return
        cur    = editor.textCursor().blockNumber()
        before = [m for m in marks if m < cur]
        target = before[-1] if before else marks[-1]
        self._jump(editor, target)

    @staticmethod
    def _jump(editor, block_number: int):
        doc    = editor.document()
        block  = doc.findBlockByNumber(block_number)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()

    # -- Serialisation (for session) ----------------------------------------

    def serialise(self, editor) -> list[int]:
        return sorted(self._marks.get(id(editor), set()))

    def deserialise(self, editor, line_numbers: list[int]):
        self._marks[id(editor)] = set(line_numbers)
        editor._line_num_area.update()
