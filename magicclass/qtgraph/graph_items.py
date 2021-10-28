from __future__ import annotations
from typing import Sequence
import pyqtgraph as pg
import numpy as np


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
        if not isinstance(value, str):
            value = np.asarray(value) * 255
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
        