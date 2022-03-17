from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Iterable,
    MutableSequence,
    Any,
    TypeVar,
)
from typing_extensions import _AnnotatedAlias, get_args
from psygnal import Signal
from qtpy.QtWidgets import QTabWidget, QLineEdit, QMenu, QVBoxLayout, QWidget
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
    from matplotlib.axes import Axes
    from numpy.typing import ArrayLike
    from superqt import QLabeledRangeSlider


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

            annot = get_args(kwargs["annotation"])[0]

            if isinstance(annot, _AnnotatedAlias):
                annot, metadata = split_annotated_type(annot)
                options.update(metadata)

            self._inner_value_widget = create_widget(
                annotation=annot,
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


class Figure(FreeWidget):
    """A matplotlib figure canvas."""

    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] = (4.0, 3.0),
        style=None,
        **kwargs,
    ):
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        from ._mpl_canvas import InteractiveFigureCanvas

        backend = mpl.get_backend()
        try:
            mpl.use("Agg")
            if style is None:
                fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
            else:
                with plt.style.context(style):
                    fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
        finally:
            mpl.use(backend)

        canvas = InteractiveFigureCanvas(fig)
        self.canvas = canvas
        super().__init__(**kwargs)
        self.set_widget(canvas)
        self.figure = fig
        self.min_height = 40

        # Update docstrings
        for name, method in self.__class__.__dict__.items():
            if name.startswith("_") or getattr(method, "__doc__", None) is None:
                continue
            plt_method = getattr(plt, name, None)
            plt_doc = getattr(plt_method, "__doc__", "")
            if plt_doc:
                method.__doc__ += f"\nOriginal docstring:\n\n{plt_doc}"

    def draw(self):
        """Copy of ``plt.draw()``."""
        self.figure.tight_layout()
        self.canvas.draw()

    @property
    def enabled(self) -> bool:
        """toggle interactivity of the figure canvas."""
        return self.canvas._interactive

    @enabled.setter
    def enabled(self, v: bool):
        self.canvas._interactive = bool(v)

    @property
    def mouse_click_callbacks(self) -> list[Callable]:
        return self.canvas._mouse_click_callbacks

    interactive = enabled  # alias

    def clf(self):
        """Copy of ``plt.clf``."""
        self.figure.clf()
        self.draw()

    def cla(self):
        """Copy of ``plt.cla``."""
        self.ax.cla()
        self.draw()

    @property
    def axes(self) -> list[Axes]:
        return self.figure.axes

    @property
    def ax(self) -> Axes:
        try:
            _ax = self.axes[0]
        except IndexError:
            _ax = self.figure.add_subplot(111)
        return _ax

    def savefig(self, *args, **kwargs):
        """Copy of ``plt.savefig``."""
        return self.figure.savefig(*args, **kwargs)

    def plot(self, *args, **kwargs) -> Axes:
        """Copy of ``plt.plot``."""
        self.ax.plot(*args, **kwargs)
        self.draw()
        return self.ax

    def scatter(self, *args, **kwargs) -> Axes:
        """Copy of ``plt.scatter``."""
        self.ax.scatter(*args, **kwargs)
        self.draw()
        return self.ax

    def hist(
        self, *args, **kwargs
    ) -> tuple[ArrayLike | list[ArrayLike], ArrayLike, list | list[list]]:
        """Copy of ``plt.hist``."""
        out = self.ax.hist(*args, **kwargs)
        self.draw()
        return out

    def text(self, *args, **kwargs):
        """Copy of ``plt.text``."""
        self.ax.text(*args, **kwargs)
        self.draw()
        return self.ax

    def quiver(self, *args, data=None, **kwargs):
        """Copy of ``plt.quiver``."""
        self.ax.quiver(*args, data=data, **kwargs)
        self.draw()
        return self.ax

    def axline(self, xy1, xy2=None, *, slope=None, **kwargs):
        """Copy of ``plt.axline``."""
        self.ax.axline(xy1, xy2=xy2, slope=slope, **kwargs)
        self.draw()
        return self.ax

    def axhline(self, y=0, xmin=0, xmax=1, **kwargs):
        """Copy of ``plt.axhline``."""
        self.ax.axhline(y, xmin, xmax, **kwargs)
        self.draw()
        return self.ax

    def axvline(self, x=0, ymin=0, ymax=1, **kwargs):
        """Copy of ``plt.axvline``."""
        self.ax.axvline(x, ymin, ymax, **kwargs)
        self.draw()
        return self.ax

    def xlim(self, *args, **kwargs):
        """Copy of ``plt.xlim``."""
        ax = self.ax
        if not args and not kwargs:
            return ax.get_xlim()
        ret = ax.set_xlim(*args, **kwargs)
        self.draw()
        return ret

    def ylim(self, *args, **kwargs):
        """Copy of ``plt.ylim``."""
        ax = self.ax
        if not args and not kwargs:
            return ax.get_ylim()
        ret = ax.set_ylim(*args, **kwargs)
        self.draw()
        return ret

    def imshow(self, *args, **kwargs) -> Axes:
        """Copy of ``plt.imshow``."""
        self.ax.imshow(*args, **kwargs)
        self.draw()
        return self.ax

    def legend(self, *args, **kwargs):
        """Copy of ``plt.legend``."""
        leg = self.ax.legend(*args, **kwargs)
        self.draw()
        return leg

    def title(self, *args, **kwargs):
        """Copy of ``plt.title``."""
        title = self.ax.set_title(*args, **kwargs)
        self.draw()
        return title

    def xlabel(self, *args, **kwargs):
        """Copy of ``plt.xlabel``."""
        xlabel = self.ax.set_xlabel(*args, **kwargs)
        self.draw()
        return xlabel

    def ylabel(self, *args, **kwargs):
        """Copy of ``plt.ylabel``."""
        ylabel = self.ax.set_ylabel(*args, **kwargs)
        self.draw()
        return ylabel

    def xticks(self, ticks=None, labels=None, **kwargs):
        """Copy of ``plt.xticks``."""
        if ticks is None:
            locs = self.ax.get_xticks()
            if labels is not None:
                raise TypeError(
                    "xticks(): Parameter 'labels' can't be set "
                    "without setting 'ticks'"
                )
        else:
            locs = self.ax.set_xticks(ticks)

        if labels is None:
            labels = self.ax.get_xticklabels()
        else:
            labels = self.ax.set_xticklabels(labels, **kwargs)
        for l in labels:
            l.update(kwargs)
        self.draw()
        return locs, labels

    def yticks(self, ticks=None, labels=None, **kwargs):
        """Copy of ``plt.xticks``."""
        if ticks is None:
            locs = self.ax.get_yticks()
            if labels is not None:
                raise TypeError(
                    "xticks(): Parameter 'labels' can't be set "
                    "without setting 'ticks'"
                )
        else:
            locs = self.ax.set_yticks(ticks)

        if labels is None:
            labels = self.ax.get_yticklabels()
        else:
            labels = self.ax.set_yticklabels(labels, **kwargs)
        for l in labels:
            l.update(kwargs)
        self.draw()
        return locs, labels

    def twinx(self) -> Axes:
        """Copy of ``plt.twinx``."""
        return self.ax.twinx()

    def twiny(self) -> Axes:
        """Copy of ``plt.twiny``."""
        return self.ax.twiny()

    def box(self, on=None) -> None:
        """Copy of ``plt.box``."""
        if on is None:
            on = not self.ax.get_frame_on()
        self.ax.set_frame_on(on)


class ConsoleTextEdit(TextEdit):
    """A text edit with console-like setting."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from qtpy.QtGui import QFont, QTextOption

        self.native: QTextEdit
        font = QFont("Consolas")
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
    _qwidget: QLineEdit

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
    _qwidget: QLineEdit

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
            backend_kwargs={"qwidg": QWidget},
            **kwargs,
        )
        self.native.setLayout(QVBoxLayout())
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


class _QtSpreadSheet(QTabWidget):
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
        self._line_edit = QLineEdit(self)

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
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda _: self.editTabBarLabel(index))
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda _: self.removeTab(index))

        menu.exec(tabbar.mapToGlobal(point))


class SpreadSheet(FreeWidget, MutableSequence[Table]):
    """A simple spread sheet widget."""

    def __init__(self):
        super().__init__()
        spreadsheet = _QtSpreadSheet()
        self.set_widget(spreadsheet)
        self.central_widget: _QtSpreadSheet
        self._tables: list[Table] = []

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
        if key < 0:
            key += len(self)
        table = Table(value=value)
        self.central_widget.addTable(table.native)
        self._tables.insert(key, table)

    def rename(self, index: int, name: str):
        self.central_widget.renameTab(index, name)
        return None
