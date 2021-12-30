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

    def __len__(self) -> int:
        return self.native.getData()[0].size
        
    def add(self, points: np.ndarray | Sequence, **kwargs):
        points = np.atleast_2d(points)
        if points.shape[1] != 2:
            raise ValueError("Points must be of the shape (N, 2).")
        self.native.setData(np.concatenate([self.xdata, points[:, 0]]), 
                            np.concatenate([self.ydata, points[:, 1]]),
                            **kwargs
                            )
        return None
    
    def remove(self, i: int | Sequence[int]):
        if isinstance(i, int):
            i = [i]
        sl = list(set(range(self.ndata)) - set(i))
        xdata = self.xdata[sl]
        ydata = self.ydata[sl]
        self.native.setData(xdata, ydata)
        return None
    
    @property
    def visible(self):
        return self.native.isVisible()
    
    @visible.setter
    def visible(self, value: bool):
        self.native.setVisible(value)
    
    @property
    def edge_color(self) -> np.ndarray:
        rgba = self.native.opts["pen"].color().getRgb()
        return np.array(rgba)/255
    
    @edge_color.setter
    def edge_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setPen(value)
    
    @property
    def face_color(self) -> np.ndarray:
        rgba = self.native.opts["brush"].color().getRgb()
        return np.array(rgba)/255
    
    @face_color.setter
    def face_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self.native.setBrush(value)
            
    @property
    def lw(self):
        return self.native.opts["pen"].width()
    
    @lw.setter
    def lw(self, value: float):
        self.native.opts["pen"].setWidth(value)
        
    linewidth = lw # alias
    
    @property
    def ls(self):
        return self.native.opts["pen"].style()
    
    @ls.setter
    def ls(self, value: str):
        _ls = LINE_STYLE[value]
        self.native.opts["pen"].setStyle(_ls)
    
    linestyle = ls # alias


class Curve(PlotDataItem):
    def __init__(self, 
                 x,
                 y,
                 face_color = None,
                 edge_color = "white",
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-"):
        pen = pg.mkPen(edge_color, width=lw, style=LINE_STYLE[ls])
        brush = pg.mkBrush(face_color)
        self.native = pg.PlotCurveItem(x=x, y=y, pen=pen, brush=brush)
        self.name = name

class Scatter(PlotDataItem):
    native: pg.ScatterPlotItem
    _SymbolMap = {
        "*": "star",
        "D": "d",
        "^": "t1",
        "<": "t3",
        "v": "t",
        ">": "t2",
    }
    def __init__(self, 
                 x,
                 y,
                 face_color = "white",
                 edge_color = None,
                 size: float = 7,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-",
                 symbol="o"
                 ):
        pen = pg.mkPen(edge_color, width=lw, style=LINE_STYLE[ls])
        brush = pg.mkBrush(face_color)
        symbol = self._SymbolMap.get(symbol, symbol)
        self.native = pg.ScatterPlotItem(x=x, y=y, pen=pen, brush=brush, size=size, symbol=symbol)
        self.name = name
        
    @property
    def symbol(self):
        return self.native.opts["symbol"]
        
    @symbol.setter
    def symbol(self, value):
        value = self._SymbolMap.get(value, value)
        self.native.setSymbol(value)
    
    @property
    def size(self):
        self.native.opts["symbolSize"]
        
    @size.setter
    def size(self, size: float):
        self.native.setSymbolSize(size)


class Histogram(PlotDataItem):
    native: pg.ScatterPlotItem
    
    def __init__(self, 
                 data,
                 bins: int | Sequence | str = 10,
                 range=None,
                 density: bool = False,
                 face_color = "white",
                 edge_color = None,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-",
                 ):
        
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
                 face_color = "white",
                 edge_color = "white",
                 width: float = 0.6,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-"):
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