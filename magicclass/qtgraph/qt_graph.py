from __future__ import annotations
import pyqtgraph as pg
from typing import Sequence, overload
import numpy as np
from magicgui.events import Signal
from .graph_items import PlotDataItem, Scatter, Curve, TextOverlay
from .mouse_event import MouseClickEvent
from ..widgets import FrozenContainer

BOTTOM = "bottom"
LEFT = "left"

class HasPlotItem:
    _items: list[PlotDataItem]
    
    @property
    def _graphics(self):
        """target widget to add graphics items."""
        raise NotImplementedError()

    @property
    def layers(self) -> list[PlotDataItem]:
        return self._items
    
    @overload
    def add_curve(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_curve(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
    
    def add_curve(self, x=None, y=None, **kwargs):
        if y is None:
            if x is None:
                x = []
                y = []
            else:
                y = x
                x = np.arange(len(y))
        item = Curve(x, y, **kwargs)
        self._add_item(item)
    
    @overload
    def add_scatter(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_scatter(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
      
    def add_scatter(self, x=None, y=None, **kwargs):
        if y is None:
            if x is None:
                x = []
                y = []
            else:
                y = x
                x = np.arange(len(y))
        item = Scatter(x, y, **kwargs)
        self._add_item(item)
        
    
    def _add_item(self, item: PlotDataItem):
        self._items.append(item)
        self._graphics.addItem(item.native)
    
    def remove_item(self, item: PlotDataItem | int | str):
        if isinstance(item, PlotDataItem):
            i = self._items.index(item)
        elif isinstance(item, int):
            i = item
        elif isinstance(item, str):
            for i, each in enumerate(self._items):
                if each.name == item:
                    break
            else:
                raise ValueError(f"No item named {item}")
            
        if i < 0:
            raise ValueError(f"Item {item} not found")
        item = self._items.pop(i)
        self._graphics.removeItem(item.native)

class Canvas(FrozenContainer, HasPlotItem):
    """
    A 1-D data viewer that have similar API as napari Viewer.
    """    
    region_changed = Signal(tuple[float, float])
    
    def __init__(self, region_visible=False, **kwargs):
        super().__init__(**kwargs)
        
        # prepare widget
        self.plotwidget = pg.PlotWidget()
        self._items: list[PlotDataItem] = []
        self.set_widget(self.plotwidget)
        
        # prepare region item
        self.regionitem = pg.LinearRegionItem()
        @self.regionitem.sigRegionChanged.connect
        def _(e=None):
            self.region_changed.emit(self.regionitem.getRegion())
            
        self.plotwidget.addItem(self.regionitem, ignoreBounds=True)
        self.region_visible = region_visible
        
        # prepare mouse event
        self.mouse_click_callbacks = []
        self.plotwidget.scene().sigMouseClicked.connect(self._mouse_clicked)
    
    def _mouse_clicked(self, e):
        if len(self._items) == 0:
            return
        e = MouseClickEvent(e, self._items[0].native)
        for callback in self.mouse_click_callbacks:
            callback(e)
    
    @property
    def _graphics(self):
        return self.plotwidget
    
    @property
    def xlabel(self):
        """
        Label of X-axis.
        """        
        return self.plotwidget.plotItem.getLabel(BOTTOM).text or ""
    
    @xlabel.setter
    def xlabel(self, label: str) -> str:
        self.plotwidget.plotItem.setLabel(BOTTOM, label)
    
    @property
    def xlim(self):
        """
        Range limits of X-axis.
        """        
        return self.plotwidget.plotItem.getAxis(BOTTOM).range
    
    @xlim.setter
    def xlim(self, value: tuple[float, float]):
        self.plotwidget.setXRange(*value)
        
    @property
    def ylabel(self) -> str:
        """
        Label of Y-axis.
        """        
        return self.plotwidget.plotItem.getLabel(LEFT).text or ""
        
    @ylabel.setter
    def ylabel(self, label: str):
        self.plotwidget.plotItem.setLabel(LEFT, label)
       
    @property
    def ylim(self):
        """
        Range limits of Y-axis.
        """        
        return self.plotwidget.plotItem.getAxis(LEFT).range
    
    @ylim.setter
    def ylim(self, value: tuple[float, float]):
        self.plotwidget.setYRange(*value)
    
    @property
    def region(self) -> tuple[float, float]:
        """
        Get the limits of linear region.
        """        
        return self.regionitem.getRegion()
    
    @region.setter
    def region(self, value: tuple[float, float]):
        self.regionitem.setRegion(value)
    
    @property
    def region_visible(self) -> bool:
        """
        Linear region visibility.
        """        
        return self.regionitem.isVisible()
    
    @region_visible.setter
    def region_visible(self, value: bool):
        self.regionitem.setVisible(value)
       
# TODO: colormap

class ImageCanvas(FrozenContainer, HasPlotItem):
    def __init__(self, image: np.ndarray = None, **kwargs):
        super().__init__(**kwargs)
        self.imageview = pg.ImageView(imageItem=image)
        self.set_widget(self.imageview)
        self._interactive = True
        self._items: list[PlotDataItem] = []
        
        # prpare text overlay
        self._text_overlay = TextOverlay(text="", color="gray")
        self.imageview.scene.addItem(self._text_overlay.native)
        
        # prepare mouse event
        self.mouse_click_callbacks = []
        self.imageview.scene.sigMouseClicked.connect(self._mouse_clicked)
        
    
    def _mouse_clicked(self, e):
        items = self.imageview.view.addedItems
        if len(items) == 0:
            return
        e = MouseClickEvent(e, items[0])
        for callback in self.mouse_click_callbacks:
            callback(e)
    
    @property
    def _graphics(self):
        return self.imageview.view
    
    @property
    def text_overlay(self) -> TextOverlay:
        """Text overlay on the image."""        
        return self._text_overlay
    
    @property
    def image(self) -> np.ndarray:
        return self.imageview.image
        
    @image.setter
    def image(self, image):
        self.imageview.setImage(np.asarray(image).T, autoRange=False)
        
    @image.deleter
    def image(self):
        self.imageview.clear()
    
    @property
    def contrast_limits(self):
        """
        Contrast limits of image.
        """        
        return self.imageview.levelMin, self.imageview.levelMax
    
    @contrast_limits.setter
    def contrast_limits(self, value):
        self.imageview.setLevels(*value)
    
    @property
    def view_range(self) -> list[list[float, float]]:
        """
        Range of image (edge coordinates of canvas).
        """        
        return self.imageview.view.viewRange()
    
    @view_range.setter
    def view_range(self, value: tuple[tuple[float, float], tuple[float, float]]):
        yrange, xrange = value
        self.imageview.view.setRange(xRange=xrange, yRange=yrange)
    
    @property
    def interactive(self) -> bool:
        """
        Mouse interactivity
        """        
        return self._interactive
    
    @interactive.setter
    def interactive(self, value: bool):
        self.imageview.view.setMouseEnabled(value, value)
        self._interactive = value
            
    def show_hist(self, visible: bool = True):
        """
        Set visibility of intensity histogram.

        Parameters
        ----------
        visible : bool
            Visibility of histogram
        """        
        if visible:
            self.imageview.ui.histogram.show()
        else:
            self.imageview.ui.histogram.hide()
        
    def show_button(self, visible: bool = True):
        """
        Set visibility of ROI/Norm buttons.

        Parameters
        ----------
        visible : bool
            Visibility of ROI/Norm buttons
        """        
        if visible:
            self.imageview.ui.menuBtn.show()
            self.imageview.ui.roiBtn.show()
        else:
            self.imageview.ui.menuBtn.hide()
            self.imageview.ui.roiBtn.hide()
    