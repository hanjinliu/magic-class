from __future__ import annotations

import pytest
from qtpy import QtGui
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from magicclass.widgets.codeedit import QCodeEditor

Ctrl = Qt.KeyboardModifier.ControlModifier
Shift = Qt.KeyboardModifier.ShiftModifier
Alt = Qt.KeyboardModifier.AltModifier

SRC = "a = 1\nif a:\n    b = 2\n\n    # c\nd = 4"


def _make(qtbot: QtBot, text: str, start: int, end: int | None = None):
    edit = QCodeEditor()
    qtbot.addWidget(edit)
    edit.setPlainText(text)
    cursor = edit.textCursor()
    cursor.setPosition(start)
    if end is not None:
        cursor.setPosition(end, QtGui.QTextCursor.MoveMode.KeepAnchor)
    edit.setTextCursor(cursor)
    return edit


def _undo_all(edit: QCodeEditor) -> int:
    n = 0
    while edit.document().isUndoAvailable():
        edit.undo()
        n += 1
    return n


def _selection(edit: QCodeEditor) -> tuple[int, int]:
    cursor = edit.textCursor()
    return cursor.anchor(), cursor.position()


@pytest.mark.parametrize(
    "start, end, expected",
    [
        # empty lines are skipped
        (0, len(SRC), "# a = 1\n# if a:\n#     b = 2\n\n#     # c\n# d = 4"),
        (len(SRC), 0, "# a = 1\n# if a:\n#     b = 2\n\n#     # c\n# d = 4"),
        # partially selected lines
        (2, 16, "# a = 1\n# if a:\n#     b = 2\n\n    # c\nd = 4"),
        # line at the end of selection is not included if nothing is selected
        (0, 12, "# a = 1\n# if a:\n    b = 2\n\n    # c\nd = 4"),
        # "#" is inserted at the indent level, and already-commented lines are
        # commented again unless all the lines are commented.
        (12, 28, "a = 1\nif a:\n    # b = 2\n\n    # # c\nd = 4"),
        # no selection
        (14, None, "a = 1\nif a:\n    # b = 2\n\n    # c\nd = 4"),
    ],
)
def test_toggle_comment(qtbot: QtBot, start, end, expected):
    edit = _make(qtbot, SRC, start, end)
    qtbot.keyClick(edit, Qt.Key.Key_Slash, Ctrl)
    assert edit.toPlainText() == expected
    qtbot.keyClick(edit, Qt.Key.Key_Slash, Ctrl)
    assert edit.toPlainText() == SRC
    # each operation is a single undo step
    assert _undo_all(edit) == 2
    assert edit.toPlainText() == SRC


def test_uncomment(qtbot: QtBot):
    edit = _make(qtbot, "#a\n    # b\n    #  c", 0, 19)
    qtbot.keyClick(edit, Qt.Key.Key_Slash, Ctrl)
    assert edit.toPlainText() == "a\n    b\n     c"


def test_indent(qtbot: QtBot):
    edit = _make(qtbot, SRC, 0, len(SRC))
    qtbot.keyClick(edit, Qt.Key.Key_Tab)
    assert (
        edit.toPlainText()
        == "    a = 1\n    if a:\n        b = 2\n\n        # c\n    d = 4"
    )
    qtbot.keyClick(edit, Qt.Key.Key_Backtab, Shift)
    assert edit.toPlainText() == SRC
    assert _undo_all(edit) == 2

    # partial indents
    edit = _make(qtbot, "  x\n   y\n     z", 0, 8)
    qtbot.keyClick(edit, Qt.Key.Key_Backtab, Shift)
    assert edit.toPlainText() == "x\ny\n     z"
    edit = _make(qtbot, "     z", 6)
    qtbot.keyClick(edit, Qt.Key.Key_Backtab, Shift)
    assert edit.toPlainText() == " z"


@pytest.mark.parametrize(
    "text, expected",
    [("", "    "), ("ab", "ab  "), ("a b c", "a b c   "), ("abcd", "abcd    ")],
)
def test_tab(qtbot: QtBot, text: str, expected: str):
    edit = _make(qtbot, text, len(text))
    qtbot.keyClick(edit, Qt.Key.Key_Tab)
    assert edit.toPlainText() == expected


def test_backspace(qtbot: QtBot):
    edit = _make(qtbot, "        x", 8)
    qtbot.keyClick(edit, Qt.Key.Key_Backspace)
    assert edit.toPlainText() == "    x"
    edit = _make(qtbot, "      x", 6)
    qtbot.keyClick(edit, Qt.Key.Key_Backspace)
    assert edit.toPlainText() == "    x"
    assert _undo_all(edit) == 1
    # not in the indent
    edit = _make(qtbot, "x =     1", 8)
    qtbot.keyClick(edit, Qt.Key.Key_Backspace)
    assert edit.toPlainText() == "x =    1"


@pytest.mark.parametrize(
    "key, mod",
    [
        (Qt.Key.Key_Slash, Ctrl),
        (Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier),
        (Qt.Key.Key_Backtab, Shift),
        (Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier),
        (Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier),
        (Qt.Key.Key_ParenLeft, Qt.KeyboardModifier.NoModifier),
        (Qt.Key.Key_QuoteDbl, Qt.KeyboardModifier.NoModifier),
        (Qt.Key.Key_Up, Alt),
        (Qt.Key.Key_V, Ctrl),
    ],
)
def test_read_only(qtbot: QtBot, key, mod):
    QApplication.clipboard().setText("xyz")
    for start, end in [(0, len(SRC)), (len(SRC), None)]:
        edit = _make(qtbot, SRC, start, end)
        edit.setReadOnly(True)
        qtbot.keyClick(edit, key, mod)
        assert edit.toPlainText() == SRC


@pytest.mark.parametrize(
    "typed, expected",
    [
        ('x = "abc"', 'x = "abc"'),
        ("f(a[0])", "f(a[0])"),
        ("f(a[0", "f(a[0])"),
        ("it's", "it's"),
        ("x = f'a", "x = f'a'"),
        ('f("a", {"b": 1})', 'f("a", {"b": 1})'),
        ("(a + (b)", "(a + (b))"),
        ('"""', '"""'),
    ],
)
def test_auto_close(qtbot: QtBot, typed: str, expected: str):
    edit = _make(qtbot, "", 0)
    qtbot.keyClicks(edit, typed)
    assert edit.toPlainText() == expected


def test_closing_bracket_not_skipped(qtbot: QtBot):
    edit = _make(qtbot, "(a + (b)", 7)
    qtbot.keyClick(edit, Qt.Key.Key_ParenRight)
    assert edit.toPlainText() == "(a + (b))"
    assert _selection(edit) == (8, 8)


def test_wrap_selection(qtbot: QtBot):
    edit = _make(qtbot, "abc", 0, 3)
    qtbot.keyClick(edit, Qt.Key.Key_ParenLeft)
    assert edit.toPlainText() == "(abc)"
    assert edit.textCursor().selectedText() == "abc"
    qtbot.keyClick(edit, Qt.Key.Key_QuoteDbl)
    assert edit.toPlainText() == '("abc")'
    assert _undo_all(edit) == 2
    # typing a closing bracket replaces the selection
    edit = _make(qtbot, "abc", 0, 3)
    qtbot.keyClick(edit, Qt.Key.Key_ParenRight)
    assert edit.toPlainText() == ")"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("if a:", "if a:\n    "),
        ("if a:  ", "if a:\n    "),
        ("    x = 1", "    x = 1\n    "),
        ("    return f(", "    return f(\n        "),
        ("    return 1", "    return 1\n"),
        ("        pass", "        pass\n    "),
        ("x = [1,", "x = [1,\n    "),
        ("# note:", "# note:\n"),
    ],
)
def test_new_line(qtbot: QtBot, text: str, expected: str):
    edit = _make(qtbot, text, len(text))
    qtbot.keyClick(edit, Qt.Key.Key_Return)
    assert edit.toPlainText() == expected
    assert _undo_all(edit) == 1


def test_new_line_with_selection(qtbot: QtBot):
    edit = _make(qtbot, "    abc = 1", 7, 11)
    qtbot.keyClick(edit, Qt.Key.Key_Return)
    assert edit.toPlainText() == "    abc\n    "


@pytest.mark.parametrize(
    "start, end, key, expected, selection",
    [
        (4, None, Qt.Key.Key_Up, "l1\nl0\nl2\nl3", (1, 1)),
        (10, None, Qt.Key.Key_Up, "l0\nl1\nl3\nl2", (7, 7)),
        (4, 7, Qt.Key.Key_Up, "l1\nl2\nl0\nl3", (1, 4)),
        (7, 4, Qt.Key.Key_Up, "l1\nl2\nl0\nl3", (4, 1)),
        (1, None, Qt.Key.Key_Up, "l0\nl1\nl2\nl3", (1, 1)),
        (4, None, Qt.Key.Key_Down, "l0\nl2\nl1\nl3", (7, 7)),
        (7, None, Qt.Key.Key_Down, "l0\nl1\nl3\nl2", (10, 10)),
        (1, 4, Qt.Key.Key_Down, "l2\nl0\nl1\nl3", (4, 7)),
        (0, None, Qt.Key.Key_Down, "l1\nl0\nl2\nl3", (3, 3)),
        (10, None, Qt.Key.Key_Down, "l0\nl1\nl2\nl3", (10, 10)),
        # full-line selection (l1 and l2)
        (3, 9, Qt.Key.Key_Down, "l0\nl3\nl1\nl2", (6, 11)),
        (3, 9, Qt.Key.Key_Up, "l1\nl2\nl0\nl3", (0, 6)),
    ],
)
def test_move_lines(qtbot: QtBot, start, end, key, expected, selection):
    src = "l0\nl1\nl2\nl3"
    edit = _make(qtbot, src, start, end)
    qtbot.keyClick(edit, key, Alt)
    assert edit.toPlainText() == expected
    assert _selection(edit) == selection
    if expected != src:
        assert _undo_all(edit) == 1
        assert edit.toPlainText() == src


def test_paste(qtbot: QtBot):
    QApplication.clipboard().setText("\tx\n\ty")
    edit = _make(qtbot, "ab", 0, 2)
    qtbot.keyClick(edit, Qt.Key.Key_V, Ctrl)
    assert edit.toPlainText() == "    x\n    y"
    edit = _make(qtbot, "ab", 0, 2)
    edit.paste()
    assert edit.toPlainText() == "    x\n    y"


def test_select_word(qtbot: QtBot):
    edit = _make(qtbot, "foo bar baz", 5)
    qtbot.keyClick(edit, Qt.Key.Key_D, Ctrl)
    assert edit.textCursor().selectedText() == "bar"
