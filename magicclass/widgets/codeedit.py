from __future__ import annotations
from contextlib import contextmanager
import inspect
from typing import Any, Iterator, NamedTuple, TYPE_CHECKING
import weakref
from collections import Counter
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal as pyqtSignal

from psygnal import Signal
from magicgui.backends._qtpy.widgets import TextEdit as QBaseTextEdit, QBaseStringWidget
from magicgui.widgets import TextEdit, EmptyWidget, FileEdit
from magicgui.application import use_app
from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined

from macrokit import parse, Symbol, Expr, Head
from magicclass._gui.utils import show_dialog_from_mgui
from magicclass.signature import split_annotated_type, is_annotated
from magicclass.widgets._const import FONT

if TYPE_CHECKING:
    from magicclass import MagicTemplate

_TAB = " " * 4
_PAIRS = {"(": ")", "[": "]", "{": "}"}


class QLineNumberArea(QtW.QWidget):
    def __init__(self, editor: QCodeEditor):
        super().__init__(editor)
        self.editor = editor
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.editor._show_context_menu)

    def sizeHint(self):
        return QtCore.QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event: QtGui.QPaintEvent):
        self.editor.lineNumberAreaPaintEvent(event)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        editor = self.editor
        y = a0.pos().y()

        num, block = editor.blockAt(y)
        if num < 0:
            return
        cursor = editor.textCursor()
        cursor.setPosition(block.position(), QtGui.QTextCursor.MoveMode.MoveAnchor)
        cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
        editor.setTextCursor(cursor)
        editor.horizontalScrollBar().setValue(0)

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.buttons() & Qt.MouseButton.LeftButton:
            y = a0.pos().y()
            num, block = self.editor.blockAt(y)
            if num < 0:
                return
            cursor = self.editor.textCursor()
            cursor.setPosition(block.position(), QtGui.QTextCursor.MoveMode.KeepAnchor)
            cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.EndOfLine,
                QtGui.QTextCursor.MoveMode.KeepAnchor,
            )
            self.editor.setTextCursor(cursor)


class Mod:
    No = Qt.KeyboardModifier.NoModifier
    Ctrl = Qt.KeyboardModifier.ControlModifier
    Shift = Qt.KeyboardModifier.ShiftModifier
    Alt = Qt.KeyboardModifier.AltModifier


class QCodeEditor(QtW.QPlainTextEdit):
    executionRequested = pyqtSignal(object)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("QToolTip { font-family: FONT; }".replace("FONT", FONT))
        font = QtGui.QFont(FONT, self.font().pointSize())
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)

        self._line_number_area = QLineNumberArea(self)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_number_area_width()

        self.setTabSize(4)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._magicclass_parent_ref: weakref.ReferenceType[MagicTemplate] = None
        self._highlight = None

    def tabSize(self) -> int:
        metrics = self.fontMetrics()
        return self.tabStopWidth() // metrics.width(" ")

    def setTabSize(self, size: int) -> None:
        metrics = self.fontMetrics()
        self.setTabStopWidth(size * metrics.width(" "))

    def lineNumberAreaWidth(self) -> int:
        count = max(1, self.blockCount())
        digits = len(str(count))
        space = 8 + self.fontMetrics().width("9") * digits
        return space

    def _update_line_number_area_width(self):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def _update_line_number_area(self, rect: QtCore.QRect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)

        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QtCore.QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )

    def event(self, ev: QtCore.QEvent):
        try:
            if ev.type() == QtCore.QEvent.Type.ToolTip:
                return self._show_tooltip(ev)
            elif ev.type() == QtCore.QEvent.Type.KeyPress:
                assert isinstance(ev, QtGui.QKeyEvent)
                _key = ev.key()
                _mod = ev.modifiers()
                if _key == Qt.Key.Key_Tab and _mod == Mod.No:
                    return self._tab_event()
                elif _key == Qt.Key.Key_Tab and _mod & Mod.Shift:
                    return self._back_tab_event()
                elif _key == Qt.Key.Key_Backtab:
                    return self._back_tab_event()
                # comment out selected lines
                elif _key == Qt.Key.Key_Slash and _mod & Mod.Ctrl:
                    return self._ctrl_slash_event()
                # move selected lines up or down
                elif _key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and _mod & Mod.Alt:
                    cursor = self.textCursor()
                    cursor0 = self.textCursor()
                    start = cursor.selectionStart()
                    end = cursor.selectionEnd()
                    Op = QtGui.QTextCursor.MoveOperation
                    _keep = QtGui.QTextCursor.MoveMode.KeepAnchor
                    if _key == Qt.Key.Key_Up and min(start, end) > 0:
                        cursor0.setPosition(start)
                        cursor0.movePosition(Op.PreviousBlock)
                        cursor0.movePosition(Op.StartOfLine)
                        cursor0.movePosition(Op.EndOfLine, _keep)
                        cursor0.movePosition(Op.NextCharacter, _keep)
                        txt = cursor0.selectedText()
                        cursor0.removeSelectedText()
                        # NOTE: cursor position changed!
                        cursor0.setPosition(cursor.selectionEnd())
                        cursor0.movePosition(Op.EndOfLine)
                        if cursor0.position() == self.document().characterCount() - 1:
                            cursor0.insertText("\n")
                            txt = txt.rstrip("\u2029")
                        if cursor.position() == self.document().characterCount() - 1:
                            cursor.movePosition(Op.Up)
                        cursor0.movePosition(Op.NextCharacter)
                        cursor0.insertText(txt)
                        self.setTextCursor(cursor)
                    elif (
                        _key == Qt.Key.Key_Down
                        and max(start, end) < self.document().characterCount() - 1
                    ):
                        cursor0.setPosition(end)
                        cursor0.movePosition(Op.EndOfLine)
                        cursor0.movePosition(Op.NextCharacter, _keep)
                        cursor0.movePosition(Op.EndOfLine, _keep)
                        txt = cursor0.selectedText()
                        cursor0.removeSelectedText()
                        # NOTE: cursor position changed!
                        cursor0.setPosition(cursor.selectionStart())
                        cursor0.movePosition(Op.StartOfLine)
                        if cursor0.position() == 0:
                            cursor0.insertText("\n")
                            txt = txt.lstrip("\u2029")
                        cursor0.movePosition(Op.PreviousCharacter)
                        cursor0.insertText(txt)
                        self.setTextCursor(cursor)
                    return True
                elif _key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
                    # get current line, check if it has tabs at the beginning
                    # if yes, insert the same number of tabs at the next line
                    self._new_line_event()
                    return True
                elif _key == Qt.Key.Key_Backspace and _mod == Mod.No:
                    # delete 4 spaces
                    _cursor = self.textCursor()
                    _cursor.movePosition(
                        QtGui.QTextCursor.MoveOperation.StartOfLine,
                        QtGui.QTextCursor.MoveMode.KeepAnchor,
                    )
                    line = _cursor.selectedText()
                    if line.endswith("    ") and not self.textCursor().hasSelection():
                        for _ in range(4):
                            self.textCursor().deletePreviousChar()
                        return True
                elif _key == Qt.Key.Key_D and _mod & Mod.Ctrl:
                    return self._select_word_event()
                elif _key == Qt.Key.Key_L and _mod & Mod.Ctrl:
                    return self._select_line_event()
                elif _key == Qt.Key.Key_Home and _mod == Mod.No:
                    return self._home_event()
                elif _key == Qt.Key.Key_V and _mod & Mod.Ctrl:
                    clip = QtGui.QGuiApplication.clipboard()
                    text = clip.text().replace("\t", _TAB)
                    cursor = self.textCursor()
                    cursor.insertText(text)
                    return True
                elif _key in (
                    Qt.Key.Key_ParenLeft,
                    Qt.Key.Key_BracketLeft,
                    Qt.Key.Key_BraceLeft,
                ):
                    _char = QtGui.QKeySequence(_key).toString()
                    return self._put_selection_in(_char, _PAIRS[_char])
                elif _key in (
                    Qt.Key.Key_ParenRight,
                    Qt.Key.Key_BracketRight,
                    Qt.Key.Key_BraceRight,
                ):
                    _char = QtGui.QKeySequence(_key).toString()
                    return self._key_no_duplicate(_char)
                elif _key in (
                    Qt.Key.Key_QuoteDbl,
                    Qt.Key.Key_Apostrophe,
                    Qt.Key.Key_QuoteLeft,
                ):
                    _char = QtGui.QKeySequence(_key).toString()
                    return self._quote_selection(_char)

        except Exception:
            pass
        return super().event(ev)

    def _magicclass_parent(self):
        if self._magicclass_parent_ref is None:
            return None
        return self._magicclass_parent_ref()

    def _search_parent_magicclass(self) -> MagicTemplate | None:
        if self._magicclass_parent_ref is None:
            return None
        if obj := self._magicclass_parent_ref():
            return obj._search_parent_magicclass()
        return None

    def wordAt(self, pos: QtCore.QPoint) -> WordInfo | None:
        if not self.isVisible():
            return None
        cursor = self.cursorForPosition(pos)
        cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
        block = cursor.block()
        line = block.text().strip()
        clicked_pos = cursor.position() - block.position()
        try:
            return eval_under_cursor(
                line, clicked_pos, self._search_parent_magicclass()
            )
        except Exception as e:
            print(e)
            # raise e
            return None

    def _open_magicgui(self, pos: QtCore.QPoint):
        from magicclass._gui.mgui_ext import is_clickable

        info = self.wordAt(pos)
        if info and is_clickable(info.widget):
            mgui = info.widget.mgui
            mcls = self._search_parent_magicclass()
            if mgui is None:
                # macro is not added from GUI. Create one.
                from magicclass._gui._base import _build_mgui, _create_gui_method

                func = _create_gui_method(mcls, info.obj)
                mgui = _build_mgui(info.widget, func, mcls)
                info.widget.mgui = mgui

            nwidgets = sum(not isinstance(wdt, EmptyWidget) for wdt in mgui)
            if nwidgets > 1:
                if isinstance(mgui[0], FileEdit):
                    show_dialog_from_mgui(mgui)
                else:
                    info.widget.changed()
            else:
                with mcls._error_mode.raise_with_handler(mcls):
                    raise TypeError(f"No parameter can be chosen in {info.widget!r}.")

        return

    def _show_context_menu(self, pos: QtCore.QPoint):
        menu = QtW.QMenu(self.viewport())
        cursor = self.textCursor()
        new_pos = self.cursorForPosition(pos).position()
        if not cursor.selectionStart() <= new_pos <= cursor.selectionEnd():
            cursor.setPosition(new_pos, QtGui.QTextCursor.MoveMode.MoveAnchor)
        text = cursor.selectedText()
        has_selection = len(text) > 0

        # fmt: off
        menu.addAction("Select All", self.selectAll, "Ctrl+A")
        menu.addAction("Cut", self.cut, "Ctrl+X").setEnabled(has_selection)
        menu.addAction("Copy", self.copy, "Ctrl+C").setEnabled(has_selection)
        menu.addAction("Paste", self.paste, "Ctrl+V")
        menu.addSeparator()
        menu.addAction("Undo", self.undo, "Ctrl+Z")
        menu.addAction("Redo", self.redo, "Ctrl+Y")
        menu.addSeparator()
        menu.addAction("Execute selected lines", lambda: self.executionRequested.emit("exec-line")).setEnabled(has_selection)
        menu.addAction("Register as a command", lambda: self.executionRequested.emit("register-command")).setEnabled(has_selection)
        menu.addAction("Rerun with new parameters", lambda: self._open_magicgui(pos)).setEnabled(has_selection)
        # fmt: on

        return menu.exec(self.mapToGlobal(pos))

    def _iter_visible_blocks(self, rect: QtCore.QRect = None):
        if rect is None:
            rect = self.viewport().rect()
        block = self.firstVisibleBlock()
        block_num = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and (top <= rect.bottom()):
            if block.isVisible() and (bottom >= rect.top()):
                yield block_num, block

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_num += 1

    def blockAt(self, y: int):
        for num, block in self._iter_visible_blocks():
            rect = self.blockBoundingGeometry(block)
            if rect.top() <= y <= rect.bottom():
                return num, block
        return -1, None

    def block(self, index: int) -> QtGui.QTextBlock | None:
        """Return the text block at index or None if not found."""
        for num, block in self._iter_visible_blocks():
            if num == index:
                return block
        return None

    def blocks(self, indices: list[int]) -> list[QtGui.QTextBlock]:
        blocks: list[QtGui.QTextBlock] = []
        indices = set(indices)
        for num, block in self._iter_visible_blocks():
            if num in indices:
                blocks.append(block)
        return blocks

    def lineNumberAreaPaintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self._line_number_area)

        bgcolor = self.palette().color(self.backgroundRole())
        color = QtGui.QColor(
            bgcolor.red() - 14, bgcolor.green() - 14, bgcolor.blue() + 14
        )
        painter.fillRect(event.rect(), color)

        height = self.fontMetrics().height()
        text_color = self.palette().color(self.foregroundRole())
        offset = self.contentOffset().y()
        for num, block in self._iter_visible_blocks(event.rect()):
            painter.setPen(text_color)
            block_rect = self.blockBoundingGeometry(block)
            block_height = block_rect.height()
            draw_y = block_rect.top() + max(block_height - height, 0) / 2 + offset
            painter.drawText(
                0,
                int(draw_y),
                int(self._line_number_area.width() - 2),
                int(height),
                Qt.AlignmentFlag.AlignRight,
                str(num),
            )

    def _highlight_current_line(self):
        extraSelections = []

        bgcolor = self.palette().color(self.backgroundRole())
        _highlight_color = QtGui.QColor(
            bgcolor.red() - 6, bgcolor.green() - 6, bgcolor.blue() + 6
        )

        if not self.isReadOnly():
            selection = QtW.QTextEdit.ExtraSelection()
            selection.format.setBackground(_highlight_color)
            selection.format.setProperty(
                QtGui.QTextFormat.Property.FullWidthSelection, True
            )
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def add_at_the_start(self, text: str, cursor: QtGui.QTextCursor):
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText(text)

    def remove_at_the_start(self, text: str, cursor: QtGui.QTextCursor):
        line = cursor.block().text()
        if line.startswith(text):
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.Right,
                QtGui.QTextCursor.MoveMode.KeepAnchor,
                len(text),
            )
            cursor.removeSelectedText()

    def syntaxHighlight(self, lang: str = "python", theme: str = "default"):
        """Highlight syntax."""
        from superqt.utils import CodeSyntaxHighlight

        highlight = CodeSyntaxHighlight(self.document(), lang, theme=theme)
        self._highlight = highlight
        return None

    @contextmanager
    def _fix_horizontal_position(self):
        hbar = self.horizontalScrollBar()
        pos = hbar.value()
        try:
            yield
        finally:
            hbar.setValue(pos)

    def appendPlainText(self, txt: str):
        with self._fix_horizontal_position():
            super().appendPlainText(txt)

    def eraseLast(self):
        """Erase the last line."""
        with self._fix_horizontal_position():
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()
            self.setTextCursor(cursor)

    def eraseFirst(self):
        """Erase the first line."""
        with self._fix_horizontal_position():
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Down)
            cursor.deletePreviousChar()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

    def selectedText(self) -> str:
        """Return selected string."""
        cursor = self.textCursor()
        return cursor.selectedText().replace("\u2029", "\n")

    def selectedLines(self) -> list[str]:
        """Return the selected lines that contain the cursor selection."""
        return [cursor.block().text() for cursor in self.iter_selected_lines()]

    def iter_selected_lines(self) -> Iterator[QtGui.QTextCursor]:
        """Iterate text cursors for each selected line."""
        _cursor = self.textCursor()
        start, end = sorted([_cursor.selectionStart(), _cursor.selectionEnd()])
        _cursor.setPosition(start)
        _cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
        nline = 0
        while True:
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextCharacter)
            nline += 1
            if _cursor.position() >= end:
                break

        _cursor.setPosition(start)
        for _ in range(nline):
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
            yield _cursor
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextCharacter)

    def text(self) -> str:
        """Return the text."""
        return self.toPlainText().replace("\u2029", "\n")

    def setText(self, text: str):
        """Set the text."""
        self.setPlainText(text.replace("\n", "\u2029"))

    def _text_of_current_line(self):
        _cursor = self.textCursor()
        _cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
        _cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.EndOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        return _cursor.selectedText()

    def _text_of_line_before_cursor(self):
        _cursor = self.textCursor()
        _cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        return _cursor.selectedText()

    def _show_tooltip(self, ev: QtGui.QHelpEvent):
        pos = self.viewport().mapFromGlobal(ev.globalPos())
        info = self.wordAt(pos)
        if info is None:
            return False
        try:
            tooltip = info.get_method_tooltip()
        except Exception:
            tooltip = info.get_simple_tooltip()
        QtW.QToolTip.showText(ev.globalPos(), tooltip, self)
        return True

    def _tab_event(self):
        if self.textCursor().hasSelection():
            for cursor in self.iter_selected_lines():
                self.add_at_the_start(_TAB, cursor)
        else:
            line = _text_before_cursor(self.textCursor())
            nspace = line.count(" ")
            if nspace % 4 == 0:
                self.textCursor().insertText(_TAB)
            else:
                self.textCursor().insertText(" " * 4 - nspace % 4)
        return True

    def _back_tab_event(self):
        # unindent
        for cursor in self.iter_selected_lines():
            self.remove_at_the_start(_TAB, cursor)
        return True

    def _ctrl_slash_event(self):
        for cursor in self.iter_selected_lines():
            line = cursor.block().text()
            if line.startswith("#"):
                if line.startswith("# "):
                    self.remove_at_the_start("# ", cursor)
                else:
                    self.remove_at_the_start("#", cursor)
            else:
                self.add_at_the_start("# ", cursor)
        return True

    def _select_word_event(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextWord)
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.PreviousWord,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        self.setTextCursor(cursor)
        return True

    def _select_line_event(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.EndOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.NextCharacter,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        self.setTextCursor(cursor)
        return True

    def _new_line_event(self):
        line = self._text_of_line_before_cursor()
        cursor = self.textCursor()
        line_rstripped = line.rstrip()
        indent = _get_indents(line)
        if line_rstripped == "":
            cursor.insertText("\n" + indent)
            self.setTextCursor(cursor)
            return

        ndel = len(line) - len(line_rstripped)
        last_char = line_rstripped[-1]
        _counter = Counter(line)
        _not_closed = (
            _counter["("] - _counter[")"] > 0
            or _counter["["] - _counter["]"] > 0
            or _counter["{"] - _counter["}"] > 0
        )
        if _not_closed or last_char in "([{:":
            for _ in range(ndel):
                cursor.deletePreviousChar()
            cursor.insertText("\n" + indent + _TAB)
            self.setTextCursor(cursor)
        else:
            cursor.insertText("\n" + indent)
            self.setTextCursor(cursor)

        line_lstripped = line.lstrip()
        if (
            line_lstripped.startswith("return ")
            or line_lstripped.startswith("raise ")
            or line_lstripped in ("return", "raise", "break", "continue", "pass")
        ):
            if line.startswith(_TAB):
                for _ in range(4):
                    cursor.deletePreviousChar()
        self.setTextCursor(cursor)

    def _home_event(self):
        # fn + left
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        text = cursor.selectedText()
        if all(c == " " for c in text):
            cursor.clearSelection()
        else:
            text_lstrip = text.lstrip()
            nmove = len(text) - len(text_lstrip)
            cursor.clearSelection()
            for _ in range(nmove):
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right)

        self.setTextCursor(cursor)
        return True

    def _put_selection_in(self, left: str, right: str) -> bool:
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
        pos_line_end = cursor.position()
        cursor.setPosition(end)
        if start != end or pos_line_end == end:
            cursor.insertText(right)
        cursor.setPosition(start)
        cursor.insertText(left)
        cursor.setPosition(start + 1)
        cursor.setPosition(end + 1, QtGui.QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        return True

    def _quote_selection(self, quot: str) -> bool:
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
        pos_line_end = cursor.position()
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        line = cursor.selectedText()
        nquot = line.count(quot)
        cursor.clearSelection()
        cursor.setPosition(end)
        if nquot % 2 == 0:
            if start != end or pos_line_end == end:
                cursor.insertText(quot)
        cursor.setPosition(start)
        cursor.insertText(quot)
        cursor.setPosition(start + 1)
        cursor.setPosition(end + 1, QtGui.QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        return True

    def _key_no_duplicate(self, char: str) -> bool:
        cursor = self.textCursor()
        pos = cursor.position()
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.EndOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        line = cursor.selectedText()
        if line.startswith(char):
            cursor.setPosition(pos + 1)
        else:
            cursor.setPosition(pos)
            cursor.insertText(char)
        self.setTextCursor(cursor)
        return True

    def _text_before_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        line = cursor.selectedText()
        return line


def _get_indents(text: str) -> int:
    chars = []
    for c in text:
        if c == " ":
            chars.append(" ")
        elif c == "\t":
            chars.append(_TAB)
        else:
            break
    return "".join(chars)


class WordInfo(NamedTuple):
    """Info of a word in the code."""

    widget: Any  # hovered widget (if available)
    expr: Expr  # hovered expression
    word: str  # hovered word
    obj: Any = None

    def get_simple_tooltip(self) -> str:
        return f"{self.expr} (widget: {annot_to_str(type(self.widget))})"

    def get_method_tooltip(self) -> str:
        sig = inspect.signature(self.obj)
        doc = getattr(self.obj, "__doc__", None)
        if doc is None:
            doc = "<No Docstring>"
        param_strs: list[str] = []
        for name, param in sig.parameters.items():
            if param.annotation is param.empty:
                repr_ = name
            else:
                repr_ = f"{name}: {annot_to_str(param.annotation)}"
            if param.default is not param.empty:
                repr_ += f" = {safe_repr(param.default)}"
            param_strs.append(repr_)
        if sig.return_annotation is not sig.empty:
            ret_annot = f" -> {annot_to_str(sig.return_annotation)}"
        else:
            ret_annot = ""
        if len(param_strs) == 0:
            all_args_str = ""
        else:
            all_args_str = "\n  " + ",\n  ".join(param_strs) + "\n"
        return (
            f"{self.expr} (widget: {annot_to_str(type(self.widget))})\n"
            f"def {self.expr.args[-1]}({all_args_str}){ret_annot}\n"
            f"{doc}"
        )


def annot_to_str(annot: Any) -> str:
    if isinstance(annot, type):
        return annot.__name__
    if is_annotated(annot):
        return annot_to_str(split_annotated_type(annot)[0])
    s = str(annot)
    if s.startswith("typing."):
        return s[7:]
    return s


def safe_repr(obj: Any) -> str:
    try:
        out = repr(obj)
    except Exception:
        return "???"
    if len(out) > 36:
        return out[:36] + " ..."
    return out


def eval_under_cursor(
    line: str, clicked_pos: int, parent: MagicTemplate | None = None
) -> WordInfo | None:
    if parent is None:
        return None
    expr = parse(line)
    pos_start = 0
    pos_stop = len(line)
    if not isinstance(expr, Expr):
        # got a Symbol
        obj = widget = expr.eval({expr: parent})
        words = expr

    elif expr.head is Head.call:
        first = expr.args[0]  # e.g. ui, ui.method. ui.subclass.method
        while isinstance(first, Expr) and first.head is Head.getattr:
            next_first, _ = first.args
            _length = len(str(next_first))
            if _length < clicked_pos - 1:
                pos_start = _length
                break
            first = next_first
        if len(str(first)) < clicked_pos:
            return None

        if isinstance(first, Expr):
            left, right = first.args
            words = first
            expr = Expr(Head.getitem, [left, str(right)])
            widget = expr.eval({Symbol.var("ui"): parent})
            obj = first.eval({Symbol.var("ui"): parent})
        else:
            obj = widget = first.eval({first: parent})
            words = first

    elif expr.head is Head.assign:
        first = expr.args[0]
        if not isinstance(first, Expr) or not str(first.args[0]).startswith("ui"):
            return None
        while isinstance(first, Expr) and first.head is Head.getattr:
            next_first, _ = first.args
            _length = len(str(next_first))
            if _length < clicked_pos - 1:
                pos_start = _length
                break
            first = next_first

        if isinstance(first, Expr):
            left, right = first.args
            left_obj = left.eval({Symbol.var("ui"): parent})
            if hasattr(left_obj, "__getitem__"):
                widget = left_obj[str(right)]
                obj = first.eval({Symbol.var("ui"): parent})
            else:
                obj = widget = getattr(left_obj, str(right))
            words = first
        else:
            obj = widget = first.eval({first: parent})
            words = first
    else:
        return None
    info = WordInfo(widget, words, str(words).split(".")[-1], obj)
    return info


def _text_before_cursor(cursor: QtGui.QTextCursor) -> str:
    cursor.movePosition(
        QtGui.QTextCursor.MoveOperation.StartOfLine,
        QtGui.QTextCursor.MoveMode.KeepAnchor,
    )
    line = cursor.selectedText()
    return line


# ##############################################################################
# ##############################################################################


class QBaseCodeEdit(QBaseTextEdit):
    _qwidget: QCodeEditor

    def __init__(self, **kwargs):
        QBaseStringWidget.__init__(
            self, QCodeEditor, "toPlainText", "setText", "textChanged", **kwargs
        )

    def _mgui_set_read_only(self, value: bool) -> None:
        self._qwidget.setReadOnly(value)

    def _mgui_get_read_only(self) -> bool:
        return self._qwidget.isReadOnly()


class CodeEdit(TextEdit):
    executing = Signal(object)

    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QBaseCodeEdit,
            **kwargs,
        )
        self._qcode_edit().executionRequested.connect(self.executing.emit)

    def _qcode_edit(self) -> QCodeEditor:
        return self._widget._qwidget

    @property
    def tab_size(self) -> int:
        return self._qcode_edit().tabSize()

    @tab_size.setter
    def tab_size(self, size: int) -> None:
        return self._qcode_edit().setTabSize(size)

    def erase_last(self) -> None:
        """Erase the last line."""
        self._qcode_edit().eraseLast()

    def erase_first(self) -> None:
        """Erase the first line."""
        self._qcode_edit().eraseFirst()

    def append(self, text: str) -> None:
        """Append text to the end of the document."""
        self._qcode_edit().appendPlainText(text)

    @property
    def selected(self) -> str:
        """Return selected string."""
        return self._qcode_edit().selectedText()

    def syntax_highlight(self, lang: str = "python", theme: str = "default"):
        """Highlight syntax."""
        self._qcode_edit().syntaxHighlight(lang, theme)

    @property
    def __magicclass_parent__(self) -> MagicTemplate | None:
        return self._qcode_edit()._magicclass_parent()

    @__magicclass_parent__.setter
    def __magicclass_parent__(self, val) -> None:
        self._qcode_edit()._magicclass_parent_ref = weakref.ref(val)

    def zoom_in(self) -> None:
        """Zoom in."""
        self._qcode_edit().zoomIn()

    def zoom_out(self) -> None:
        """Zoom out."""
        self._qcode_edit().zoomOut()
