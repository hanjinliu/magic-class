from __future__ import annotations
from typing import Any, Iterable, MutableSequence
from qtpy.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView

from .object import BaseWidget, ContextMenuMixin, PyObjectBound


class ListWidget(BaseWidget, MutableSequence):
    def __init__(self, value: Iterable[Any] = None, dragdrop: bool = True, **kwargs):
        """
        A widget composed of a list of items. This widget behaves very similar to Python
        list so that you can append, insert, pop or do any indexing.

        Parameters
        ----------
        value : Iterable, optional
            Initial value of the list widget. Any iterable object that can be passed to
            Python list.
        dragdrop : bool, default is True
            Allow drag and drop of list contents.
        """
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
            self._listwidget.setDragDropMode(
                QAbstractItemView.DragDropMode.InternalMove
            )

        if value is not None:
            for v in value:
                self.append(v)

    def __len__(self) -> int:
        """
        Length of widget contents.
        """
        return self._listwidget.count()

    @property
    def value(self) -> list[Any]:
        """
        Get all the contents as a Python list.

        Returns
        -------
        list
            Contents of the list widget.
        """
        return [self._listwidget.item(i).obj for i in range(len(self))]

    def insert(self, i: int, obj: Any):
        """
        Insert object of any type to the list.
        """
        name = self._delegates.get(type(obj), str)(obj)
        tooltip = self._tooltip.get(type(obj), str)(obj)
        item = PyListWidgetItem(self._listwidget, obj=obj, name=name)
        item.setToolTip(tooltip)
        self._listwidget.insertItem(i, item)

    def __getitem__(self, i: int) -> Any:
        """
        Get i-th Python object (not widget item object!).
        """
        return self._listwidget.item(i).obj

    def __setitem__(self, i: int, obj: Any):
        """
        Set i-th Python object.
        """
        self._listwidget.takeItem(i)
        self.insert(i, obj)

    def __delitem__(self, i: int):
        """
        Delete i-th Python object from the list widget.
        """
        self._listwidget.takeItem(i)

    def clear(self):
        """
        Clear all the items.
        """
        self._listwidget.clear()

    def index(self, obj: Any, start: int = 0, stop: int = None) -> int:
        """
        Find object or list widget item from the list widget.

        Parameters
        ----------
        obj : Any
            Object to find. If a PyListWidgetItem is given, the index of the item
            (not the tagged object) is searched for.
        start : int, optional
            Starting index, by default 0
        stop : int, optional
            Index to stop searching.

        Returns
        -------
        int
            Index of object.

        Raises
        ------
        ValueError
            If object was not found.
        """
        if isinstance(obj, PyListWidgetItem):
            f = self._listwidget.item
        else:
            f = lambda i: self._listwidget.item(i).obj
        if start is not None and start < 0:
            start = max(len(self) + start, 0)
        if stop is not None and stop < 0:
            stop += len(self)

        i = start
        while stop is None or i < stop:
            try:
                v = f(i)
                if v is obj or v == obj:
                    return i
            except IndexError:
                break
            i += 1
        raise ValueError(f"Object {obj!r} not found in the list")


class PyListWidget(ContextMenuMixin, QListWidget):
    def item(self, row: int) -> PyListWidgetItem:
        return super().item(row)

    def itemAt(self, *p) -> PyListWidgetItem:
        return super().itemAt(*p)

    def __init__(self, parent: None) -> None:
        super().__init__(parent=parent)
        self.setContextMenu()


class PyListWidgetItem(PyObjectBound, QListWidgetItem):
    def __init__(self, parent: QListWidget = None, obj=None, name=None):
        super().__init__(parent)
        self.setObject(obj, name)
