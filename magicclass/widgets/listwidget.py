"""
ListWidget is a QListWidget wrapper class. This widget can contain any Python objects as list items.

.. code-block:: python

    from magicclass.widgets import ListWidget

    listwidget = ListWidget()
    
    # You can add any objects
    listwidget.add_item("abc")
    listwidget.add_item(np.arange(5))

You can dispatch double click callbacks depending on the type of contents.

.. code-block:: python

    @listwidget.register_callback(str)
    def _(item, i):
        # This function will be called when the item "abc" is double-clicked.
        print(item)
    
    @listwidget.register_callback(np.ndarray)
    def _(item, i):
        # This function will be called when the item np.arange(5) is double-clicked.
        print(item.tolist())

In a similar way, you can dispatch display method and context menu.


"""

from __future__ import annotations
from functools import wraps
from typing import Callable, Any
from collections import defaultdict
from qtpy.QtWidgets import QLabel, QListWidget, QListWidgetItem, QAbstractItemView, QMenu, QAction
from qtpy.QtCore import Qt
from .utils import FrozenContainer

_Callback = Callable[[Any, int], Any]
    
class ListWidget(FrozenContainer):
    def __init__(self, dragdrop:bool=True, **kwargs):
        super().__init__(labels=False, **kwargs)
        self._listwidget = PyListWidget(self.native)
        self._listwidget.setParentContainer(self)
        self._title = QLabel(self.native)
        self._title.setText(self.name)
        self._title.setAlignment(Qt.AlignCenter)
        self.set_widget(self._title)
        self.set_widget(self._listwidget)
        
        self._callbacks: defaultdict[type, list[_Callback]] = defaultdict(list)
        self._delegates: dict[type, Callable[[Any], str]] = dict()
        self._contextmenu: defaultdict[type, list[_Callback]] = defaultdict(list)
        
        @self._listwidget.itemDoubleClicked.connect
        def _(item: PyListWidgetItem):
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
    
    @property
    def title(self) -> str:
        return self._title.text()
    
    @title.setter
    def title(self, text: str):
        self._title.setText(text)
        
    def add_item(self, obj: Any):
        """
        Append any item to the list.
        """
        self.insert_item(self.nitems, obj)
    
    def insert_item(self, i: int, obj: Any):
        """
        Insert any item to the list.
        """
        name = self._delegates.get(type(obj), str)(obj)
        item = PyListWidgetItem(self._listwidget, obj=obj, name=name)
        self._listwidget.insertItem(i, item)
    
    def pop_item(self, i: int) -> Any:
        """
        Pop item at an index.
        """
        self._listwidget.takeItem(i)
        return None

    def clear(self):
        """
        Clear all the items.
        """
        self._listwidget.clear()
    
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


class PyListWidget(QListWidget):
    def item(self, row: int) -> PyListWidgetItem:
        return super().item(row)
    
    def itemAt(self, *p) -> PyListWidgetItem:
        return super().itemAt(*p)
        
    def __init__(self, parent: None) -> None:
        super().__init__(parent=parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)
        
    def setParentContainer(self, container: ListWidget) -> None:
        self._parent = container
        return None
    
    def contextMenu(self, point):
        menu = QMenu(self)
        item = self.itemAt(point)
        type_ = type(item.obj)
        menus = self._parent._contextmenu.get(type_, [])
        for f in menus:
            text = f.__name__.replace("_", " ")
            action = QAction(text, self)
            pfunc = partial_event(f, item.obj, self.row(item))
            action.triggered.connect(pfunc)
            menu.addAction(action)
         
        menu.exec_(self.mapToGlobal(point))

def partial_event(f, *args):
    @wraps(f)
    def _func(e):
        return f(*args)
    return _func

class PyListWidgetItem(QListWidgetItem):
    def __init__(self, parent:QListWidget=None, obj=None, name=None):
        super().__init__(parent)
        if obj is not None:
            self.obj = obj
        if name is None:
            self.setText(str(obj))
        else:
            self.setText(name)
