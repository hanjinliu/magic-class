from __future__ import annotations
from typing import Any
import pandas as pd
from pandas._typing import Axes, Dtype, Axis
from magicgui.widgets import Table
from ...fields import field


class WidgetSeries(pd.Series):
    _table = field(Table)

    def __init__(
        self,
        data=None,
        index=None,
        dtype: Dtype | None = None,
        name=None,
        copy: bool = False,
        fastpath: bool = False,
    ):
        super().__init__(
            data=data, index=index, dtype=dtype, name=name, copy=copy, fastpath=fastpath
        )
        self._table_initialized = False

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self._table_initialized:
            with self._table.changed.blocked():
                self._table[key] = value

    @_table.connect
    def _on_table_data_change(self, info: dict[str, Any]):
        nc = info["column"]
        if nc > 0:
            raise ValueError(f"Cannot set value at column-{nc}")
        self.iloc[info["row"]] = info["data"]

    @property
    def table(self) -> Table:
        with self._table.changed.blocked():
            self._table.value = {self.name: self.values}
            self._table.row_headers = self.index
        self._table_initialized = True
        return self._table


class WidgetDataFrame(pd.DataFrame):
    _table = field(Table)

    @property
    def _constructor(self):
        return self.__class__

    _constructor_sliced = WidgetSeries

    def __init__(
        self,
        data=None,
        index: Axes | None = None,
        columns: Axes | None = None,
        dtype: Dtype | None = None,
        copy: bool | None = None,
    ):
        super().__init__(
            data=data, index=index, columns=columns, dtype=dtype, copy=copy
        )
        self._table_initialized = False

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self._table_initialized:
            with self._table.changed.blocked():
                self._table[key] = value

    @_table.connect
    def _on_table_data_change(self, info: dict[str, Any]):
        self.iloc[info["row"], info["column"]] = info["data"]

    def aggregate(self, func=None, axis: Axis = 0, *args, **kwargs):
        out = super().aggregate(func, axis, *args, **kwargs)
        return self.__class__(out)

    agg = aggregate

    @property
    def table(self) -> Table:
        with self._table.changed.blocked():
            self._table.value = self
        self._table_initialized = True
        return self._table

    @property
    def index(self) -> pd.Index:
        """Return the index (row headers)."""
        return super().index

    @index.setter
    def index(self, value) -> None:
        super().index = value
        if self._table_initialized:
            self._table.row_headers = value

    @property
    def columns(self) -> pd.Index:
        """Return the columns (column headers)."""
        return super().columns

    @columns.setter
    def columns(self, value) -> None:
        super().columns = value
        if self._table_initialized:
            self._table.column_headers = value


def read_csv(path, *args, **kwargs):
    df = pd.read_csv(path, *args, **kwargs)
    return WidgetDataFrame(data=df)
