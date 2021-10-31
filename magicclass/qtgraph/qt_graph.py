from __future__ import annotations
import pyqtgraph as pg
from typing import Sequence, overload
import numpy as np
from magicgui.events import Signal
from .graph_items import PlotDataItem, Scatter, Curve, TextOverlay
from ..widgets import FrozenContainer

BOTTOM = "bottom"
LEFT = "left"

class SingleRegion:
    region_changed = Signal(tuple[float, float])
    
    def __init__(self):
        self.regionitem = pg.LinearRegionItem()
        @self.regionitem.sigRegionChanged.connect
        def _(e=None):
            self.region_changed.emit(self.regionitem.getRegion())
    
    @property
    def region(self) -> tuple[float, float]:
        return self.regionitem.getRegion()
    
    @region.setter
    def region(self, value: tuple[float, float]):
        self.regionitem.setRegion(value)
    
    @property
    def region_visible(self) -> bool:
        return self.regionitem.isVisible()
    
    @region_visible.setter
    def region_visible(self, value: bool):
        self.regionitem.setVisible(value)
    
class MultiRegion:
    regionitems: list[pg.LinearRegionItem]
        
class Canvas(FrozenContainer, SingleRegion):
    def __init__(self, region_visible=False, **kwargs):
        super().__init__(**kwargs)
        self.plotwidget = pg.PlotWidget()
        self._items: list[PlotDataItem] = []
        self.set_widget(self.plotwidget)
        
        SingleRegion.__init__(self)
        self.plotwidget.addItem(self.regionitem, ignoreBounds=True)
        self.region_visible = region_visible
               
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