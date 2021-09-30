from __future__ import annotations
from typing import Any, Callable, Iterable, TypeVar, overload
import inspect
from collections import defaultdict
from PyQt5.QtWidgets import QWidget
from qtpy.QtWidgets import (QFrame, QLabel, QMessageBox, QPushButton, QGridLayout, QTextEdit, 
                            QListWidget, QListWidgetItem, QAbstractItemView)
from qtpy.QtGui import QIcon, QFont
from qtpy.QtCore import QSize, Qt
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.colors import to_rgb
from magicgui.widgets import create_widget, Container, PushButton, TextEdit
from magicgui.widgets._bases.value_widget import UNSET

# Here's some widgets that doesn't seem needed for magicgui but commonly used in magicclass.

__all__ = ["raise_error_msg", "Figure", "Separator", "ListEdit", "Logger", "CheckButton", "PushButtonPlus"]

_V = TypeVar("_V")

def raise_error_msg(parent, title:str="Error", msg:str="error"):
    QMessageBox.critical(parent, title, msg, QMessageBox.Ok)
    return None

class FrozenContainer(Container):
    """
    Non-editable container. 
    This class is useful to add QWidget into Container. If a QWidget is added via 
    Container.layout(), it will be invisible from Container. We can solve this
    problem by "wrapping" a QWidget with a Container.
    """    
    def insert(self, key, value):
        raise AttributeError(f"Cannot insert widget to {self.__class__.__name__}")
    
    def set_widget(self, widget:QWidget):
        self.native.layout().addWidget(widget)
        self.margins = (0, 0, 0, 0)
        return None

class Figure(FrozenContainer):
    def __init__(self, nrows:int=1, ncols:int=1, figsize=(4, 3), layout:str="vertical", **kwargs):
        backend = mpl.get_backend()
        mpl.use("Agg")
        fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
        mpl.use(backend)
        
        super().__init__(layout=layout, labels=False, **kwargs)
        canvas = FigureCanvas(fig)
        self.set_widget(canvas)
        self.figure = fig
        self.min_height = 40
        
    def draw(self):
        self.figure.canvas.draw()
    
    @property
    def axes(self):
        return self.figure.axes
    
    @property
    def ax(self):
        return self.axes[0]
        
class Separator(FrozenContainer):
    # TODO: not shown in napari
    def __init__(self, orientation="horizontal", text:str="", name:str=""):
        super().__init__(layout=orientation, labels=False, name=name)
        main = QFrame(parent=self.native)
        main.setLayout(QGridLayout())
        
        line = QFrame(parent=main)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setContentsMargins(0, 0, 0, 0)
        main.layout().addWidget(line)
        
        if text:
            label = QLabel(text, parent=main)
            label.setContentsMargins(0, 0, 0, 0)
            label.setAlignment(Qt.AlignRight)
            main.layout().addWidget(label)
        
        self.set_widget(main)

class ListEdit(Container):
    def __init__(
        self,
        value: Iterable[_V] = UNSET,
        annotation: type = None, # such as int, str, ...
        layout: str = "horizontal",
        options: dict = None,
        **kwargs,
    ):
        if value is not UNSET:
            types = set(type(a) for a in value)
            if len(types) == 1:
                self._type = types.pop()
            else:
                self._type = str
                
        else:
            self._type = annotation if annotation is not inspect._empty else str
            value = []
            
        self.child_options = options or {}
        
        super().__init__(layout=layout, labels=False, **kwargs)
        
        button_plus = PushButton(text="+")
        button_plus.changed.connect(lambda e: self.append_new())
        
        button_minus = PushButton(text="-")
        button_minus.changed.connect(self.delete_last)
        
        self.append(button_plus)
        self.append(button_minus)
        
        for a in value:
            self.append_new(a)
    
    def append_new(self, value=UNSET):
        i = len(self)-2
        widget = create_widget(value=value, annotation=self._type, name=f"value_{i}",
                               options=self.child_options)
        self.insert(i, widget)
    
    def delete_last(self, value):
        try:
            self.pop(-3)
        except IndexError:
            pass
    
    @property
    def value(self):
        return ListDataView(self)

    @value.setter
    def value(self, vals:Iterable[_V]):
        for i in reversed(range(len(self))):
            if not isinstance(self[i], PushButton):
                self.pop(i)
        for v in vals:
            self.append_new(v)        
    
class ListDataView:
    def __init__(self, widget: ListEdit):
        self.widget = list(filter(lambda x: not isinstance(x, PushButton), widget))
    
    def __repr__(self):
        return repr([w.value for w in self.widget])
    
    def __str__(self):
        return str([w.value for w in self.widget])
    
    def __len__(self):
        return len(self.widget)
    
    @overload
    def __getitem__(self, i:int) -> _V: ...
    @overload
    def __getitem__(self, key:slice) -> list[_V]: ...
    @overload
    def __setitem__(self, key:int, value:_V) -> None: ...
    @overload
    def __setitem__(self, key:slice, value:_V|Iterable[_V]) -> None: ...
    
    def __getitem__(self, key:int|slice):
        if isinstance(key, int):
            return self.widget[key].value
        else:
            return [w.value for w in self.widget[key]]
    
    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.widget[key].value = value
        else:
            if isinstance(value, type(self.widget.value[0])):
                for w in self.widget[key]:
                    w.value = value
            else:
                for w, v in zip(self.widget[key], value):
                    w.value = v
                    
class TupleEdit(Container):
    def __init__(
        self,
        value: Iterable[_V] = UNSET,
        annotation: type = None, # such as int, str, ...
        layout: str = "horizontal",
        options: dict = None,
        **kwargs,
    ):
            
        if value is not UNSET:
            types = set(type(a) for a in value)
            if len(types) == 1:
                self._type = types.pop()
            else:
                self._type = str
                
        else:
            self._type = annotation if annotation is not inspect._empty else str
            value = (UNSET, UNSET)

        super().__init__(layout=layout, labels=False, **kwargs)
        self.child_options = options or {}
        
        for a in value:
            self.append_new(a)

    def append_new(self, value=UNSET):
        i = len(self)
        widget = create_widget(value=value, annotation=self._type, name=f"value_{i}", 
                               options=self.child_options)
        self.insert(i, widget)
            
    @property        
    def value(self):
        return tuple(w.value for w in self)

    @value.setter
    def value(self, vals:Iterable[_V]):
        if len(vals) != len(self):
            raise ValueError("Length of tuple does not match.")
        for w, v in zip(self, vals):
            w.value = v
    
class Logger(TextEdit):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.native: QTextEdit
        self.read_only = True
        self.native.setFont(QFont("Consolas"))
        self.n_line = 0
        
    def append(self, text:str|Iterable[str]):
        if isinstance(text, str):
            self.native.append(text)
            vbar = self.native.verticalScrollBar()
            vbar.setValue(vbar.maximum())
            self.n_line += 1
        else:
            for txt in text:
                self.append(txt)
        return None
    
class ListWidget(FrozenContainer):
    def __init__(self, dragdrop:bool=True, **kwargs):
        super().__init__(labels=False, **kwargs)
        self._listwidget = QListWidget(self.native)
        self.set_widget(self._listwidget)
        self._callbacks: defaultdict[type, list[Callable[[Any, int], Any]]] = defaultdict(list)
        self._delegates: dict[type, Callable[[Any], str]] = dict()
        @self._listwidget.itemDoubleClicked.connect
        def _(item):
            type_ = type(item.obj)
            callbacks = self._callbacks.get(type_, [])
            for callback in callbacks:
                try:
                    callback(item.obj, self._listwidget.row(item))
                except TypeError:
                    callback(item.obj)
        
        if dragdrop:
            self._listwidget.setAcceptDrops(True)
            self._listwidget.setDragEnabled(True)
            self._listwidget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
    
    @property
    def nitems(self) -> int:
        return self._listwidget.count()
    
    @property
    def value(self) -> list[Any]:
        return [self._listwidget.item(i).obj for i in range(self.nitems)]
        
    def add_item(self, obj: Any):
        self.insert_item(self.nitems, obj)
    
    def insert_item(self, i: int, obj: Any):
        name = self._delegates.get(type(obj), str)(obj)
        item = PyListWidgetItem(self._listwidget, obj=obj, name=name)
        self._listwidget.insertItem(i, item)
    
    def pop_item(self, i: int) -> Any:
        item = self._listwidget.item(i)
        obj = item.obj
        self._listwidget.removeItemWidget(item)
        return obj

    def clear(self):
        self._listwidget.clear()
    
    def register_callback(self, type_: type):
        def wrapper(func: Callable):
            self._callbacks[type_].append(func)
            return func
        return wrapper
    
    def register_delegate(self, type_: type):
        def wrapper(func: Callable):
            self._delegates[type_] = func
            return func
        return wrapper
    

class PyListWidgetItem(QListWidgetItem):
    def __init__(self, parent:QListWidget=None, obj=None, name=None):
        super().__init__(parent)
        if obj is not None:
            self.obj = obj
        if name is None:
            self.setText(str(obj))
        else:
            self.setText(name)

class CheckButton(PushButton):
    def __init__(self, text:str|None=None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native.setCheckable(True)

class PushButtonPlus(PushButton):
    def __init__(self, text:str|None=None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native: QPushButton
        self._icon_path = None
        self.mgui = None
    
    @property
    def background_color(self):
        return self.native.palette().button().color().getRgb()
    
    @background_color.setter
    def background_color(self, color:str|Iterable[float]):
        # TODO: In napari stylesheet is somehow overwritten and all the colored button will be "flat" 
        # (not shadowed when clicked/toggled)
        stylesheet = self.native.styleSheet()
        d = _stylesheet_to_dict(stylesheet)
        d.update({"background-color": _to_rgb(color)})
        stylesheet = _dict_to_stylesheet(d)
        self.native.setStyleSheet(stylesheet)
        
    @property
    def icon_path(self):
        return self._icon_path
    
    @icon_path.setter
    def icon_path(self, path:str):
        icon = QIcon(path)
        self.native.setIcon(icon)
    
    @property
    def icon_size(self):
        qsize = self.native.iconSize()
        return qsize.width(), qsize.height()
        
    @icon_size.setter
    def icon_size(self, size:tuple[int, int]):
        w, h = size
        self.native.setIconSize(QSize(w, h))
    
    @property
    def font_size(self):
        return self.native.font().pointSize()
    
    @font_size.setter
    def font_size(self, size:int):
        font = self.native.font()
        font.setPointSize(size)
        self.native.setFont(font)
        
    @property
    def font_color(self):
        return self.native.palette().text().color().getRgb()
    
    @font_color.setter
    def font_color(self, color:str|Iterable[float]):
        stylesheet = self.native.styleSheet()
        d = _stylesheet_to_dict(stylesheet)
        d.update({"color": _to_rgb(color)})
        stylesheet = _dict_to_stylesheet(d)
        self.native.setStyleSheet(stylesheet)

    @property
    def font_family(self):
        return self.native.font().family()
    
    @font_family.setter
    def font_family(self, family:str):
        font = self.native.font()
        font.setFamily(family)
        self.native.setFont(font)
    
    def from_options(self, options:dict[str]|Callable):
        if callable(options):
            try:
                options = options.__signature__.caller_options
            except AttributeError:
                return None
                
        for k, v in options.items():
            v = options.get(k, None)
            if v is not None:
                setattr(self, k, v)
        return None

def _to_rgb(color):
    if isinstance(color, str):
        color = to_rgb(color)
    rgb = ",".join(str(max(min(int(c*255), 255), 0)) for c in color)
    return f"rgb({rgb})"

def _stylesheet_to_dict(stylesheet:str):
    if stylesheet == "":
        return {}
    lines = stylesheet.split(";")
    d = dict()
    for line in lines:
        k, v = line.split(":")
        d[k.strip()] = v.strip()
    return d

def _dict_to_stylesheet(d:dict):
    stylesheet = [f"{k}: {v}" for k, v in d.items()]
    return ";".join(stylesheet)