"""
ListWidget is a QListWidget wrapper class. This widget can contain any Python objects as list items.

.. code-block:: python

    from magicclass.widgets import ListWidget

    listwidget = ListWidget()
    
    # You can add any objects
    listwidget.append("abc")
    listwidget.append(np.arange(5))

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

.. code-block:: python

    @listwidget.register_delegate(np.ndarray)
    def _(item):
        # This function should return how ndarray will be displayed.
        return f"Array with shape {item.shape}"
    
    @listwidget.register_contextmenu(np.ndarray)
    def Plot(item, i):
        '''Function documentation will be the tooltip.'''
        plt.plot(item)
        plt.show()
    
"""

from __future__ import annotations
from typing import Any
from collections.abc import MutableSequence
from qtpy.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView

from .object import BaseWidget, ContextMenuMixin, PyObjectBound
    
class ListWidget(BaseWidget, MutableSequence):
    def __init__(self, value=None, dragdrop: bool = True, **kwargs):
        super().__init__(**kwargs)
        self._listwidget = PyListWidget(self.native)
        self._listwidget.setParentWidget(self)
        self.set_widget(self._listwidget)
        
        @self._listwidget.itemDoubleClicked.connect
        def _(item: PyListWidgetItem):
            type_ = type(item.obj)
            callbacks = self._callbacks.get(type_, [])
            self.running = True
            try:
                for callback in callbacks:
                    try:
                        callback(item.obj, self._listwidget.row(item))
                    except TypeError:
                        callback(item.obj)
            finally:
                self.running = False
        
        if dragdrop:
            self._listwidget.setAcceptDrops(True)
            self._listwidget.setDragEnabled(True)
            self._listwidget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        if value is not None:
            for v in value:
                self.append(v)
        
    def __len__(self) -> int:
        return self._listwidget.count()
    
    @property
    def value(self) -> list[Any]:
        return [self._listwidget.item(i).obj for i in range(len(self))]
            
    def insert(self, i: int, obj: Any):
        """
        Insert any item to the list.
        """
        name = self._delegates.get(type(obj), str)(obj)
        item = PyListWidgetItem(self._listwidget, obj=obj, name=name)
        self._listwidget.insertItem(i, item)
        
    def __getitem__(self, i: int) -> Any:
        """
        Get i-th python object.
        """        
        return self._listwidget.item(i).obj
    
    def __setitem__(self, i: int, obj: Any):
        self._listwidget.takeItem(i)
        self.insert(i, obj)
    
    def __delitem__(self, i: int):
        self._listwidget.takeItem(i)

    def clear(self):
        """
        Clear all the items.
        """
        self._listwidget.clear()
    


class PyListWidget(ContextMenuMixin, QListWidget):
    def item(self, row: int) -> PyListWidgetItem:
        return super().item(row)
    
    def itemAt(self, *p) -> PyListWidgetItem:
        return super().itemAt(*p)
        
    def __init__(self, parent: None) -> None:
        super().__init__(parent=parent)
        self.setContextMenu()
        

class PyListWidgetItem(PyObjectBound, QListWidgetItem):
    def __init__(self, parent: QListWidget=None, obj=None, name=None):
        super().__init__(parent)
        self.setObject(obj, name)
