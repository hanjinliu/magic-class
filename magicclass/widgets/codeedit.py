from __future__ import annotations
from contextlib import contextmanager
import inspect
from typing import Any, Generator, Iterator, NamedTuple, TYPE_CHECKING
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
# characters before which brackets and quotations are automatically closed
# (empty string means the end of line)
_CAN_CLOSE_BEFORE = ("", " ", ")", "]", "}", ",", ":")
_STR_PREFIXES = ("r", "b", "f", "u", "rb", "br", "rf", "fr")


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
                if self._handle_key_press(ev):
                    return True
        except Exception:
            pass
        return super().event(ev)

    def _handle_key_press(self, ev: QtGui.QKeyEvent) -> bool:
        """Handle key press. Return True if the event is consumed."""
        _key = ev.key()
        _mod = ev.modifiers()
        _ctrl = bool(_mod & Mod.Ctrl)

        # keys that do not edit the text
        if _key == Qt.Key.Key_D and _ctrl:
            return self._select_word_event()
        elif _key == Qt.Key.Key_L and _ctrl:
            return self._select_line_event()
        elif _key == Qt.Key.Key_Home and _mod == Mod.No:
            return self._home_event()

        # NOTE: QTextCursor can edit the document even if the widget is read-only.
        if self.isReadOnly():
            return False

        if _key == Qt.Key.Key_Tab and _mod == Mod.No:
            return self._tab_event()
        elif _key == Qt.Key.Key_Tab and _mod & Mod.Shift:
            return self._back_tab_event()
        elif _key == Qt.Key.Key_Backtab:
            return self._back_tab_event()
        # comment out selected lines
        elif _key == Qt.Key.Key_Slash and _ctrl:
            return self._ctrl_slash_event()
        # move selected lines up or down
        elif _key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and _mod & Mod.Alt:
            return self._move_lines_event(up=_key == Qt.Key.Key_Up)
        elif _key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            # keep (or increase/decrease) the indent in the next line
            return self._new_line_event()
        elif _key == Qt.Key.Key_Backspace and _mod == Mod.No:
            return self._backspace_event()

        # Ctrl+Alt (AltGr) is used to type brackets in some keyboard layouts
        if _ctrl and not _mod & Mod.Alt:
            return False
        if _key in (
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
        return False

    def insertFromMimeData(self, source: QtCore.QMimeData):
        # paste (Ctrl+V, context menu, drop ...) as a plain text without tabs
        if source.hasText():
            self.textCursor().insertText(source.text().replace("\t", _TAB))
            self.ensureCursorVisible()
        else:
            super().insertFromMimeData(source)

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

    @contextmanager
    def _edit_block(self) -> Generator[QtGui.QTextCursor]:
        """Group the edits into a single undo step."""
        cursor = QtGui.QTextCursor(self.document())
        cursor.beginEditBlock()
        try:
            yield cursor
        finally:
            cursor.endEditBlock()

    def _selected_block_numbers(self) -> list[int]:
        """Line numbers of the lines that are (partially) selected."""
        cursor = self.textCursor()
        doc = self.document()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        first = doc.findBlock(start).blockNumber()
        last_block = doc.findBlock(end)
        last = last_block.blockNumber()
        if last > first and end == last_block.position():
            # selection ends at the beginning of a line (such as Ctrl+L)
            last -= 1
        return list(range(first, last + 1))

    def _selection_is_multiline(self) -> bool:
        cursor = self.textCursor()
        doc = self.document()
        return doc.findBlock(cursor.selectionStart()) != doc.findBlock(
            cursor.selectionEnd()
        )

    def _remove_range(self, cursor: QtGui.QTextCursor, start: int, stop: int):
        cursor.setPosition(start)
        cursor.setPosition(stop, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

    def _tab_event(self):
        doc = self.document()
        if self._selection_is_multiline():
            # indent
            with self._edit_block() as cursor:
                for num in self._selected_block_numbers():
                    block = doc.findBlockByNumber(num)
                    if block.text().strip() == "":
                        continue
                    cursor.setPosition(block.position())
                    cursor.insertText(_TAB)
        else:
            # move to the next tab stop
            cursor = self.textCursor()
            start = cursor.selectionStart()
            col = start - doc.findBlock(start).position()
            cursor.insertText(" " * (4 - col % 4))
            self.ensureCursorVisible()
        return True

    def _back_tab_event(self):
        # unindent
        doc = self.document()
        with self._edit_block() as cursor:
            for num in self._selected_block_numbers():
                block = doc.findBlockByNumber(num)
                line = block.text()
                if line.startswith("\t"):
                    nchars = 1
                else:
                    nchars = min(len(line) - len(line.lstrip(" ")), 4)
                if nchars > 0:
                    pos = block.position()
                    self._remove_range(cursor, pos, pos + nchars)
        return True

    def _ctrl_slash_event(self):
        doc = self.document()
        nums = self._selected_block_numbers()
        lines = [doc.findBlockByNumber(num).text() for num in nums]
        if len(nums) > 1:
            # ignore empty lines
            targets = [(n, line) for n, line in zip(nums, lines) if line.strip()]
        else:
            targets = list(zip(nums, lines))
        if not targets:
            return True
        all_commented = all(line.lstrip().startswith("#") for _, line in targets)
        with self._edit_block() as cursor:
            if all_commented:
                for num, line in targets:
                    idx = line.index("#")
                    nchars = 2 if line[idx + 1 : idx + 2] == " " else 1
                    pos = doc.findBlockByNumber(num).position() + idx
                    self._remove_range(cursor, pos, pos + nchars)
            else:
                # comment out at the same column
                indent = min(len(line) - len(line.lstrip()) for _, line in targets)
                for num, line in targets:
                    cursor.setPosition(doc.findBlockByNumber(num).position() + indent)
                    cursor.insertText("# ")
        return True

    def _move_lines_event(self, up: bool):
        doc = self.document()
        nums = self._selected_block_numbers()
        first, last = nums[0], nums[-1]
        if (up and first == 0) or (not up and last == doc.blockCount() - 1):
            return True
        _cursor = self.textCursor()
        anchor, pos = _cursor.anchor(), _cursor.position()
        with self._edit_block() as cursor:
            if up:
                # move the previous line to the next of the selected lines
                text = doc.findBlockByNumber(first - 1).text()
                dst = doc.findBlockByNumber(last)
                cursor.setPosition(dst.position() + dst.length() - 1)
                cursor.insertText("\n" + text)
                src = doc.findBlockByNumber(first - 1)
                self._remove_range(
                    cursor, src.position(), src.position() + src.length()
                )
                shift = -(len(text) + 1)
            else:
                # move the next line to the previous of the selected lines
                src = doc.findBlockByNumber(last + 1)
                text = src.text()
                self._remove_range(
                    cursor, src.position() - 1, src.position() + src.length() - 1
                )
                cursor.setPosition(doc.findBlockByNumber(first).position())
                cursor.insertText(text + "\n")
                shift = len(text) + 1
        max_pos = doc.characterCount() - 1
        _cursor.setPosition(min(anchor + shift, max_pos))
        _cursor.setPosition(
            min(pos + shift, max_pos), QtGui.QTextCursor.MoveMode.KeepAnchor
        )
        self.setTextCursor(_cursor)
        return True

    def _backspace_event(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        pos = cursor.position()
        line = cursor.block().text()[: pos - cursor.block().position()]
        if line == "" or line.strip(" ") != "":
            return False
        # in the indent. Delete spaces to the previous tab stop
        nchars = (len(line) - 1) % 4 + 1
        self._remove_range(cursor, pos - nchars, pos)
        self.setTextCursor(cursor)
        return True

    def _select_word_event(self):
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
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
        cursor = self.textCursor()
        start = cursor.selectionStart()
        block = self.document().findBlock(start)
        line = block.text()[: start - block.position()]
        indent = _get_indents(line)
        code = line.strip()
        ndel = 0
        if code and not code.startswith("#"):
            _counter = Counter(code)
            _not_closed = any(_counter[l] > _counter[r] for l, r in _PAIRS.items())
            if _not_closed or code.endswith(":"):
                indent += _TAB
                ndel = len(line) - len(line.rstrip())
            elif (
                code.startswith(("return ", "raise "))
                or code in ("return", "raise", "break", "continue", "pass")
            ) and indent.endswith(_TAB):
                indent = indent[: -len(_TAB)]
        cursor.beginEditBlock()
        try:
            cursor.removeSelectedText()
            if ndel > 0:
                self._remove_range(cursor, start - ndel, start)
            cursor.insertText("\n" + indent)
        finally:
            cursor.endEditBlock()
        self.setTextCursor(cursor)
        return True

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

    def _chars_around_cursor(self) -> tuple[str, str, str]:
        """Return (text of the line, previous character, next character)."""
        cursor = self.textCursor()
        line = cursor.block().text()
        col = cursor.position() - cursor.block().position()
        return line, line[max(col - 1, 0) : col], line[col : col + 1]

    def _wrap_selection(self, left: str, right: str) -> bool:
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.beginEditBlock()
        try:
            cursor.setPosition(end)
            cursor.insertText(right)
            cursor.setPosition(start)
            cursor.insertText(left)
        finally:
            cursor.endEditBlock()
        cursor.setPosition(start + 1)
        cursor.setPosition(end + 1, QtGui.QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        return True

    def _insert_pair(self, left: str, right: str) -> bool:
        cursor = self.textCursor()
        pos = cursor.position()
        cursor.insertText(left + right)
        cursor.setPosition(pos + len(left))
        self.setTextCursor(cursor)
        return True

    def _put_selection_in(self, left: str, right: str) -> bool:
        if self.textCursor().hasSelection():
            return self._wrap_selection(left, right)
        _, _, next_char = self._chars_around_cursor()
        if next_char in _CAN_CLOSE_BEFORE:
            return self._insert_pair(left, right)
        return False

    def _quote_selection(self, quot: str) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return self._wrap_selection(quot, quot)
        line, prev_char, next_char = self._chars_around_cursor()
        if next_char == quot:
            # just go out of the quotation
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right)
            self.setTextCursor(cursor)
            return True
        if line.count(quot) % 2 == 1 or next_char not in _CAN_CLOSE_BEFORE:
            return False
        if prev_char == quot:
            return False
        if prev_char.isalnum() or prev_char == "_":
            # such as "it's". String prefixes are exceptions.
            col = cursor.position() - cursor.block().position()
            word = _last_word(line[:col])
            if word.lower() not in _STR_PREFIXES:
                return False
        return self._insert_pair(quot, quot)

    def _key_no_duplicate(self, char: str) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        line, _, next_char = self._chars_around_cursor()
        left = {v: k for k, v in _PAIRS.items()}[char]
        if next_char == char and line.count(left) <= line.count(char):
            # already closed
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right)
            self.setTextCursor(cursor)
            return True
        return False


def _last_word(text: str) -> str:
    chars = []
    for c in reversed(text):
        if c.isalnum() or c == "_":
            chars.append(c)
        else:
            break
    return "".join(reversed(chars))


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
