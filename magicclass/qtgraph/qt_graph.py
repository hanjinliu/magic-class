from __future__ import annotations
import pyqtgraph as pg
from typing import Sequence, overload
import numpy as np
from .graph_items import PlotDataItem, Scatter, Curve, TextOverlay
from ..widgets import FrozenContainer

BOTTOM = "bottom"
LEFT = "left"
        
class Canvas(FrozenContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plotwidget = pg.PlotWidget()
        self._items: list[PlotDataItem] = []
        self.set_widget(self.plotwidget)
               
    @property
    def xlabel(self):
        return self.plotwidget.plotItem.getLabel(BOTTOM).text or ""
    
    @xlabel.setter
    def xlabel(self, label: str) -> str:
        self.plotwidget.plotItem.setLabel(BOTTOM, label)
    
    @property
    def xlim(self):
        return self.plotwidget.plotItem.getAxis(BOTTOM).range
    
    @xlim.setter
    def xlim(self, value: tuple[float, float]):
        self.plotwidget.setXRange(*value)
        
    @property
    def ylabel(self) -> str:
        return self.plotwidget.plotItem.getLabel(LEFT).text or ""
        
    @ylabel.setter
    def ylabel(self, label: str):
        self.plotwidget.plotItem.setLabel(LEFT, label)
       
    @property
    def ylim(self):
        return self.plotwidget.plotItem.getAxis(LEFT).range
    
    @ylim.setter
    def ylim(self, value: tuple[float, float]):
        self.plotwidget.setYRange(*value)
             
    @overload
    def add_curve(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_curve(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
    
    def add_curve(self, x, y=None, **kwargs):
        if y is None:
            y = x
            x = np.arange(len(y))
        item = Curve(x, y, **kwargs)
        self._items.append(item)
        self.plotwidget.addItem(item.native)
    
    @overload
    def add_scatter(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_scatter(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
      
    def add_scatter(self, x, y=None, **kwargs):
        if y is None:
            y = x
            x = np.arange(len(y))
        item = Scatter(x, y, **kwargs)
        self._items.append(item)
        self.plotwidget.addItem(item.native)


class ImageCanvas(FrozenContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.imageview = pg.ImageView()
        self.set_widget(self.imageview)
        self._text_overlay = TextOverlay("", "gray")
        self.imageview.scene.addItem(self._text_overlay.native)
    
    @property
    def text_overlay(self):
        return self._text_overlay
    
    @property
    def image(self):
        return self.imageview.image
        
    @image.setter
    def image(self, image):
        self.imageview.setImage(np.asarray(image).T, autoRange=False)
        
    @image.deleter
    def image(self):
        self.imageview.clear()
    
    @property
    def contrast_limits(self):
        return self.imageview.levelMin, self.imageview.levelMax
    
    @contrast_limits.setter
    def contrast_limits(self, value):
        self.imageview.setLevels(*value)