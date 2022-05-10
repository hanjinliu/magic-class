from __future__ import annotations
import sys
from typing import (
    TYPE_CHECKING,
    Generic,
    Iterable,
    MutableSequence,
    Any,
    TypeVar,
)
from typing_extensions import _AnnotatedAlias, get_args
from psygnal import Signal
from qtpy import QtWidgets as QtW
from qtpy.QtGui import QTextCursor
from qtpy.QtCore import Qt
from magicgui.signature import split_annotated_type
from magicgui.widgets import (
    PushButton,
    TextEdit,
    Table,
    Container,
    CheckBox,
    create_widget,
)
from magicgui.application import use_app
from magicgui.widgets import LineEdit
from magicgui.widgets._bases.value_widget import ValueWidget, UNSET
from magicgui.backends._qtpy.widgets import (
    QBaseWidget,
    LineEdit as BaseLineEdit,
)
from .utils import FreeWidget, merge_super_sigs

if TYPE_CHECKING:
    from qtpy.QtWidgets import QTextEdit
    from superqt import QLabeledRangeSlider


if sys.platform == "win32":
    _FONT = "Consolas"
else:
    _FONT = "Menlo"


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
        inner_widget: type[ValueWidget] | None = None,
        text: str = None,
        layout="vertical",
        nullable=True,
        value=UNSET,
        options=None,
        **kwargs,
    ):
        if text is None:
            text = "Use default value"
        if options is None:
            options = {}
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
        if v is None or v is UNSET:
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


class ConsoleTextEdit(TextEdit):
    """A text edit with console-like setting."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from qtpy.QtGui import QFont, QTextOption

        self.native: QTextEdit
        font = QFont(_FONT)
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        self.native.setFont(font)
        self.native.setWordWrapMode(QTextOption.NoWrap)

        # set tab width
        self.tab_size = 4

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
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self.native.setTextCursor(cursor)

    def erase_first(self):
        """Erase the first line."""
        cursor = self.native.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.movePosition(QTextCursor.Down)
        cursor.deletePreviousChar()
        cursor.movePosition(QTextCursor.End)
        self.native.setTextCursor(cursor)

    @property
    def selected(self) -> str:
        """Return selected string."""
        cursor = self.native.textCursor()
        return cursor.selectedText().replace("\u2029", "\n")


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
    def __init__(self, value=UNSET, **kwargs):
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
    def __init__(self, value=UNSET, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QFloatEdit,
            **kwargs,
        )


_V = TypeVar("_V")


class QRangeSlider(QBaseWidget):
    _qwidget: QLabeledRangeSlider

    def _mgui_get_value(self):
        pass

    def _mgui_bind_change_callback(self, callback):
        pass

    def _mgui_set_value(self, rng):
        pass


class AbstractRangeSlider(ValueWidget, Generic[_V]):
    """
    A slider widget that represent a range like (2, 5).

    This class is a temporary one and may be substituted by magicgui widget soon.
    See https://github.com/napari/magicgui/pull/337.
    """

    changed = Signal(tuple)

    def __init__(
        self,
        value=UNSET,
        min=0,
        max=1000,
        orientation: str = "horizontal",
        nullable: bool = True,
        **kwargs,
    ):
        sl = self._construct_qt()
        sl.setMinimum(min)
        sl.setMaximum(max)
        sl.valueChanged.connect(self.changed)
        if orientation == "horizontal":
            sl.setOrientation(Qt.Horizontal)
        elif orientation == "vertical":
            sl.setOrientation(Qt.Vertical)
        else:
            raise ValueError(
                "Only horizontal and vertical orientation are currently supported"
            )
        self._slider = sl
        super().__init__(
            value=value,
            widget_type=QRangeSlider,
            backend_kwargs={"qwidg": QtW.QWidget},
            **kwargs,
        )
        self.native.setLayout(QtW.QVBoxLayout())
        self.native.setContentsMargins(0, 0, 0, 0)
        self.native.layout().addWidget(sl)

    @classmethod
    def _construct_qt(cls, *args, **kwargs) -> QLabeledRangeSlider:
        raise NotImplementedError()

    @property
    def value(self) -> tuple[_V, _V]:
        return self._slider.value()

    @value.setter
    def value(self, rng: tuple[_V, _V]) -> None:
        x0, x1 = rng
        if x0 > x1:
            raise ValueError(f"lower value exceeds higher value ({x0} > {x1}).")
        self._slider.setValue((x0, x1))

    @property
    def range(self) -> tuple[_V, _V]:
        return self._slider.minimum(), self._slider.maximum()

    @range.setter
    def range(self, rng: tuple[_V, _V]) -> None:
        x0, x1 = rng
        if x0 > x1:
            raise ValueError(f"Minimum value exceeds maximum value ({x0} > {x1}).")
        self._slider.setMinimum(x0)
        self._slider.setMaximum(x1)

    @property
    def min(self) -> _V:
        return self._slider.minimum()

    @min.setter
    def min(self, value: _V) -> None:
        self._slider.setMinimum(value)

    @property
    def max(self) -> _V:
        return self._slider.maximum()

    @max.setter
    def max(self, value: _V) -> None:
        self._slider.setMaximum(value)


class RangeSlider(AbstractRangeSlider[int]):
    @classmethod
    def _construct_qt(cls, *args, **kwargs):
        from superqt import QLabeledRangeSlider

        sl = QLabeledRangeSlider()
        sl.setHandleLabelPosition(QLabeledRangeSlider.LabelPosition.LabelsAbove)
        sl.setEdgeLabelMode(QLabeledRangeSlider.EdgeLabelMode.NoLabel)
        return sl


class FloatRangeSlider(AbstractRangeSlider[float]):
    @classmethod
    def _construct_qt(cls, *args, **kwargs):
        from superqt import QLabeledDoubleRangeSlider

        sl = QLabeledDoubleRangeSlider()
        sl.setHandleLabelPosition(QLabeledDoubleRangeSlider.LabelPosition.LabelsAbove)
        sl.setEdgeLabelMode(QLabeledDoubleRangeSlider.EdgeLabelMode.NoLabel)
        return sl


class _QtSpreadSheet(QtW.QTabWidget):
    def __init__(self):
        super().__init__()
        self.setMovable(True)
        self._n_table = 0
        self.tabBar().tabBarDoubleClicked.connect(self.editTabBarLabel)
        self.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
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
