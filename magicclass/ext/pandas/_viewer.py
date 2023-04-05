from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from qtpy import QtCore, QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal

from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np
    import pandas as pd


class QDataFrameModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    def __init__(self, df: pd.DataFrame = None, parent=None):
        super().__init__(parent)
        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def rowCount(self, parent=None):
        return self.df.shape[0]

    def columnCount(self, parent=None):
        return self.df.shape[1]

    def data(
        self,
        index: QtCore.QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return QtCore.QVariant()
        if role != Qt.ItemDataRole.DisplayRole:
            return QtCore.QVariant()
        r, c = index.row(), index.column()
        df = self.df
        if r < df.shape[0] and c < df.shape[1]:
            val = df.iat[r, c]
            colname = df.columns[c]
            text = _format_value(val, df.dtypes[colname])
            return text
        return QtCore.QVariant()

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                if section >= self.df.columns.size:
                    return None
                if self.df.columns.nlevels == 1:
                    text = str(self.df.columns[section])
                else:
                    text = "\n".join(map(str, self.df.columns[section]))
                return text
            elif role == Qt.ItemDataRole.ToolTipRole:
                if section < self.df.columns.size:
                    return self._column_tooltip(section)
                return None

        if orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                if section >= self.df.index.size:
                    return None
                text = str(self.df.index[section])
                return text
            elif role == Qt.ItemDataRole.ToolTipRole:
                if section < self.df.index.size:
                    return str(self.df.index[section])
                return None

    def _column_tooltip(self, section: int):
        name = self.df.columns[section]
        dtype = self.df.dtypes.values[section]
        return f"{name} (dtype: {dtype})"


def _format_float(value, ndigits: int = 4) -> str:
    """convert string to int or float if possible"""
    try:
        if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
            text = f"{value:.{ndigits}f}"
        else:
            text = f"{value:.{ndigits-1}e}"
    except Exception:
        text = "NA"

    return text


def _format_int(value, ndigits: int = 4) -> str:
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = str(value)
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_complex(value: complex, ndigits: int = 3) -> str:
    try:
        if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
            text = f"{value.real:.{ndigits}f}{value.imag:+.{ndigits}f}j"
        else:
            text = f"{value.real:.{ndigits-1}e}{value.imag:+.{ndigits-1}e}j"
    except Exception:
        text = "NA"

    return text


_DEFAULT_FORMATTERS: dict[str, Callable[[Any], str]] = {
    "u": _format_int,
    "i": _format_int,
    "f": _format_float,
    "c": _format_complex,
}


def _format_value(val, dtype: np.dtype):
    return _DEFAULT_FORMATTERS.get(dtype.kind, str)(val)


class QDataFrameView(QtW.QTableView):
    valueChanged = Signal(object)

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        _per_pixel = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel
        self.setVerticalScrollMode(_per_pixel)
        self.setHorizontalScrollMode(_per_pixel)

    def dataFrame(self):
        return self.model().df

    def setDataFrame(self, val):
        import pandas as pd

        df = pd.DataFrame(val)
        self.setModel(QDataFrameModel(df))
        self.valueChanged.emit(df)
        self.update()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.matches(QtGui.QKeySequence.StandardKey.Copy):
            return self.copy_data()
        return super().keyPressEvent(e)

    def copy_data(self):
        model = self.selectionModel()
        if not model.hasSelection():
            return
        indexes = model.selectedIndexes()
        start = indexes[0]
        stop = indexes[-1]
        rstart = start.row()
        rstop = stop.row() + 1
        cstart = start.column()
        cstop = stop.column() + 1
        df_sub = self.model().df.iloc[rstart:rstop, cstart:cstop]
        df_sub.to_clipboard()

    if TYPE_CHECKING:  # pragma: no cover

        def model(self) -> QDataFrameModel:
            ...


class QDataFrameViewBase(QBaseValueWidget):
    def __init__(self, **kwargs):
        super().__init__(
            QDataFrameView, "dataFrame", "setDataFrame", "valueChanged", **kwargs
        )


class DataFrameView(ValueWidget):
    def __init__(
        self,
        value=Undefined,
        bind=Undefined,
        nullable=False,
        **kwargs,
    ):
        kwargs["widget_type"] = QDataFrameViewBase
        super().__init__(value=value, bind=bind, nullable=nullable, **kwargs)
