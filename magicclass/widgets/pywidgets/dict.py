from __future__ import annotations
from typing import Any, Iterable, MutableMapping
from qtpy.QtWidgets import QTableWidget, QTableWidgetItem

from .object import BaseWidget, ContextMenuMixin, PyObjectBound


class DictWidget(BaseWidget, MutableMapping):
    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)

        self._tablewidget = PyTableWidget(self.native)
        self._tablewidget.setParentWidget(self)
        self._tablewidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tablewidget.verticalHeader().setDefaultSectionSize(30)
        self._dict: dict[str, int] = {}  # mapping from key to row

        self.set_widget(self._tablewidget)

        @self._tablewidget.itemDoubleClicked.connect
        def _(item: PyTableWidgetItem):
            type_ = type(item.obj)
            callbacks = self._callbacks.get(type_, [])
            self.running = True
            try:
                for callback in callbacks:
                    try:
                        callback(item.obj, self._tablewidget.row(item))
                    except TypeError:
                        callback(item.obj)
            finally:
                self.running = False

        if value is not None:
            self.update(dict(value))

    def __len__(self) -> int:
        return self._tablewidget.rowCount()

    @property
    def value(self) -> dict[str, Any]:
        return {k: self._tablewidget.item(row, 0) for k, row in self._dict}

    def __getitem__(self, k: str) -> Any:
        row = self._dict[k]
        return self._tablewidget.item(row, 0).obj

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
                self._tablewidget.setHorizontalHeaderItem(0, QTableWidgetItem("value"))
            key_item = QTableWidgetItem(k)
            self._tablewidget.setVerticalHeaderItem(row, key_item)

        name = self._delegates.get(type(obj), str)(obj)
        value_item = PyTableWidgetItem(obj, name)
        tooltip = self._tooltip.get(type(obj), str)(obj)
        value_item.setToolTip(tooltip)
        self._tablewidget.setItem(row, 0, value_item)

    def __delitem__(self, k: str) -> None:
        row = self._dict.pop(k)
        self._tablewidget.removeRow(row)

    def __iter__(self) -> Iterable[str]:
        return iter(self._dict)

    def keys(self):
        """
        Return the view of dictionary keys.
        """
        return self._dict.keys()

    def values(self) -> DictValueView:
        """
        Return the view of dictionary values as Python objects.
        """
        return DictValueView(self._tablewidget)

    def items(self) -> DictItemView:
        """
        Return the view of dictionary keys and values as strings and Python objects.
        """
        return DictItemView(self._tablewidget)

    def update(self, d: dict[str, Any]):
        """
        Update the dictionary contents.
        """
        for k, v in d.items():
            self[k] = v

    def clear(self) -> None:
        """
        Clear dictionary contents.
        """
        self._tablewidget.clear()
        self._dict.clear()

    def pop(self, k: str):
        """
        Pop a dictionary content.
        """
        row = self._dict.pop(k)
        out = self._tablewidget.item(row, 0).obj
        self._tablewidget.removeRow(row)
        return out

    def get(self, k: str, default=None):
        self._dict.get(k, default)


class PyTableWidget(ContextMenuMixin, QTableWidget):
    def item(self, row: int, column: int) -> PyTableWidgetItem:
        return super().item(row, column)

    def itemAt(self, *p) -> PyTableWidgetItem:
        return super().itemAt(*p)

    def __init__(self, parent: None) -> None:
        super().__init__(parent=parent)
        self.setContextMenu()


class PyTableWidgetItem(PyObjectBound, QTableWidgetItem):
    def __init__(self, obj=None, name=None):
        super().__init__()
        self.setObject(obj, name)


class DictValueView:
    def __init__(self, widget: PyTableWidget):
        self.widget = widget

    def __iter__(self):
        for row in range(self.widget.rowCount()):
            yield self.widget.item(row, 0).obj


class DictItemView:
    def __init__(self, widget: PyTableWidget):
        self.widget = widget

    def __iter__(self):
        for row in range(self.widget.rowCount()):
            key = self.widget.verticalHeaderItem(row).text()
            value = self.widget.item(row, 0).obj
            yield key, value
