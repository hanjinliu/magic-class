from __future__ import annotations
import sys
from typing import Any, NamedTuple, TYPE_CHECKING
import weakref
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal as pyqtSignal

from psygnal import Signal
from magicgui.backends._qtpy.widgets import TextEdit as QBaseTextEdit, QBaseStringWidget
from magicgui.widgets import TextEdit, EmptyWidget, FileEdit
from magicgui.application import use_app

from macrokit import parse, Symbol, Expr, Head
from magicclass._gui.utils import show_dialog_from_mgui
from magicclass._magicgui_compat import ValueWidget, Undefined
from magicclass.utils import show_messagebox

if TYPE_CHECKING:
    from magicclass import MagicTemplate


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


class QCodeEditor(QtW.QPlainTextEdit):
    executionRequested = pyqtSignal(object)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        if sys.platform == "win32":
            _font = "Consolas"
        elif sys.platform == "darwin":
            _font = "Menlo"
        else:
            _font = "Monospace"
        font = QtGui.QFont(_font, self.font().pointSize())
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

    def tabSize(self):
        metrics = self.fontMetrics()
        return self.tabStopWidth() // metrics.width(" ")

    def setTabSize(self, size: int):
        metrics = self.fontMetrics()
        self.setTabStopWidth(size * metrics.width(" "))

    def lineNumberAreaWidth(self):
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
        if ev.type() == QtCore.QEvent.Type.ToolTip:
            ev = QtGui.QHelpEvent(ev)
            line = self._analyze_line(self.viewport().mapFromGlobal(ev.globalPos()))
            QtW.QToolTip.showText(ev.globalPos(), str(line), self)
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

    def _analyze_line(self, pos: QtCore.QPoint):
        """Analyze the line under position."""
        info = self.wordAt(pos)
        if info is None:
            return ""
        return f"{info.expr} (type: {type(info.obj).__name__})"

    def wordAt(self, pos: QtCore.QPoint) -> WordInfo | None:
        cursor = self.cursorForPosition(pos)
        cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
        block = cursor.block()
        line = block.text()
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
        from magicclass._gui.mgui_ext import PushButtonPlus, Action

        info = self.wordAt(pos)
        if info and isinstance(info.obj, (PushButtonPlus, Action)):
            mgui = info.obj.mgui
            if mgui is None:
                return show_messagebox("error", "Error", "No magicgui found", self)
            nwidgets = sum(not isinstance(wdt, EmptyWidget) for wdt in mgui)
            if nwidgets > 1:
                if isinstance(mgui[0], FileEdit):
                    show_dialog_from_mgui(mgui)
                else:
                    mgui.show()
            else:
                show_messagebox(
                    "error",
                    "Error",
                    f"No parameter can be chosen in {info.obj.name!r}.",
                    self,
                )
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

        for num, block in self._iter_visible_blocks(event.rect()):
            painter.setPen(text_color)
            block_rect = self.blockBoundingGeometry(block)
            block_height = block_rect.height()
            draw_y = block_rect.top() + max(block_height - height, 0) / 2
            painter.drawText(
                0,
                int(draw_y),
                int(self._line_number_area.width() - 2),
                int(height),
                Qt.AlignmentFlag.AlignRight,
                str(num + 1),
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

    def eraseLast(self):
        """Erase the last line."""
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self.setTextCursor(cursor)

    def eraseFirst(self):
        """Erase the first line."""
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

    def text(self) -> str:
        """Return the text."""
        return self.toPlainText().replace("\u2029", "\n")

    def setText(self, text: str):
        """Set the text."""
        self.setPlainText(text.replace("\n", "\u2029"))


class WordInfo(NamedTuple):
    obj: Any
    expr: Expr
    word: str


def eval_under_cursor(
    line: str, clicked_pos: int, parent: MagicTemplate
) -> WordInfo | None:
    expr = parse(line)
    pos_start = 0
    pos_stop = len(line)
    if not isinstance(expr, Expr):
        # got a Symbol
        obj = expr.eval({expr: parent})
        words = expr

    elif expr.head is Head.call:
        first = expr.args[0]
        while isinstance(first, Expr) and first.head is Head.getattr:
            next_first, _ = first.args
            _length = len(str(next_first))
            if _length < clicked_pos - 1:
                pos_start = _length
                break
            first = next_first

        if isinstance(first, Expr):
            left, right = first.args
            words = first
            expr = Expr(Head.getitem, [left, str(right)])
            obj = expr.eval({Symbol.var("ui"): parent})
        else:
            obj = first.eval({first: parent})
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
                obj = left_obj[str(right)]
            else:
                obj = getattr(left_obj, str(right))
            words = first
        else:
            obj = first.eval({first: parent})
            words = first
    else:
        return None
    return WordInfo(obj, words, str(words).split(".")[-1])


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
    def tab_size(self):
        return self._qcode_edit().tabSize()

    @tab_size.setter
    def tab_size(self, size: int):
        return self._qcode_edit().setTabSize(size)

    def erase_last(self):
        """Erase the last line."""
        self._qcode_edit().eraseLast()

    def erase_first(self):
        """Erase the first line."""
        self._qcode_edit().eraseFirst()

    def append(self, text: str):
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
    def __magicclass_parent__(self):
        return self._qcode_edit()._magicclass_parent()

    @__magicclass_parent__.setter
    def __magicclass_parent__(self, val):
        self._qcode_edit()._magicclass_parent_ref = weakref.ref(val)

    def zoom_in(self):
        """Zoom in."""
        self._qcode_edit().zoomIn()

    def zoom_out(self):
        """Zoom out."""
        self._qcode_edit().zoomOut()
