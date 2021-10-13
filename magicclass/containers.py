from __future__ import annotations
from typing import TypeVar, Callable
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, Slot
from magicgui.application import use_app
from magicgui.widgets._bases import Widget
from magicgui.widgets._concrete import merge_super_sigs, ContainerWidget
from magicgui.backends._qtpy.widgets import QBaseWidget, Container as ContainerBase

C = TypeVar("C")
_ICON_EXP = "▼ "
_ICON_CLP = "▲ "

def wrap_container(
    cls: type[C] = None,
    base: type = None
) -> Callable | type[C]:
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
        self._qwidget.setContentsMargins(0, 0, 0, 0)

class _CollapsibleContainer(ContainerBase):
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
        self._btn_text = btn_text
        
        self._expanded = True
        self._qwidget.layout().setSpacing(0)
        self._qwidget.layout().setContentsMargins(0, 0, 0, 0)
        self._expand_btn = QtW.QPushButton(_ICON_EXP + self._btn_text, self._qwidget)
        self._expand_btn.setStyleSheet("text-align:left;")
        self._expand_btn.clicked.connect(self._mgui_change_expand)
        self._qwidget.layout().addWidget(self._expand_btn, 0, Qt.AlignTop)
        self._qwidget.layout().addWidget(self._inner_widget, 0, Qt.AlignTop)
        self._qwidget.setContentsMargins(0, 0, 0, 0)
    
    def _mgui_change_expand(self):
        if self._expanded:
            self._inner_widget.setMaximumHeight(0)
            self._qwidget.setFixedHeight(self._expand_btn.height())
            self._qwidget.setMaximumHeight(self._expand_btn.height())
            self._expanded = False
            self._expand_btn.setText(_ICON_CLP + self._btn_text)
        else:
            h = self._inner_widget.sizeHint().height()
            self._inner_widget.setMaximumHeight(h)
            self._qwidget.setMaximumHeight(self._expand_btn.height() + h)
            self._qwidget.setFixedHeight(self._expand_btn.height() + h)
            self._expanded = True
            self._expand_btn.setText(_ICON_EXP + self._btn_text)

@wrap_container(base=_ScrollableContainer)
class ScrollableContainer(ContainerWidget):
    """A scrollable Container Widget."""

@wrap_container(base=_CollapsibleContainer)
class CollapsibleContainer(ContainerWidget):
    """A collapsible Container Widget."""    
    
    @property
    def btn_text(self):
        return self._widget._btn_text
    
    @btn_text.setter
    def btn_text(self, text: str):
        self._widget._btn_text = text
        if self._widget._expanded:
            self._widget._expand_btn.setText(_ICON_EXP + text)
        else:
            self._widget._expand_btn.setText(_ICON_CLP + text)
            