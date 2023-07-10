from __future__ import annotations

from pathlib import Path
import os
from typing import (
    Iterable,
    MutableSequence,
    Any,
    TypeVar,
)
from typing_extensions import _AnnotatedAlias, get_args
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt
from magicgui.widgets import (
    PushButton,
    TextEdit,
    Table,
    Container,
    CheckBox,
    FileEdit,
    create_widget,
    LineEdit,
)
from magicgui.application import use_app
from magicgui.types import FileDialogMode, Undefined
from magicgui.widgets.bases import ValueWidget, RangedWidget
from magicgui.backends._qtpy.widgets import (
    QBaseStringWidget,
    LineEdit as BaseLineEdit,
)
from .utils import FreeWidget, merge_super_sigs
from magicclass.signature import split_annotated_type
from magicclass.widgets._const import FONT

_W = TypeVar("_W", bound=ValueWidget)


@merge_super_sigs
class OptionalWidget(Container):
    """
    A container that can represent optional argument.

    Parameters
    ----------
    widget_type : ValueWidget type
        Type of inner value widget.
    text : str, optional
        Text of checkbox.
    value : Any
        Initial value.
    options : dict, optional
        Widget options of the inner value widget.
    """

    def __init__(
        self,
        inner_widget: _W | None = None,
        text: str | None = None,
        layout: str = "vertical",
        nullable: bool = True,
        value=Undefined,
        options: dict | None = None,
        **kwargs,
    ):
        if text is None:
            text = "Use default value"
        self._checkbox = CheckBox(text=text, value=True)

        if inner_widget is None:
            annot = kwargs.get("annotation", None)
            if annot is None:
                annot_arg = type(value)
            else:
                args = get_args(annot)
                if len(args) > 0:
                    annot_arg = args[0]
                else:
                    annot_arg = type(value)

            if isinstance(annot_arg, _AnnotatedAlias):
                options = options or {}
                annot_arg, metadata = split_annotated_type(annot_arg)
                options.update(metadata)

            self._inner_value_widget = create_widget(
                annotation=annot_arg,
                options=options,
            )

        else:
            self._inner_value_widget = inner_widget

        super().__init__(
            layout=layout,
            widgets=(self._checkbox, self._inner_value_widget),
            labels=True,
            **kwargs,
        )

        @self._checkbox.changed.connect
        def _toggle_visibility(v: bool):
            self._inner_value_widget.visible = not v

        self.value = value

    @property
    def value(self) -> Any:
        if not self._checkbox.value:
            return self._inner_value_widget.value
        else:
            return None

    @value.setter
    def value(self, v: Any) -> None:
        if v is None or v is Undefined:
            self._checkbox.value = True
            self._inner_value_widget.visible = False
        else:
            self._inner_value_widget.value = v
            self._checkbox.value = False
            self._inner_value_widget.visible = True

    @property
    def text(self) -> str:
        return self._checkbox.text

    @text.setter
    def text(self, v: str) -> None:
        self._checkbox.text = v

    @property
    def inner_widget(self) -> _W:
        return self._inner_value_widget

    @property
    def min(self):
        if isinstance(self.inner_widget, RangedWidget):
            return self.inner_widget.min
        raise AttributeError(f"Inner widget {self.inner_widget} has no attribute 'min'")

    @min.setter
    def min(self, v):
        if isinstance(self.inner_widget, RangedWidget):
            self.inner_widget.min = v
        else:
            raise AttributeError(
                f"Inner widget {self.inner_widget} has no attribute 'min'"
            )

    @property
    def max(self):
        if isinstance(self.inner_widget, RangedWidget):
            return self.inner_widget.max
        raise AttributeError(f"Inner widget {self.inner_widget} has no attribute 'max'")

    @max.setter
    def max(self, v):
        if isinstance(self.inner_widget, RangedWidget):
            self.inner_widget.max = v
        else:
            raise AttributeError(
                f"Inner widget {self.inner_widget} has no attribute 'max'"
            )


class ConsoleTextEdit(TextEdit):
    """A text edit with console-like setting."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from qtpy.QtGui import QFont, QTextOption

        self.native: QtW.QTextEdit
        font = QFont(FONT)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.native.setFont(font)
        self.native.setWordWrapMode(QTextOption.WrapMode.NoWrap)

        # set tab width
        self.tab_size = 4
        self._highlight = None

    @property
    def tab_size(self):
        metrics = self.native.fontMetrics()
        return self.native.tabStopWidth() // metrics.width(" ")

    @tab_size.setter
    def tab_size(self, size: int):
        metrics = self.native.fontMetrics()
        self.native.setTabStopWidth(size * metrics.width(" "))

    def append(self, text: str):
        """Append new text."""
        self.native.append(text)

    def erase_last(self):
        """Erase the last line."""
        cursor = self.native.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self.native.setTextCursor(cursor)

    def erase_first(self):
        """Erase the first line."""
        cursor = self.native.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
        cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Down)
        cursor.deletePreviousChar()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self.native.setTextCursor(cursor)

    @property
    def selected(self) -> str:
        """Return selected string."""
        cursor = self.native.textCursor()
        return cursor.selectedText().replace("\u2029", "\n")

    def syntax_highlight(self, lang: str = "python", theme: str = "default"):
        """Highlight syntax."""
        from superqt.utils import CodeSyntaxHighlight

        highlight = CodeSyntaxHighlight(self.native.document(), lang, theme=theme)
        self._highlight = highlight
        return None


class CheckButton(PushButton):
    """A checkable button."""

    def __init__(self, text: str | None = None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native.setCheckable(True)


class QIntEdit(BaseLineEdit):
    _qwidget: QtW.QLineEdit

    def _post_get_hook(self, value):
        if value == "":
            return None
        return int(value)

    def _pre_set_hook(self, value):
        return str(value)


class IntEdit(LineEdit):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QIntEdit,
            **kwargs,
        )


class QFloatEdit(BaseLineEdit):
    _qwidget: QtW.QLineEdit

    def _post_get_hook(self, value):
        if value == "":
            return None
        return float(value)

    def _pre_set_hook(self, value):
        return str(value)


class FloatEdit(LineEdit):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QFloatEdit,
            **kwargs,
        )


class _QtSpreadSheet(QtW.QTabWidget):
    def __init__(self):
        super().__init__()
        self.setMovable(True)
        self._n_table = 0
        self.tabBar().tabBarDoubleClicked.connect(self.editTabBarLabel)
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self.showContextMenu)
        self._line_edit = None

    def addTable(self, table):
        self.addTab(table, f"Sheet {self._n_table}")
        self._n_table += 1

    def renameTab(self, index: int, name: str) -> None:
        self.tabBar().setTabText(index, name)
        return None

    def editTabBarLabel(self, index: int):
        if index < 0:
            return
        if self._line_edit is not None:
            self._line_edit.deleteLater()
            self._line_edit = None

        tabbar = self.tabBar()
        self._line_edit = QtW.QLineEdit(self)

        @self._line_edit.editingFinished.connect
        def _(_=None):
            self.renameTab(index, self._line_edit.text())
            self._line_edit.deleteLater()
            self._line_edit = None

        self._line_edit.setText(tabbar.tabText(index))
        self._line_edit.setGeometry(tabbar.tabRect(index))
        self._line_edit.setFocus()
        self._line_edit.selectAll()
        self._line_edit.show()

    def showContextMenu(self, point):
        if point.isNull():
            return
        tabbar = self.tabBar()
        index = tabbar.tabAt(point)
        menu = QtW.QMenu(self)
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda _: self.editTabBarLabel(index))
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda _: self.removeTab(index))

        menu.exec(tabbar.mapToGlobal(point))


class SpreadSheet(FreeWidget, MutableSequence[Table]):
    """A simple spread sheet widget."""

    def __init__(self, read_only: bool = False):
        super().__init__()
        spreadsheet = _QtSpreadSheet()
        self.set_widget(spreadsheet)
        self.central_widget: _QtSpreadSheet
        self._tables: list[Table] = []
        self.read_only = read_only

    def __len__(self) -> int:
        return self.central_widget.count()

    def index(self, item: Table | str):
        if isinstance(item, Table):
            for i, table in enumerate(self._tables):
                if item is table:
                    return i
            else:
                raise ValueError
        elif isinstance(item, str):
            tabbar = self.central_widget.tabBar()
            for i in range(tabbar.count()):
                text = tabbar.tabText(i)
                if text == item:
                    return i
            else:
                raise ValueError
        else:
            raise TypeError

    def __getitem__(self, key):
        if isinstance(key, str):
            key = self.index(key)
        return self._tables[key]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        if isinstance(key, str):
            key = self.index(key)
        self.central_widget.removeTab(key)
        del self._tables[key]

    def __iter__(self) -> Iterable[Table]:
        return iter(self._tables)

    def insert(self, key: int, value):
        """Insert a table-like data as a new sheet."""
        if key < 0:
            key += len(self)
        table = Table(value=value)
        table.read_only = self.read_only
        self.central_widget.addTable(table.native)
        self._tables.insert(key, table)
        return None

    def rename(self, index: int, name: str):
        """Rename tab at index `index` with name `name`."""
        self.central_widget.renameTab(index, name)
        return None

    @property
    def read_only(self):
        return self._read_only

    @read_only.setter
    def read_only(self, v: bool):
        for table in self._tables:
            table.read_only = v
        self._read_only = v


class _QEditableComboBox(QtW.QComboBox):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setSizePolicy(QtW.QSizePolicy.Policy.Ignored, QtW.QSizePolicy.Policy.Fixed)

    def showPopup(self):
        """Do not abbreviate the text."""
        self.view().setMinimumWidth(self.view().sizeHintForColumn(0))
        return super().showPopup()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            self.showPopup()
        super().keyPressEvent(event)

    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        """Don't change the value when scrolling the mouse wheel."""
        return None

    def _append_history(self, text: str):
        i = self.findText(text)
        if i >= 0:
            self.removeItem(i)
        self.addItem(text)
        if self.count() == 1:
            self.setCurrentIndex(0)

    def _pop_history(self, i: int):
        nhist = self.count()
        if i < 0:
            i += nhist
        if 0 <= i < nhist:
            return self.removeItem(i)
        raise IndexError(
            f"Index {i} out of range. There are {nhist} items in the history."
        )


class QHistoryLineEdit(QBaseStringWidget):
    _qwidget: _QEditableComboBox

    def __init__(self, **kwargs):
        super().__init__(
            _QEditableComboBox,
            "currentText",
            "setCurrentText",
            "currentTextChanged",
            **kwargs,
        )


class HistoryLineEdit(LineEdit):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QHistoryLineEdit,
            **kwargs,
        )

    def append_history(self, text: str) -> None:
        """Append new history to the line edit"""
        return self.native._append_history(text)

    def pop_history(self, i: int):
        """Pop history at index `i`"""
        return self.native._pop_history(i)

    def get_history(self) -> list[str]:
        """Return the history as a list"""
        return [self.native.itemText(i) for i in range(self.native.count())]


class HistoryFileEdit(FileEdit):
    def __init__(
        self,
        mode: FileDialogMode = FileDialogMode.EXISTING_FILE,
        filter=None,
        nullable=False,
        **kwargs,
    ):
        value = kwargs.pop("value", None)
        if value is None:
            value = ""
        self.line_edit = HistoryLineEdit(value=value)
        self.choose_btn = PushButton()
        self.mode = mode  # sets the button text too
        self.filter = filter
        self._nullable = nullable
        kwargs["widgets"] = [self.line_edit, self.choose_btn]
        kwargs["labels"] = False
        kwargs["layout"] = "horizontal"
        Container.__init__(self, **kwargs)
        self.margins = (0, 0, 0, 0)
        self._show_file_dialog = use_app().get_obj("show_file_dialog")
        self.choose_btn.changed.disconnect()
        self.line_edit.changed.disconnect()
        self.choose_btn.changed.connect(self._on_choose_clicked)
        self.choose_btn.max_width = 60
        self.line_edit.changed.connect(lambda: self.changed.emit(self.value))
        self._append_history_of_current()

    def _append_history_of_current(self):
        val = self.value
        if isinstance(val, (str, Path)):
            val = str(val)
            if val != ".":
                self.line_edit.append_history(val)
        elif isinstance(val, tuple):
            self.line_edit.append_history("; ".join(map(str, val)))

    def _on_choose_clicked(self):
        _p = self.value
        if _p:
            start_path: Path = _p[0] if isinstance(_p, tuple) else _p
            _start_path: str | None = os.fspath(start_path.expanduser().absolute())
        else:
            _start_path = None
        result = self._show_file_dialog(
            self.mode,
            caption=self._btn_text,
            start_path=_start_path,
            filter=self.filter,
        )
        if result:
            self.value = result
            self._append_history_of_current()

    def append_history(self, path: str | Path):
        """Append new history to the line edit""" ""
        return self.line_edit.append_history(path)

    def pop_history(self, i: int):
        """Pop history at index `i`"""
        return self.line_edit.pop_history(i)

    def get_history(self) -> list[Path]:
        """Return the history as a list"""
        return [Path(p) for p in self.line_edit.get_history()]
