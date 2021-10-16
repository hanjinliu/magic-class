from __future__ import annotations
from typing import TypeVar, Callable
import warnings
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from magicgui.application import use_app
from magicgui.widgets._bases import Widget
from magicgui.widgets._concrete import merge_super_sigs, ContainerWidget
from magicgui.backends._qtpy.widgets import (
    QBaseWidget, 
    Container as ContainerBase,
    MainWindow as MainWindowBase
    )

C = TypeVar("C")

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

class _Splitter(ContainerBase):
    _qwidget: QtW.QSplitter
    def __init__(self, layout="vertical"):
        QBaseWidget.__init__(self, QtW.QSplitter)
        
        if layout == "horizontal":
            self._qwidget.setOrientation(Qt.Horizontal)
        else:
            self._qwidget.setOrientation(Qt.Vertical)
    
    def _mgui_insert_widget(self, position: int, widget: Widget):
        self._qwidget.insertWidget(position, widget.native)

    
    def _mgui_remove_widget(self, widget: Widget):
        raise NotImplementedError()

    def _mgui_get_margins(self) -> tuple[int, int, int, int]:
        raise NotImplementedError()

    def _mgui_set_margins(self, margins: tuple[int, int, int, int]) -> None:
        raise NotImplementedError()
        
class _ToolBox(ContainerBase):
    _qwidget: QtW.QToolBox
    def __init__(self, layout="vertical"):
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
    _qwidget: QtW.QTabWidget
    def __init__(self, layout="vertical"):
        QBaseWidget.__init__(self, QtW.QTabWidget)
        
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()
        
        self._qwidget.setLayout(self._layout)
    
    def _mgui_insert_widget(self, position: int, widget: Widget):
        self._qwidget.insertTab(position, widget.native, widget.name)
    
    def _mgui_remove_widget(self, widget: Widget):
        for i in range(self._qwidget.count()):
            if self._qwidget.widget(i) is widget.native:
                self._qwidget.removeTab(i)
                widget.native.setParent(None)
                break
        else:
            raise ValueError(f"Widget {widget.name} not found.")


class _Stack(ContainerBase):
    _qwidget: QtW.QWidget
    def __init__(self, layout="vertical"):
        QBaseWidget.__init__(self, QtW.QWidget)
        
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()
        
        self._stacked_widget = QtW.QStackedWidget(self._qwidget)
        self._stacked_widget.setContentsMargins(0, 0, 0, 0)
        self._inner_widget = QtW.QWidget(self._qwidget)
        self._qwidget.setLayout(self._layout)
        self._layout.addWidget(self._stacked_widget)
        self._layout.addWidget(self._inner_widget)
    
    def _mgui_insert_widget(self, position: int, widget: Widget):
        self._stacked_widget.insertWidget(position, widget.native)
    
    def _mgui_remove_widget(self, widget: Widget):
        self._stacked_widget.removeWidget(widget.native)
        widget.native.setParent(None)

class _ScrollableContainer(ContainerBase):
    def __init__(self, layout="vertical"):
        QBaseWidget.__init__(self, QtW.QWidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()
            
        self._scroll_area = QtW.QScrollArea(self._qwidget)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setContentsMargins(0, 0, 0, 0)
        self._inner_widget = QtW.QWidget(self._scroll_area)
        self._inner_widget.setLayout(self._layout)
        self._scroll_area.setWidget(self._inner_widget)
        
        self._qwidget.setLayout(QtW.QHBoxLayout())
        self._qwidget.layout().addWidget(self._scroll_area)
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)

class _ButtonContainer(ContainerBase):
    def __init__(self, layout="vertical", btn_text=""):
        QBaseWidget.__init__(self, QtW.QWidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()
        
        self._qwidget = QtW.QPushButton()
        self._inner_widget = QtW.QWidget()
        self._inner_widget.setParent(self._qwidget, self._inner_widget.windowFlags())
        self._inner_widget.setLayout(self._layout)
        
        self._qwidget.setText(btn_text)
        self._qwidget.clicked.connect(lambda x: self._inner_widget.show())
        
class _CollapsibleContainer(ContainerBase):
    """
    Collapsible container.
    See https://stackoverflow.com/questions/32476006/how-to-make-an-expandable-collapsable-section-widget-in-qt.
    """    
    def __init__(self, layout="vertical", btn_text=""):
        QBaseWidget.__init__(self, QtW.QWidget)
        if layout == "horizontal":
            self._layout: QtW.QLayout = QtW.QHBoxLayout()
        else:
            self._layout = QtW.QVBoxLayout()
        
        self._qwidget = QtW.QWidget()
        self._qwidget.setLayout(QtW.QVBoxLayout())
        self._inner_widget = QtW.QWidget(self._qwidget)
        self._inner_widget.setLayout(self._layout)
        
        self._qwidget.layout().setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        
        self._expand_btn = QtW.QToolButton(self._qwidget)
        self._expand_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._expand_btn.setArrowType(Qt.ArrowType.RightArrow)
        self._expand_btn.setText(btn_text)
        self._expand_btn.setCheckable(True)
        self._expand_btn.setChecked(False)
        self._expand_btn.setStyleSheet("QToolButton { border: none; text-align: left;}")
        self._expand_btn.clicked.connect(self._mgui_change_expand)
        self._mgui_change_expand()
        
        self._qwidget.layout().addWidget(self._expand_btn, 0, Qt.AlignTop)
        self._qwidget.layout().addWidget(self._inner_widget, 0, Qt.AlignTop)
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)
    
    def _mgui_change_expand(self):
        if not self._expand_btn.isChecked():
            self._inner_widget.setMaximumHeight(0)
            w = self._qwidget.width()
            h = max(self._expand_btn.sizeHint().height(), 30)
            self._qwidget.resize(w, h)
            self._expand_btn.setArrowType(Qt.ArrowType.RightArrow)
        else:
            h = self._inner_widget.sizeHint().height()
            w = self._qwidget.width()
            self._inner_widget.setMaximumHeight(h)
            self._qwidget.resize(w, self._expand_btn.sizeHint().height() + h)
            self._expand_btn.setArrowType(Qt.ArrowType.DownArrow)


@wrap_container(base=_Splitter)
class SplitterContainer(ContainerWidget):
    """A Container equipped with splitter"""
    
@wrap_container(base=_ToolBox)
class ToolBox(ContainerWidget):
    """A Tool box Widget."""

@wrap_container(base=_Tab)
class TabbedContainer(ContainerWidget):
    """A tab categorized Container Widget."""
    
    @property
    def current_index(self):
        return self.native.currentIndex()
    
    @current_index.setter
    def current_index(self, index: int):
        self.native.setCurrentIndex(index)

@wrap_container(base=_Stack)
class StackedContainer(ContainerWidget):
    """A stacked Container Widget"""
    
    @property
    def current_index(self):
        return self._widget._stacked_widget.currentIndex()
    
    @current_index.setter
    def current_index(self, index: int):
        self._widget._stacked_widget.setCurrentIndex(index)
        

@wrap_container(base=_ScrollableContainer)
class ScrollableContainer(ContainerWidget):
    """A scrollable Container Widget."""

@wrap_container(base=_ButtonContainer)
class ButtonContainer(ContainerWidget):
    """A Container Widget hidden in a button."""    
    
    @property
    def btn_text(self):
        return self._widget._qwidget.text()

    @btn_text.setter
    def btn_text(self, text: str):
        self._widget._qwidget.setText(text)

@wrap_container(base=_CollapsibleContainer)
class CollapsibleContainer(ContainerWidget):
    """A collapsible Container Widget."""    
    
    @property
    def btn_text(self):
        return self._widget._expand_btn.text()

    @btn_text.setter
    def btn_text(self, text: str):
        self._widget._expand_btn.setText(text)
