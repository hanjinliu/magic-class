from __future__ import annotations
from typing import Sequence
import pyqtgraph as pg
import numpy as np

def _convert_color_code(c):
    if not isinstance(c, str):
        c = np.asarray(c) * 255
    return c
    

class PlotDataItem:
    base_item: type[pg.PlotDataItem]
    def __init__(self, x, y, **kwargs):
        self.native = self.base_item(x=x, y=y, **kwargs)
    
    @property
    def xdata(self):
        return self.native.xData
    
    @xdata.setter
    def xdata(self, value):
        self.native.setData(value, self.native.yData)
    
    @property
    def ydata(self):
        return self.native.yData
    
    @ydata.setter
    def ydata(self, value):
        self.native.setData(self.native.xData, value)
    
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
        for k, v in kwargs:
            if k not in ["color", "text", "visible"]:
                raise AttributeError(f"Cannot set attribute {k} to TextOverlay.")
        for k, v in kwargs:
            setattr(self, k, v)
            
        