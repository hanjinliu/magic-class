from __future__ import annotations
from typing import Sequence
import pyqtgraph as pg
from qtpy.QtCore import Qt
import numpy as np
from .utils import convert_color_code

LINE_STYLE = {"-": Qt.SolidLine,
              "--": Qt.DashLine,
              ":": Qt.DotLine,
              "-.": Qt.DashDotLine,
              }

_SYMBOL_MAP = {
        "*": "star",
        "D": "d",
        "^": "t1",
        "<": "t3",
        "v": "t",
        ">": "t2",
    }

class PlotDataItem:
    native: pg.PlotCurveItem | pg.ScatterPlotItem
    
    @property
    def xdata(self) -> np.ndarray:
        return self.native.getData()[0]
    
    @xdata.setter
    def xdata(self, value: Sequence[float]):
        self.native.setData(value, self.ydata)
    
    @property
    def ydata(self) -> np.ndarray:
        return self.native.getData()[1]
    
    @ydata.setter
    def ydata(self, value: Sequence[float]):
        self.native.setData(self.xdata, value)
    
    @property
    def ndata(self) -> int:
        return self.native.getData()[0].size
    
    @property
    def name(self) -> str:
        return self.native.opts["name"]
    
    @name.setter
    def name(self, value: str):
        value = str(value)
        self.native.opts["name"] = value
        # TODO: now name is not linked to label item

    def __len__(self) -> int:
        return self.native.getData()[0].size
        
    def add(self, points: np.ndarray | Sequence, **kwargs):
        """Add new points to the plot data item."""
        points = np.atleast_2d(points)
        if points.shape[1] != 2:
            raise ValueError("Points must be of the shape (N, 2).")
        self.native.setData(np.concatenate([self.xdata, points[:, 0]]), 
                            np.concatenate([self.ydata, points[:, 1]]),
                            **kwargs
                            )
        return None
    
    def remove(self, i: int | Sequence[int]):
        """Remove the i-th data."""
        if isinstance(i, int):
            i = [i]
        sl = list(set(range(self.ndata)) - set(i))
        xdata = self.xdata[sl]
        ydata = self.ydata[sl]
        self.native.setData(xdata, ydata)
        return None
    
    @property
    def visible(self):
        """Visibility of data."""
        return self.native.isVisible()
    
    @visible.setter
    def visible(self, value: bool):
        self.native.setVisible(value)
    
    @property
    def edge_color(self) -> np.ndarray:
        """Edge color of the data."""
        rgba = self.native.opts["pen"].color().getRgb()
        return np.array(rgba)/255
    
    @edge_color.setter
    def edge_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setPen(value)
    
    @property
    def face_color(self) -> np.ndarray:
        """Face color of the data."""
        rgba = self.native.opts["brush"].color().getRgb()
        return np.array(rgba)/255
    
    @face_color.setter
    def face_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setBrush(value)

    color = property()
    
    @color.setter
    def color(self, value: str | Sequence):
        """Set face color and edge color at the same time."""
        self.face_color = value
        self.edge_color = value
        
    @property
    def lw(self):
        """Line width."""
        return self.native.opts["pen"].width()
    
    @lw.setter
    def lw(self, value: float):
        self.native.opts["pen"].setWidth(value)
        
    linewidth = lw # alias
    
    @property
    def ls(self):
        """Line style."""
        return self.native.opts["pen"].style()
    
    @ls.setter
    def ls(self, value: str):
        _ls = LINE_STYLE[value]
        self.native.opts["pen"].setStyle(_ls)
    
    linestyle = ls # alias

    @property
    def zorder(self) -> float:
        """Z-order of item. Item with larger z will be displayed on the top."""
        return self.native.zValue()
    
    @zorder.setter
    def zorder(self, value: float):
        self.native.setZValue(value)


class Scatter(PlotDataItem):
    native: pg.ScatterPlotItem
    
    def __init__(self, 
                 x,
                 y,
                 face_color = None,
                 edge_color = None,
                 size: float = 7,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-",
                 symbol="o"
                 ):
        face_color, edge_color = _set_default_colors(
            face_color, edge_color, "white", "white"
            )
        pen = pg.mkPen(edge_color, width=lw, style=LINE_STYLE[ls])
        brush = pg.mkBrush(face_color)
        symbol = _SYMBOL_MAP.get(symbol, symbol)
        self.native = pg.ScatterPlotItem(x=x, y=y, pen=pen, brush=brush, size=size, symbol=symbol)
        self.name = name
        
    @property
    def symbol(self):
        return self.native.opts["symbol"]
        
    @symbol.setter
    def symbol(self, value):
        value = _SYMBOL_MAP.get(value, value)
        self.native.setSymbol(value)
    
    @property
    def size(self):
        return self.native.opts["symbolSize"]
        
    @size.setter
    def size(self, size: float):
        self.native.setSymbolSize(size)


class Curve(PlotDataItem):
    native: pg.PlotDataItem
    
    def __init__(self, 
                 x,
                 y,
                 face_color = None,
                 edge_color = None,
                 size: float = 7,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-",
                 symbol=None
                 ):
        face_color, edge_color = _set_default_colors(
            face_color, edge_color, "white", "white"
            )
        pen = pg.mkPen(edge_color, width=lw, style=LINE_STYLE[ls])
        brush = pg.mkBrush(face_color)
        symbol = _SYMBOL_MAP.get(symbol, symbol)
        self.native = pg.PlotDataItem(x=x, y=y, pen=pen, brush=brush, symbolSize=size, 
                                      symbol=symbol, symbolPen=pen, symbolBrush=brush)
        self.name = name
        
    @property
    def symbol(self):
        return self.native.opts["symbol"]
        
    @symbol.setter
    def symbol(self, value):
        value = _SYMBOL_MAP.get(value, value)
        self.native.setSymbol(value)
    
    @property
    def size(self):
        return self.native.opts["symbolSize"]
        
    @size.setter
    def size(self, size: float):
        self.native.setSymbolSize(size)
        
    @property
    def edge_color(self) -> np.ndarray:
        rgba = self.native.opts["pen"].color().getRgb()
        return np.array(rgba)/255
    
    @edge_color.setter
    def edge_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setPen(value)
        self.native.setSymbolPen(value)
    
    @property
    def face_color(self) -> np.ndarray:
        rgba = self.native.opts["symbolBrush"].color().getRgb()
        return np.array(rgba)/255
    
    @face_color.setter
    def face_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setBrush(value)
        self.native.setSymbolBrush(value)


class Histogram(PlotDataItem):
    native: pg.ScatterPlotItem
    
    def __init__(self, 
                 data,
                 bins: int | Sequence | str = 10,
                 range=None,
                 density: bool = False,
                 face_color = None,
                 edge_color = None,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-",
                 ):
        face_color, edge_color = _set_default_colors(
            face_color, edge_color, "white", "white"
            )
        pen = pg.mkPen(edge_color, width=lw, style=LINE_STYLE[ls])
        brush = pg.mkBrush(face_color)
        y, x = np.histogram(data, bins=bins, range=range, density=density)
        self.native = pg.PlotCurveItem(x=x, y=y, pen=pen, brush=brush, 
                                       stepMode="center", fillLevel=0)
        self.name = name
    
    def set_hist(self, data, bins=10, range=None, density=False):
        y, x = np.histogram(data, bins=bins, range=range, density=density)
        self.native.setData(x=x, y=y)


class BarPlot(PlotDataItem):
    native: pg.BarGraphItem
    
    def __init__(self, 
                 x,
                 y,
                 face_color = None,
                 edge_color = None,
                 width: float = 0.6,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-"):
        face_color, edge_color = _set_default_colors(
            face_color, edge_color, "white", "white"
            )
        pen = pg.mkPen(edge_color, width=lw, style=LINE_STYLE[ls])
        brush = pg.mkBrush(face_color)
        self.native = pg.BarGraphItem(x=x, height=y, width=width, pen=pen, brush=brush)
        self.name = name

    @property
    def edge_color(self) -> np.ndarray:
        rgba = self.native.opts["pen"].color().getRgb()
        return np.array(rgba)/255
    
    @edge_color.setter
    def edge_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setOpts(pen=pg.mkPen(value))
    
    @property
    def face_color(self) -> np.ndarray:
        rgba = self.native.opts["brush"].color().getRgb()
        return np.array(rgba)/255
    
    @face_color.setter
    def face_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setOpts(brush=pg.mkBrush(value))

    @property
    def xdata(self) -> np.ndarray:
        return self.native.getData()[0]
    
    @xdata.setter
    def xdata(self, value: Sequence[float]):
        self.native.setOpts(x=value)
    
    @property
    def ydata(self) -> np.ndarray:
        return self.native.getData()[1]
    
    @ydata.setter
    def ydata(self, value: Sequence[float]):
        self.native.setOpts(height=value)


class FillBetween(PlotDataItem):
    native: pg.FillBetweenItem
    
    def __init__(self, 
                 x,
                 y1,
                 y2,
                 face_color = None,
                 edge_color = None,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-"):
        face_color, edge_color = _set_default_colors(
            face_color, edge_color, "white", "white"
            )
        pen = pg.mkPen(edge_color, width=lw, style=LINE_STYLE[ls])
        brush = pg.mkBrush(face_color)
        curve1 = pg.PlotCurveItem(x=x, y=y1, pen=pen)
        curve2 = pg.PlotCurveItem(x=x, y=y2, pen=pen)
        self.native = pg.FillBetweenItem(curve1, curve2, brush=brush, pen=pen)
        self.name = name

    @property
    def edge_color(self) -> np.ndarray:
        rgba = self.native.curves[0].opts["pen"].color().getRgb()
        return np.array(rgba)/255
    
    @edge_color.setter
    def edge_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setPen(pg.mkPen(value))
    
    @property
    def face_color(self) -> np.ndarray:
        rgba = self.native.curves[0].opts["brush"].color().getRgb()
        return np.array(rgba)/255
    
    @face_color.setter
    def face_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setBrush(pg.mkBrush(value))
    
    @property
    def name(self) -> str:
        return self.native.curves[0].opts["name"]
    
    @name.setter
    def name(self, value: str):
        value = str(value)
        self.native.curves[0].opts["name"] = value
    
    @property
    def lw(self):
        """Line width."""
        return self.native.curves[0].opts["pen"].width()
    
    @lw.setter
    def lw(self, value: float):
        self.native.curves[0].opts["pen"].setWidth(value)
        self.native.curves[1].opts["pen"].setWidth(value)
        
    linewidth = lw # alias
    
    @property
    def ls(self):
        """Line style."""
        return self.native.curves[0].opts["pen"].style()
    
    @ls.setter
    def ls(self, value: str):
        _ls = LINE_STYLE[value]
        self.native.curves[0].opts["pen"].setStyle(_ls)
        self.native.curves[1].opts["pen"].setStyle(_ls)
    
    linestyle = ls # alias
        

def _set_default_colors(face_color, edge_color, default_f, default_e):
    if face_color is None:
        face_color = default_f
    if edge_color is None:
        edge_color = default_e
    return face_color, edge_color

def _find_ancestor(widget, itemtype: type):
    item = widget
    while type(item) is not itemtype:
        item = widget.parentItem()
    return item