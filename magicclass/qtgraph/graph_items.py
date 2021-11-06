from __future__ import annotations
from typing import Sequence
import pyqtgraph as pg
import numpy as np

def _convert_color_code(c):
    if not isinstance(c, str):
        c = np.asarray(c) * 255
    return c

class PlotDataItem:
    base_item: type[pg.PlotCurveItem|pg.ScatterPlotItem]
    def __init__(self, x, y, name=None, **kwargs):
        if "color" in kwargs:
            # alias for consistency with matplotlib
            kwargs["pen"] = kwargs.pop("color")
            
        self.native = self.base_item(x=x, y=y, **kwargs)
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
        
    def add(self, points: np.ndarray | Sequence):
        points = np.atleast_2d(points)
        if points.shape[1] != 2:
            raise ValueError("Points must be of the shape (N, 2).")
        self.native.setData(np.concatenate([self.xdata, points[:, 0]]), 
                            np.concatenate([self.ydata, points[:, 1]])
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
    def color(self) -> np.ndarray:
        rgba = self.native.opts["pen"].color().getRgb()
        return np.array(rgba)/255
    
    @color.setter
    def color(self, value: str | Sequence):
        value = _convert_color_code(value)
        self.native.setPen(value)
            
    # setDownsampling
    
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
    def symbol_size(self):
        self.native.opts["symbolSize"]
        
    @symbol.setter
    def symbol_size(self, size: float):
        self.native.setSymbolSize(size)

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
            
        