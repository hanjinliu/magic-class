from __future__ import annotations
from functools import wraps
from typing import Callable, Any, Iterable
from collections import defaultdict
from collections.abc import MutableMapping
from qtpy.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QMenu, QAction
from qtpy.QtCore import Qt
from .utils import FreeWidget
from ..utils import extract_tooltip


_Callback = Callable[[Any, int], Any]

class DictWidget(FreeWidget, MutableMapping):
    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)
        
        self._tablewidget = PyTableWidget(self.native)
        self._tablewidget.setParentWidget(self)
        self._dict: dict[str, int] = {} # mapping from key to row
        self._title = QLabel(self.native)
        self._title.setText(self.name)
        self._title.setAlignment(Qt.AlignCenter)
        self.running = False
        self.set_widget(self._title)
        self.set_widget(self._tablewidget)
        
        self._callbacks: defaultdict[type, list[_Callback]] = defaultdict(list)
        self._delegates: dict[type, Callable[[Any], str]] = dict()
        self._contextmenu: defaultdict[type, list[_Callback]] = defaultdict(list)
        
        
        @self._tablewidget.itemDoubleClicked.connect
        def _(item: PyTableWidgetItem):
            type_ = type(item.obj)
            callbacks = self._callbacks.get(type_, [])
            self.running = True
            try:
                for callback in callbacks:
                    try:
                        callback(item.obj, self._tablewidget.row(1, item))
                    except TypeError:
                        callback(item.obj)
            finally:
                self.running = False
        
        if value is not None:
            self.update(dict(value))
            
    def __len__(self) -> int:
        return self._tablewidget.rowCount()
    
    @property
    def value(self) -> list[Any]:
        return {k: self._tablewidget.item(row, 1) for k, row in self._dict}
    
    @property
    def title(self) -> str:
        return self._title.text()
    
    @title.setter
    def title(self, text: str):
        self._title.setText(text)
    
    def __getitem__(self, k: str) -> Any:
        row = self._dict[k]
        return self._tablewidget.item(row, 1).obj
    
    def __setitem__(self, k: str, obj: Any) -> None:
        if not isinstance(k, str):
            raise ValueError("Can only use str type as keys.")
        
        if k in self._dict.keys():
            row = self._dict[k]
        else:
            row = len(self)
            self._dict[k] = row
            self._tablewidget.insertRow(row)
            if row == 0:
                self._tablewidget.insertColumn(0)
                self._tablewidget.setHorizontalHeaderItem(0, QTableWidgetItem("key"))
                self._tablewidget.insertColumn(1)
                self._tablewidget.setHorizontalHeaderItem(1, QTableWidgetItem("value"))
            key_item = PyTableWidgetItem(self._tablewidget, k, k)
            self._tablewidget.setItem(row, 0, key_item)
            
        name = self._delegates.get(type(obj), str)(obj)
        value_item = PyTableWidgetItem(self._tablewidget, obj, name)
        self._tablewidget.setItem(row, 1, value_item)

    def __delitem__(self, k: str) -> None:
        row = self._dict.pop(k)
        self._tablewidget.removeRow(row)
    
    def __iter__(self) -> Iterable[str]:
        return iter(self._dict)
    
    def keys(self):
        return self._dict.keys()
    
    def values(self) -> DictValueView:
        return DictValueView(self._tablewidget)
    
    def items(self) -> DictItemView:
        return DictItemView(self._tablewidget)
    
    def update(self, d: dict[str, Any]):
        for k, v in d.items():
            self[k] = v
            
    def clear(self) -> None:
        self._tablewidget.clear()
        self._dict.clear()
    
    def pop(self, k: str):
        row = self._dict.pop(k)
        out = self._tablewidget.item(row, 1).obj
        self._tablewidget.removeRow(row)
        return out
    
    def register_callback(self, type_: type):
        """
        Register a double-click callback function for items of certain type.
        """        
        def wrapper(func: Callable):
            self._callbacks[type_].append(func)
            return func
        return wrapper
    
    def register_delegate(self, type_: type):
        """
        Register a custom display.
        """        
        def wrapper(func: Callable):
            self._delegates[type_] = func
            return func
        return wrapper
    
    def register_contextmenu(self, type_:type):
        """
        Register a custom context menu for items of certain type.
        """        
        def wrapper(func: Callable):
            self._contextmenu[type_].append(func)
            return func
        return wrapper

class PyTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        
    def item(self, row: int, column: int) -> PyTableWidgetItem:
        return super().item(row, column)
    
    def itemAt(self, *p) -> PyTableWidgetItem:
        return super().itemAt(*p)
        
    def __init__(self, parent: None) -> None:
        super().__init__(parent=parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

    
    def setParentWidget(self, listwidget: DictWidget) -> None:
        self._parent = listwidget
        return None
    
    def contextMenu(self, point):
        item = self.itemAt(point)
        if item.column() == 0:
            return
        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        type_ = type(item.obj)
        menus = self._parent._contextmenu.get(type_, [])
        for f in menus:
            text = f.__name__.replace("_", " ")
            action = QAction(text, self)
            pfunc = partial_event(f, item.obj, self.row(item))
            action.triggered.connect(pfunc)
            doc = extract_tooltip(f)
            if doc:
                action.setToolTip(doc)
            menu.addAction(action)
         
        menu.exec_(self.mapToGlobal(point))

def partial_event(f, *args):
    @wraps(f)
    def _func(e):
        return f(*args)
    return _func

class PyTableWidgetItem(QTableWidgetItem):
    def __init__(self, parent: QTableWidget=None, obj=None, name=None):
        super().__init__()
        if obj is not None:
            self.obj = obj
        if name is None:
            self.setText(str(obj))
        else:
            self.setText(name)
    
class DictValueView:
    def __init__(self, widget: PyTableWidget):
        self.widget = widget
    
    def __iter__(self):
        for row in range(self.widget.rowCount()):
            yield self.widget.item(row, 1).obj

class DictItemView:
    def __init__(self, widget: PyTableWidget):
        self.widget = widget
    
    def __iter__(self):
        for row in range(self.widget.rowCount()):
            key = self.widget.item(row, 0).text()
            value = self.widget.item(row, 1).obj
            yield key, value