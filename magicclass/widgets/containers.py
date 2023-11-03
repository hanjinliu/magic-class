from __future__ import annotations

from typing import Any, Callable, Sequence, TypeVar, TYPE_CHECKING
import warnings
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, QSize

from magicgui.application import use_app
from magicgui.widgets import Widget
from magicgui.widgets._concrete import _LabeledWidget
from magicgui.backends._qtpy.widgets import (
    QBaseWidget,
    Container as ContainerBase,
    MainWindow as MainWindowBase,
)
from magicgui.widgets.bases import ContainerWidget

from .utils import merge_super_sigs

if TYPE_CHECKING:
    from typing import TypeGuard
    from magicclass._gui import BaseGui

# Container variations that is useful in making GUI designs better.

C = TypeVar("C", bound=ContainerWidget)
_W = TypeVar("_W", bound=Widget)


def wrap_container(
    cls: type[C] | None = None,
    base: type | None = None,
    *,
    additionals: Sequence[str] = (),
) -> Callable | type[C]:
    """Provide a wrapper for containers widget with a new protocol."""

    def wrapper(cls) -> type[Widget]:
        def __init__(self, **kwargs):
            app = use_app()
            assert app.native
            kwargs["widget_type"] = base
            _container_kwargs = {}
            for key in additionals:
                if key in kwargs:
                    _container_kwargs[key] = kwargs.pop(key)
            super(cls, self).__init__(**kwargs)
            for key, value in _container_kwargs.items():
                setattr(self, key, value)

        cls.__init__ = __init__
        cls = merge_super_sigs(cls)
        return cls

    return wrapper(cls) if cls else wrapper


class _Splitter(ContainerBase):
    _qwidget: QtW.QWidget

    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)
        # SetLayout is not supported for QSplitter.
        # Layout is just a dummy.
        self._splitter = QtW.QSplitter(self._qwidget)
        if layout == "horizontal":
            self._splitter.setOrientation(Qt.Orientation.Horizontal)
            self._layout = QtW.QHBoxLayout()
        else:
            self._splitter.setOrientation(Qt.Orientation.Vertical)
            self._layout = QtW.QVBoxLayout()

        self._scroll_area = None
        self._qwidget.setLayout(QtW.QVBoxLayout())
        self._qwidget.layout().addWidget(self._splitter)
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)

    def _mgui_insert_widget(self, position: int, widget: Widget):
        self._splitter.insertWidget(position, widget.native)

    def _mgui_remove_widget(self, widget: Widget):
        widget.native.setParent(None)

    def _mgui_get_margins(self) -> tuple[int, int, int, int]:
        return (0, 0, 0, 0)

    def _mgui_set_margins(self, margins: tuple[int, int, int, int]) -> None:
        pass


class _ToolBox(ContainerBase):
    _qwidget: QtW.QToolBox

    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QToolBox)

        if layout == "horizontal":
            msg = "Horizontal ToolBox is not implemented yet."
            warnings.warn(msg, UserWarning)

        self._layout = self._qwidget.layout()

    def _mgui_insert_widget(self, position: int, widget: Widget):
        if _is_unwrapped(widget):
            return
        self._qwidget.insertItem(position, widget.native, widget.name)

    def _mgui_remove_widget(self, widget: Widget):
        for i in range(self._qwidget.count()):
            if self._qwidget.widget(i) is widget.native:
                self._qwidget.removeItem(i)
                widget.native.setParent(None)
                break
        else:
            raise ValueError(f"Widget {widget.name} not found.")


class _Tab(ContainerBase):
    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)

        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()
        self._scroll_area = None
        self._tab_widget = QtW.QTabWidget(self._qwidget)
        self._tab_widget.setLayout(self._layout)
        self._qwidget.setLayout(QtW.QVBoxLayout())
        self._qwidget.layout().addWidget(self._tab_widget)
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)

    def _mgui_insert_widget(self, position: int, widget: Widget):
        if _is_unwrapped(widget):
            return
        if isinstance(widget, _LabeledWidget):
            tabname = widget._label_widget.value
        else:
            tabname = widget.name or widget.label
        idx = self._tab_widget.insertTab(position, widget.native, tabname)
        if _is_magicclass(widget):
            qicon = widget.icon.get_qicon(widget)
            self._tab_widget.setTabIcon(idx, qicon)

    def _mgui_remove_widget(self, widget: Widget):
        for i in range(self._tab_widget.count()):
            if self._tab_widget.widget(i) is widget.native:
                self._tab_widget.removeTab(i)
                widget.native.setParent(None)
                break
        else:
            raise ValueError(f"Widget {widget.name} not found.")


class _Stack(ContainerBase):
    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)

        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()

        self._stacked_widget = QtW.QStackedWidget(self._qwidget)
        self._stacked_widget.setContentsMargins(0, 0, 0, 0)
        self._inner_qwidget = QtW.QWidget(self._qwidget)
        self._qwidget.setLayout(self._layout)
        self._layout.addWidget(self._stacked_widget)
        self._layout.addWidget(self._inner_qwidget)

    def _mgui_insert_widget(self, position: int, widget: Widget):
        self._stacked_widget.insertWidget(position, widget.native)

    def _mgui_remove_widget(self, widget: Widget):
        self._stacked_widget.removeWidget(widget.native)
        widget.native.setParent(None)


class _ScrollableContainer(ContainerBase):
    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)
        self._scroll_area = QtW.QScrollArea(self._qwidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
            self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self._layout = QtW.QVBoxLayout()
            self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setContentsMargins(0, 0, 0, 0)
        self._inner_qwidget = QtW.QWidget(self._scroll_area)
        self._inner_qwidget.setLayout(self._layout)
        self._scroll_area.setWidget(self._inner_qwidget)

        self._qwidget.setLayout(QtW.QVBoxLayout())
        self._qwidget.layout().addWidget(self._scroll_area)
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)

    def _policy(self, value):
        if value:
            policy = Qt.ScrollBarPolicy.ScrollBarAsNeeded
        else:
            policy = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        return policy

    def x_scrollable(self):
        xpolicy = self._scroll_area.horizontalScrollBarPolicy()
        return xpolicy != Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    def set_x_scrollable(self, value: bool):
        self._scroll_area.setHorizontalScrollBarPolicy(self._policy(value))

    def y_scrollable(self):
        ypolicy = self._scroll_area.verticalScrollBarPolicy()
        return ypolicy != Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    def set_y_scrollable(self, value: bool):
        self._scroll_area.setVerticalScrollBarPolicy(self._policy(value))


class _WheelDisabledScrollArea(QtW.QScrollArea):
    def eventFilter(self, source, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.Type.Wheel:
            return True
        return super().eventFilter(source, event)


class _DraggableContainer(ContainerBase):
    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)
        self._scroll_area = _WheelDisabledScrollArea(self._qwidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
            self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self._layout = QtW.QVBoxLayout()
            self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setContentsMargins(0, 0, 0, 0)
        self._inner_qwidget = QtW.QWidget(self._scroll_area)
        self._inner_qwidget.setLayout(self._layout)
        self._scroll_area.setWidget(self._inner_qwidget)

        self._qwidget.setLayout(QtW.QVBoxLayout())
        self._qwidget.layout().addWidget(self._scroll_area)
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)
        QtW.QScroller.grabGesture(
            self._scroll_area, QtW.QScroller.ScrollerGestureType.LeftMouseButtonGesture
        )

        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )


class _ButtonContainer(ContainerBase):
    def __init__(self, layout="vertical", text="", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()

        self._qwidget = QtW.QPushButton()
        self._inner_qwidget = QtW.QWidget()
        self._inner_qwidget.setParent(self._qwidget, self._inner_qwidget.windowFlags())
        self._inner_qwidget.setLayout(self._layout)

        self._qwidget.setText(text)
        self._qwidget.clicked.connect(lambda x: self._inner_qwidget.show())


_VERTICAL_SETTING = {
    "expanded-arrow": Qt.ArrowType.DownArrow,
    "collapsed-arrow": Qt.ArrowType.RightArrow,
    "align": Qt.AlignmentFlag.AlignTop,
    "text-align": "left",
    "property-name": b"maximumHeight",
    "layout": QtW.QVBoxLayout,
}
_HORIZONTAL_SETTING = {
    "expanded-arrow": Qt.ArrowType.RightArrow,
    "collapsed-arrow": Qt.ArrowType.LeftArrow,
    "align": Qt.AlignmentFlag.AlignLeft,
    "text-align": "center",
    "property-name": b"maximumWidth",
    "layout": QtW.QHBoxLayout,
}


# modified from superqt\collapsible\_collapsible.py
class _QCollapsible(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None, layout: str = "vertical"):
        super().__init__(parent)

        if layout == "horizontal":
            _layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            _layout = QtW.QVBoxLayout()

        _layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(_layout)
        self._collapsed = True

        self._animation = QtCore.QPropertyAnimation(self)
        self._animation.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

    def setPropertyName(self, name: bytes):
        self._animation.setPropertyName(name)
        self._animation.setStartValue(0)
        self._animation.setDuration(300)
        self._animation.setTargetObject(self)

    def sizeHint(self) -> QSize:
        if not self._collapsed:
            return super().sizeHint()
        else:
            return QSize(0, 0)

    def collapsed(self):
        return self._collapsed

    def setCollapsed(self, col: bool):
        if col:
            direction = QtCore.QPropertyAnimation.Direction.Backward
        else:
            direction = QtCore.QPropertyAnimation.Direction.Forward
        self._collapsed = col
        _content_height = self.sizeHint().height() + 10
        self._animation.setDirection(direction)
        self._animation.setEndValue(_content_height)
        self._animation.start()


class _Collapsibles(ContainerBase):
    _setting: dict[str, Any]

    def __init__(
        self,
        layout: str = "vertical",
        text: str = "",
        scrollable: bool = False,
        **kwargs,
    ):
        QBaseWidget.__init__(self, QtW.QWidget, **kwargs)

        self._get_setting()
        self._qwidget = QtW.QWidget()
        self._qwidget.setLayout(self._setting["layout"]())
        self._inner_qwidget = _QCollapsible(self._qwidget, layout)
        self._inner_qwidget.setPropertyName(self._setting["property-name"])
        self._layout = self._inner_qwidget.layout()

        self._qwidget.layout().setSpacing(0)

        self._expand_btn = QtW.QToolButton(self._qwidget)
        self._expand_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._expand_btn.setArrowType(self._setting["expanded-arrow"])
        self._expand_btn.setText(text)
        self._expand_btn.setCheckable(True)
        self._expand_btn.setChecked(True)
        self._expand_btn.setStyleSheet(
            f"""
            QToolButton {{
                border: none;
                text-align: {self._setting['text-align']};
                }}
            """
        )
        self._expand_btn.clicked.connect(self._mgui_change_expand)

        self._qwidget.layout().addWidget(self._expand_btn, 0, self._setting["align"])
        self._qwidget.layout().addWidget(self._inner_qwidget, 0, self._setting["align"])
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)

    @property
    def collapsed(self) -> bool:
        return not self._expand_btn.isChecked()

    def _collapse(self):
        self._inner_qwidget.setCollapsed(True)
        self._expand_btn.setArrowType(self._setting["collapsed-arrow"])

    def _expand(self):
        self._inner_qwidget.setCollapsed(False)
        self._expand_btn.setArrowType(self._setting["expanded-arrow"])

    def _mgui_change_expand(self):
        if self.collapsed:
            self._collapse()
        else:
            self._expand()

    def _get_setting(self):
        raise NotImplementedError()


class _VCollapsibleContainer(_Collapsibles):
    def _get_setting(self):
        self._setting = _VERTICAL_SETTING


class _HCollapsibleContainer(_Collapsibles):
    def _get_setting(self):
        self._setting = _HORIZONTAL_SETTING


class _QListWidget(QtW.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtW.QAbstractItemView.DragDropMode.InternalMove)

    def dropEvent(self, event):
        widget = self.itemWidget(self.currentItem())
        super().dropEvent(event)

        # It seems that QListView has a bug in drag-and-drop.
        # When we tried to move the first item to the upper half region of the
        # second item, the inner widget of the first item dissapears.
        # This bug seemed to be solved to set the inner widget again.
        item = self.itemAt(event.pos())
        dest = self.itemWidget(item)
        if dest is None:
            self.setItemWidget(item, widget)


class _ListContainer(ContainerBase):
    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)
        self._listwidget = _QListWidget(self._qwidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._listwidget)
        self._qwidget.setLayout(self._layout)

        if layout == "horizontal":
            self._listwidget.setFlow(QtW.QListView.Flow.LeftToRight)
        else:
            self._listwidget.setFlow(QtW.QListView.Flow.TopToBottom)

    def _mgui_insert_widget(self, position: int, widget: Widget):
        item = QtW.QListWidgetItem(self._listwidget)
        item.setSizeHint(widget.native.sizeHint())
        self._listwidget.insertItem(position, item)
        self._listwidget.setItemWidget(item, widget.native)

    def _mgui_remove_widget(self, widget: Widget):
        for i in range(self._listwidget.count()):
            item = self._listwidget.item(i)
            w = self._listwidget.itemWidget(item)
            if widget.native is w:
                self._listwidget.removeItemWidget(item)
                self._listwidget.takeItem(i)
                break
        else:
            raise ValueError(f"Widget {widget} not found in the list.")

        widget.native.setParent(None)


class _SubWindowsContainer(ContainerBase):
    # The close button in QMdiArea completely deletes the sub window widget. This accident
    # can be avoided by defining a custom window flag.
    _NoCloseButtonFlag = (
        Qt.WindowType.CustomizeWindowHint
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.WindowMinMaxButtonsHint
    )

    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)
        self._mdiarea = QtW.QMdiArea(self._qwidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()

        self._layout.addWidget(self._mdiarea)
        self._qwidget.setLayout(self._layout)

    def _mgui_insert_widget(self, position: int, widget: Widget):
        # position does not have any effect
        if _is_unwrapped(widget):
            return

        sub = self._mdiarea.addSubWindow(widget.native, self._NoCloseButtonFlag)
        if _is_magicclass(widget):
            # FIXME: icon is not shown in the sub window title bar.
            qicon = widget.icon.get_qicon(widget)
            sub.setWindowIcon(qicon)

    def _mgui_remove_widget(self, widget: Widget):
        self._mdiarea.removeSubWindow(widget.native)
        widget.native.setParent(None)


class _GroupBoxContainer(ContainerBase):
    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)

        # To precisely control margins, _layout should not be set to the QGroupBox widget.
        self._groupbox = QtW.QGroupBox(self._qwidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()

        self._inner_qwidget = QtW.QWidget(self._groupbox)
        self._inner_qwidget.setLayout(self._layout)
        self._groupbox.setLayout(QtW.QHBoxLayout())
        self._groupbox.layout().addWidget(self._inner_qwidget)

        self._qwidget.setLayout(QtW.QVBoxLayout())
        self._qwidget.layout().addWidget(self._groupbox)
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)

    def _set_title(self, title: str):
        self._groupbox.setTitle(title)


class _FrameContainer(_GroupBoxContainer):
    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        super().__init__(layout=layout)
        self._groupbox.setTitle("")


class _SizeGrip(QtW.QSizeGrip):
    def __init__(self, parent: QtW.QWidget) -> None:
        super().__init__(parent)
        self.setFixedHeight(12)
        self._last_pos: QtCore.QPoint | None = None
        self._y_resizable = True
        self._x_resizable = True

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.LeftButton:
            self._last_pos = a0.globalPos()

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._last_pos = None

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if self._last_pos is not None:
            pos = a0.globalPos()
            dx = pos.x() - self._last_pos.x()
            dy = pos.y() - self._last_pos.y()
            parent = self.parentWidget()
            width = parent.width()
            height = parent.height()
            if self._x_resizable:
                if width + dx > 20:
                    width += dx
                parent.setFixedWidth(width)
            if self._y_resizable:
                if height + dy > 20:
                    height += dy
                parent.setFixedHeight(height)
            self._last_pos = pos
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        return None

    def moveEvent(self, ev: QtGui.QMoveEvent) -> None:
        # to avoid changing the size grip icon
        return QtW.QWidget.moveEvent(self, ev)


class _ResizableContainer(ContainerBase):
    def __init__(self, layout="vertical", scrollable: bool = False, **kwargs):
        QBaseWidget.__init__(self, QtW.QWidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
            self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self._layout = QtW.QVBoxLayout()
            self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._inner_qwidget = QtW.QWidget(self._qwidget)
        self._inner_qwidget.setLayout(self._layout)

        self._qwidget.setLayout(QtW.QVBoxLayout())
        _size_grip = _SizeGrip(self._qwidget)
        self._qwidget.layout().addWidget(self._inner_qwidget)
        self._qwidget.layout().addWidget(
            _size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight
        )
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)
        self._qwidget.layout().setSpacing(0)
        self._size_grip = _size_grip


def _is_unwrapped(widget: Widget) -> bool:
    if widget.widget_type == "PushButtonPlus":
        if getattr(widget, "_unwrapped", False):
            return True
    return False


# Container Widgets


@wrap_container(base=_Splitter)
class SplitterContainer(ContainerWidget[_W]):
    """A Container equipped with splitter"""


@wrap_container(base=_ToolBox)
class ToolBoxContainer(ContainerWidget[_W]):
    """A Tool box Widget."""

    @property
    def current_index(self):
        return self.native.currentIndex()

    @current_index.setter
    def current_index(self, index: int):
        self.native.setCurrentIndex(index)


@wrap_container(base=_Tab)
class TabbedContainer(ContainerWidget[_W]):
    """A tab categorized Container Widget."""

    @property
    def native_tab_widget(self) -> QtW.QTabWidget:
        return self._widget._tab_widget

    @property
    def current_index(self):
        return self.native_tab_widget.currentIndex()

    @current_index.setter
    def current_index(self, index: int):
        self.native_tab_widget.setCurrentIndex(index)


@wrap_container(base=_Stack)
class StackedContainer(ContainerWidget[_W]):
    """A stacked Container Widget"""

    @property
    def native_stacked_widget(self) -> QtW.QStackedWidget:
        return self._widget._stacked_widget

    @property
    def current_index(self):
        return self.native_stacked_widget.currentIndex()

    @current_index.setter
    def current_index(self, index: int):
        self.native_stacked_widget.setCurrentIndex(index)


@wrap_container(base=_ScrollableContainer, additionals=["x_enabled", "y_enabled"])
class ScrollableContainer(ContainerWidget[_W]):
    """A scrollable Container Widget."""

    @property
    def x_enabled(self):
        """Whether the widget is scrollable in x direction."""
        return self._widget.x_scrollable()

    @x_enabled.setter
    def x_enabled(self, value: bool):
        self._widget.set_x_scrollable(value)

    @property
    def y_enabled(self):
        """Whether the widget is scrollable in y direction."""
        return self._widget.y_scrollable()

    @y_enabled.setter
    def y_enabled(self, value: bool):
        self._widget.set_y_scrollable(value)


@wrap_container(base=_DraggableContainer)
class DraggableContainer(ContainerWidget[_W]):
    """A draggable Container Widget."""


@wrap_container(base=_ButtonContainer, additionals=["text"])
class ButtonContainer(ContainerWidget[_W]):
    """A Container Widget hidden in a button."""

    @property
    def text(self):
        """The text of the button."""
        return self._widget._qwidget.text()

    @text.setter
    def text(self, text: str):
        self._widget._qwidget.setText(text)


@wrap_container(base=_VCollapsibleContainer, additionals=["text", "collapsed"])
class CollapsibleContainer(ContainerWidget[_W]):
    """A collapsible Container Widget."""

    @property
    def text(self):
        return self._widget._expand_btn.text()

    @text.setter
    def text(self, text: str):
        self._widget._expand_btn.setText(text)

    @property
    def collapsed(self) -> bool:
        return self._widget.collapsed

    @collapsed.setter
    def collapsed(self, value: bool):
        if value:
            self._widget._collapse()
        else:
            self._widget._expand()


@wrap_container(base=_HCollapsibleContainer, additionals=["collapsed"])
class HCollapsibleContainer(ContainerWidget[_W]):
    """A collapsible Container Widget."""

    @property
    def collapsed(self) -> bool:
        return self._widget.collapsed

    @collapsed.setter
    def collapsed(self, value: bool):
        if value:
            self._widget._collapse()
        else:
            self._widget._expand()


@wrap_container(base=_ListContainer)
class ListContainer(ContainerWidget[_W]):
    """A Container Widget that support drag and drop."""

    def _post_init(self):
        self._widget._listwidget.model().rowsMoved.connect(self._drag_and_drop_happened)
        return super()._post_init()

    def _drag_and_drop_happened(self, e=None):
        """Sort widget list when item drag/drop happens."""
        l = []
        for i in range(self._widget._listwidget.count()):
            item = self._widget._listwidget.item(i)
            w = self._widget._listwidget.itemWidget(item)

            for widget in self._list:
                # if widget is a _LabeledWidget, inserted widget item will
                # be the parent of the widget in "_list".
                if widget.native is w or widget.native.parent() is w:
                    l.append(widget)
                    break

        self._list = l

    @property
    def current_index(self):
        return self._widget._listwidget.currentRow()

    @current_index.setter
    def current_index(self, index: int):
        self._widget._listwidget.setCurrentRow(index)


@wrap_container(base=_SubWindowsContainer)
class SubWindowsContainer(ContainerWidget[_W]):
    """A window-in-window container"""


@wrap_container(base=_GroupBoxContainer)
class GroupBoxContainer(ContainerWidget[_W]):
    """A QGroupBox like container"""

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value
        self._widget._set_title(value.replace("_", " "))


@wrap_container(base=_FrameContainer)
class FrameContainer(ContainerWidget[_W]):
    """A QGroupBox like container without title."""


@wrap_container(base=_ResizableContainer, additionals=["x_enabled", "y_enabled"])
class ResizableContainer(ContainerWidget[_W]):
    """A resizable Container Widget."""

    @property
    def x_enabled(self):
        """Whether the widget is resizable in x direction."""
        return self._widget._size_grip._x_resizable

    @x_enabled.setter
    def x_enabled(self, value: bool):
        self._widget._size_grip._x_resizable = value

    @property
    def y_enabled(self):
        """Whether the widget is resizable in y direction."""
        return self._widget._size_grip._y_resizable

    @y_enabled.setter
    def y_enabled(self, value: bool):
        self._widget._size_grip._y_resizable = value


def _is_magicclass(widget) -> TypeGuard[BaseGui]:
    from magicclass._gui import BaseGui

    return isinstance(widget, BaseGui)
