from __future__ import annotations

from typing import Any, TypeVar, Callable
import warnings
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt, QEvent, QSize

from magicgui.application import use_app
from magicgui.widgets import Widget
from magicgui.backends._qtpy.widgets import (
    QBaseWidget,
    Container as ContainerBase,
    MainWindow as MainWindowBase,
)
from magicclass._magicgui_compat import ContainerWidget

from .utils import merge_super_sigs

# Container variations that is useful in making GUI designs better.

C = TypeVar("C", bound=ContainerWidget)


def wrap_container(cls: type[C] = None, base: type = None) -> Callable | type[C]:
    """
    Provide a wrapper for a new container widget with a new protocol.
    """

    def wrapper(cls) -> type[Widget]:
        def __init__(self, **kwargs):
            app = use_app()
            assert app.native
            kwargs["widget_type"] = base
            super(cls, self).__init__(**kwargs)

        cls.__init__ = __init__
        cls = merge_super_sigs(cls)
        return cls

    return wrapper(cls) if cls else wrapper


def _btn_text_warning():
    msg = "'btn_text' is deprecated and will be removed soon. Please use 'text'."
    warnings.warn(msg, DeprecationWarning)


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
        self._tab_widget.insertTab(position, widget.native, widget.name)

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


class _WheelDisabledScrollArea(QtW.QScrollArea):
    def eventFilter(self, source, event: QEvent):
        if event.type() == QEvent.Type.Wheel:
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
        self._mdiarea.addSubWindow(widget.native, self._NoCloseButtonFlag)

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


# Container Widgets


@wrap_container(base=_Splitter)
class SplitterContainer(ContainerWidget):
    """A Container equipped with splitter"""


@wrap_container(base=_ToolBox)
class ToolBoxContainer(ContainerWidget):
    """A Tool box Widget."""

    @property
    def current_index(self):
        return self.native.currentIndex()

    @current_index.setter
    def current_index(self, index: int):
        self.native.setCurrentIndex(index)


@wrap_container(base=_Tab)
class TabbedContainer(ContainerWidget):
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
class StackedContainer(ContainerWidget):
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


@wrap_container(base=_ScrollableContainer)
class ScrollableContainer(ContainerWidget):
    """A scrollable Container Widget."""


@wrap_container(base=_DraggableContainer)
class DraggableContainer(ContainerWidget):
    """A draggable Container Widget."""


@wrap_container(base=_ButtonContainer)
class ButtonContainer(ContainerWidget):
    """A Container Widget hidden in a button."""

    @property
    def btn_text(self):
        _btn_text_warning()
        return self._widget._qwidget.text()

    @btn_text.setter
    def btn_text(self, text: str):
        _btn_text_warning()
        self._widget._qwidget.setText(text)

    @property
    def text(self):
        return self._widget._qwidget.text()

    @text.setter
    def text(self, text: str):
        self._widget._qwidget.setText(text)


@wrap_container(base=_VCollapsibleContainer)
class CollapsibleContainer(ContainerWidget):
    """A collapsible Container Widget."""

    @property
    def btn_text(self):
        _btn_text_warning()
        return self._widget._expand_btn.text()

    @btn_text.setter
    def btn_text(self, text: str):
        _btn_text_warning()
        self._widget._expand_btn.setText(text)

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


@wrap_container(base=_HCollapsibleContainer)
class HCollapsibleContainer(ContainerWidget):
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
class ListContainer(ContainerWidget):
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
class SubWindowsContainer(ContainerWidget):
    """A window-in-window container"""


@wrap_container(base=_GroupBoxContainer)
class GroupBoxContainer(ContainerWidget):
    """A QGroupBox like container"""

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value
        self._widget._set_title(value.replace("_", " "))


@wrap_container(base=_FrameContainer)
class FrameContainer(ContainerWidget):
    """A QGroupBox like container without title."""
