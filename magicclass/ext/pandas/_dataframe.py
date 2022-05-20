from __future__ import annotations
from typing import Any
import pandas as pd
from pandas._typing import Axes, Dtype, Axis
from magicgui.widgets import Table

from ...fields import field

Defaults = {
    "read_only": True,
}


class WidgetSeries(pd.Series):
    _table = field(Table)

    @property
    def _constructor(self):
        return self.__class__

    @property
    def _constructor_expanddim(self):
        return WidgetDataFrame

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
        tab = self._table
        with tab.changed.blocked():
            tab.value = {self.name: self.values}
            tab.row_headers = self.index
        tab.read_only = Defaults["read_only"]
        self._table_initialized = True
        return tab


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
        tab = self._table
        with tab.changed.blocked():
            tab.value = self
        self._table_initialized = True
        tab.read_only = Defaults["read_only"]
        return tab

    _dataframe_index = pd.DataFrame.index
    _dataframe_columns = pd.DataFrame.columns

    @property
    def index(self) -> pd.Index:
        return self._dataframe_index

    @index.setter
    def index(self, value) -> None:
        self._dataframe_index = value
        if self._table_initialized:
            self._table.row_headers = value

    @property
    def columns(self) -> pd.Index:
        return self._dataframe_columns

    @columns.setter
    def columns(self, value) -> None:
        self._dataframe_columns = value
        if self._table_initialized:
            self._table.column_headers = value
