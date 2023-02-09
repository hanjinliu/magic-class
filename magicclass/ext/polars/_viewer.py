from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from qtpy import QtCore, QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal

from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicclass._magicgui_compat import ValueWidget, Undefined

if TYPE_CHECKING:  # pragma: no cover
    import polars as pl
    from polars.datatypes import DataType


class QDataFrameModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    def __init__(self, df: pl.DataFrame = None, parent=None):
        super().__init__(parent)
        self._df = df

    @property
    def df(self) -> pl.DataFrame:
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
            colname = df.columns[c]
            val = df.get_column(colname)[r]
            text = _format_value(val, df.dtypes[c])
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
                if section >= self.df.shape[1]:
                    return None
                return str(self.df.columns[section])
            elif role == Qt.ItemDataRole.ToolTipRole:
                if section < self.df.shape[1]:
                    return self._column_tooltip(section)
                return None

        if orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(section)

    def _column_tooltip(self, section: int):
        name = self.df.columns[section]
        dtype = self.df.dtypes[section]
        return f"{name} (dtype: {dtype})"


def _format_float(value, ndigits: int = 4) -> str:
    """convert string to int or float if possible"""
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value:.{ndigits}f}"
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_int(value, ndigits: int = 4) -> str:
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = str(value)
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_complex(value: complex, ndigits: int = 3) -> str:
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value.real:.{ndigits}f}{value.imag:+.{ndigits}f}j"
    else:
        text = f"{value.real:.{ndigits-1}e}{value.imag:+.{ndigits-1}e}j"

    return text


_DEFAULT_FORMATTERS: dict[str, Callable[[Any], str]] = {
    "u": _format_int,
    "i": _format_int,
    "f": _format_float,
    "c": _format_complex,
}


def _format_value(val, dtype: DataType):
    return _DEFAULT_FORMATTERS.get(dtype.string_repr(dtype)[0], str)(val)


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
        import polars as pl

        if not isinstance(val, pl.DataFrame):
            df = pl.DataFrame(val)
        else:
            df = val
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
        df = self.model().df
        columns = df.columns[cstart:cstop]
        df_sub = df.select(columns)[rstart:rstop]
        text = df_sub.write_csv(sep="\t")
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(text)

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
