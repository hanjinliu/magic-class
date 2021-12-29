from __future__ import annotations
from typing import Sequence, Any
import pyqtgraph as pg
from qtpy.QtCore import Qt
import numpy as np

LINE_STYLE = {"-": Qt.SolidLine,
              "--": Qt.DashLine,
              ":": Qt.DotLine,
              "-.": Qt.DashDotLine,
              }

def _convert_color_code(c):
    if not isinstance(c, str):
        c = np.asarray(c) * 255
    return c

def _get_pen(kwargs: dict[str, Any]):
    """Translation from matplotlib's kwargs to pyqtgraph's"""
    if "pen" in kwargs:
        return kwargs["pen"]
    
    if "c" in kwargs:
        color = kwargs["c"]
    else:
        color = kwargs.get("color", None)
    
    if "lw" in kwargs:
        width = kwargs["lw"]
    else:
        width = kwargs.get("lw", 1)
        
    if "ls" in kwargs:
        style = LINE_STYLE[kwargs["ls"]]
    else:
        style = LINE_STYLE[kwargs.get("linestyle", "-")]
    
    return pg.mkPen(color=color, width=width, style=style)

class PlotDataItem:
    base_item: type[pg.PlotCurveItem | pg.ScatterPlotItem]
    def __init__(self, x, y, name=None, **kwargs):
        pen = _get_pen(kwargs)
        kwargs.pop("pen", None)
            
        self.native = self.base_item(x=x, y=y, pen=pen, **kwargs)
        self.name = name
    
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
        value = _convert_color_code(value)
        self.native.setPen(value)
    
    @property
    def face_color(self) -> np.ndarray:
        rgba = self.native.opts["brush"].color().getRgb()
        return np.array(rgba)/255
    
    @face_color.setter
    def face_color(self, value: str | Sequence):
        value = _convert_color_code(value)
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
        self.native.opts["pen"].setWidth(_ls)
    
    linestyle = ls # alias


class Curve(PlotDataItem):
    base_item = pg.PlotCurveItem


class Scatter(PlotDataItem):
    base_item = pg.ScatterPlotItem
            
    @property
    def symbol(self):
        return self.native.opts["symbol"]
        
    @symbol.setter
    def symbol(self, value):
        self.native.setSymbol(value)
    
    @property
    def size(self):
        self.native.opts["symbolSize"]
        
    @size.setter
    def size(self, size: float):
        self.native.setSymbolSize(size)


class Histogram(PlotDataItem):
    base_item = pg.PlotCurveItem
    
    def __init__(self, 
                 data,
                 bins: int | Sequence | str = 10,
                 range=None,
                 density:bool = False, 
                 name=None,
                 **kwargs):
        pen = _get_pen(kwargs)
        kwargs.pop("pen", None)
        
        y, x = np.histogram(data, bins=bins, range=range, density=density)
        
        self.native = self.base_item(x=x, y=y, pen=pen, stepMode=True, 
                                     fillLevel=0, **kwargs)
        self.name = name



class TextOverlay:
    def __init__(self, text: str, color: Sequence[float] | str) -> None:
        self.native = pg.TextItem(text, color=_convert_color_code(color))
    
    @property
    def color(self):
        rgba = self.native.color.getRgb()
        return np.array(rgba)/255
    
    @color.setter
    def color(self, value):
        value = _convert_color_code(value)
        self.native.setText(self.text, value)
    
    @property
    def visible(self):
        return self.native.isVisible()
    
    @visible.setter
    def visible(self, value: bool):
        self.native.setVisible(value)
    
    @property
    def text(self):
        return self.native.toPlainText()
    
    @text.setter
    def text(self, value: str):
        self.native.setText(value)
    
    def update(self, **kwargs):
        for k, v in kwargs.items():
            if k not in ["color", "text", "visible"]:
                raise AttributeError(f"Cannot set attribute {k} to TextOverlay.")
        for k, v in kwargs.items():
            setattr(self, k, v)


class ScaleBar:
    def __init__(self):
        self._unit = ""
        self.native = pg.ScaleBar(10, suffix=self._unit)
    
    @property
    def color(self):
        rgba = self.native.brush.color().getRgb()
        return np.array(rgba)/255
    
    @color.setter
    def color(self, value):
        value = _convert_color_code(value)
        self.native.brush = pg.mkBrush(value)
        self.native.bar.setBrush(self.native.brush)
    
    @property
    def visible(self):
        return self.native.isVisible()
    
    @visible.setter
    def visible(self, value: bool):
        self.native.setVisible(value)
    
    @property
    def unit(self) -> str:
        return self._unit
    
    @unit.setter
    def unit(self, value: str):
        value = str(value)
        self.native.text.setText(pg.siFormat(self.native.size, suffix=value))
        self._unit = value