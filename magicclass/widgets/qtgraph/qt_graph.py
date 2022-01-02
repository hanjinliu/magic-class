from __future__ import annotations
from qtpy.QtGui import QTransform
import pyqtgraph as pg
from pyqtgraph import colormap as cmap
from typing import Iterator, Sequence, overload, MutableSequence
import numpy as np
from .components import Legend, Region, Roi, ScaleBar, TextOverlay
from .graph_items import BarPlot, Curve, PlotDataItem, Scatter, Histogram
from .mouse_event import MouseClickEvent
from ._doc import write_docs
from ..utils import FreeWidget

BOTTOM = "bottom"
LEFT = "left"

class LayerList(MutableSequence[PlotDataItem]):
    """A napari-like layer list for plot item handling."""
    def __init__(self, parent: HasDataItems):
        self.parent = parent
    
    
    def __getitem__(self, key: int | str) -> PlotDataItem:
        if isinstance(key, int):
            return self.parent._items[key]
        elif isinstance(key, str):
            for item in self.parent._items:
                if item.name == key:
                    return item
            else:
                raise ValueError(f"Item '{key}' not found.")
        else:
            raise TypeError(f"Cannot use type {type(key)} as a key.")
    
    
    def __setitem__(self, key, value):
        raise NotImplementedError("Can't set item")
    
    
    def __delitem__(self, key: int | str):
        return self.parent._remove_item(key)
    
    
    def append(self, item: PlotDataItem):
        if not isinstance(item, PlotDataItem):
            raise TypeError(f"Cannot append type {type(item)}.")
        self.parent._add_item(item)
            
    
    def insert(self, pos: int, item: PlotDataItem):
        if not isinstance(item, PlotDataItem):
            raise TypeError(f"Cannot insert type {type(item)}.")
        self.parent._insert_item(pos, item)
        
        
    def __len__(self):
        return len(self.parent._items)
    
    
    def clear(self):
        for _ in range(len(self)):
            self.parent._remove_item(-1)
    
    
    def swap(self, pos0: int, pos1: int):
        return self.parent._swap_items(pos0, pos1)
    
    
    def move(self, source: int, destination: int):
        return self.parent._move_item(source, destination)


class HasDataItems:
    _items: list[PlotDataItem]
    
    @property
    def _graphics(self):
        """Target widget to add graphics items."""
        raise NotImplementedError()

    @property
    def layers(self) -> LayerList:
        return LayerList(self)
    
    @overload
    def add_curve(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_curve(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
    
    @write_docs
    def add_curve(self, 
                  x=None, 
                  y=None,
                  face_color = None,
                  edge_color = None,
                  color = None,
                  size: float = 7,
                  name: str | None = None,
                  lw: float = 1,
                  ls: str = "-",
                  symbol=None):
        """
        Add a line plot like ``plt.plot(x, y)``.

        Parameters
        ----------
        {x}
        {y}
        {face_color}
        {edge_color}
        {color}
        size: float, default is 7
            Symbol size.
        {name}
        {lw}
        {ls}
        {symbol}
        
        Returns
        -------
        Curve
            A plot item of a curve.
        """        
        x, y = _check_xy(x, y)
        name = self._find_unique_name((name or "Curve"))
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = Curve(x, y, face_color=face_color, edge_color=edge_color, 
                            size=size, name=name, lw=lw, ls=ls, symbol=symbol)
        self._add_item(item)
        return item
    
    @overload
    def add_scatter(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_scatter(self, x: Sequence[float], y: Sequence[float], **kwargs): ...

    @write_docs
    def add_scatter(self, 
                    x=None, 
                    y=None,
                    face_color = None,
                    edge_color = None,
                    color = None,
                    size: float = 7,
                    name: str | None = None,
                    lw: float = 1,
                    ls: str = "-",
                    symbol="o"):
        """
        Add scatter plot like ``plt.scatter(x, y)``.

        Parameters
        ----------
        {x}
        {y}
        {face_color}
        {edge_color}
        {color}
        size: float, default is 7
            Symbol size.
        {name}
        {lw}
        {ls}
        {symbol}
        
        Returns
        -------
        Scatter
            A plot item of the scatter plot.
        """        
        x, y = _check_xy(x, y)
        name = self._find_unique_name((name or "Scatter"))
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = Scatter(x, y, face_color=face_color, edge_color=edge_color, 
                       size=size, name=name, lw=lw, ls=ls, symbol=symbol)
        self._add_item(item)
        return item
    
    @write_docs
    def add_hist(self, data: Sequence[float],
                 bins: int | Sequence | str = 10,
                 range=None,
                 density: bool = False,
                 face_color = None,
                 edge_color = None,
                 color = None,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-",
                 ):
        """
        Add histogram like ``plt.hist(data)``.

        Parameters
        ----------
        data : array-like
            Data for histogram constrction.
        bins : int, sequence of float or str, default is 10
            Bin numbers. See ``np.histogram`` for detail.
        range : two floats, optional
            Bin ranges. See ``np.histogram`` for detail.
        density : bool, default is False
            If true, plot the density instead of the counts. See ``np.histogram`` for
            detail.
        {face_color}
        {edge_color}
        {color}
        {name}
        {lw}
        {ls}
        
        Returns
        -------
        Histogram
            A plot item of the histogram.
        """        
        name = self._find_unique_name((name or "Histogram"))
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = Histogram(data, bins=bins, range=range, density=density, 
                         face_color=face_color, edge_color=edge_color,
                         name=name, lw=lw, ls=ls)
        self._add_item(item)
        return item
    
    @overload
    def add_bar(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_bar(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
    
    @write_docs
    def add_bar(self, 
                x=None,
                y=None, 
                width: float = 0.6,
                face_color = None,
                edge_color = None,
                color = None,
                name: str | None = None,
                lw: float = 1,
                ls: str = "-"):
        """
        Add a bar plot like ``plt.bar(x, y)``.

        Parameters
        ----------
        {x}
        {y}
        width : float, default is 0.6
            Width of each bar.
        {face_color}
        {edge_color}
        {color}
        {name}
        {lw}
        {ls}
        
        Returns
        -------
        BarPlot
            A plot item of the bar plot.
        """               
        x, y = _check_xy(x, y)
        name = self._find_unique_name((name or "Bar"))
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = BarPlot(x, y, width=width, face_color=face_color,
                       edge_color=edge_color, name=name, lw=lw, ls=ls)
        self._add_item(item)
        return item
    
    def _add_item(self, item: PlotDataItem):
        item.zorder = len(self._items)
        self._graphics.addItem(item.native)
        self._items.append(item)
    
    def _insert_item(self, pos: int, item: PlotDataItem):
        self._graphics.addItem(item.native)
        self._items.insert(pos, item)
        self._reorder()
    
    def _swap_items(self, pos0: int, pos1: int):
        item0 = self._items[pos0]
        item1 = self._items[pos1]
        self._items[pos0] = item1
        self._items[pos1] = item0
        self._reorder()
    
    def _move_item(self, source: int, destination: int):
        if source < destination:
            destination -= 1
        item = self._items.pop(source)
        self._items.insert(destination, item)
        self._reorder()
    
    def _remove_item(self, item: PlotDataItem | int | str):
        if isinstance(item, PlotDataItem):
            i = self._items.index(item)
        elif isinstance(item, int):
            if item < 0:
                item += len(self._items)
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
    
    def _reorder(self):
        for i, item in enumerate(self._items):
            item.zorder = i
        return None
    
    def _find_unique_name(self, prefix: str):
        existing_names = [item.name for item in self._items]
        name = prefix
        i = 0
        while name in existing_names:
            name = f"{prefix}-{i}"
            i += 1
        return name


class ViewBox(HasDataItems):
    def __init__(self):
        # prepare plot items
        self.pgitem = pg.ViewBox()
        self._items: list[PlotDataItem] = []
        
        # prepare mouse event
        self.mouse_click_callbacks = []
        
        # initialize private attributes
        self._enabled = True
        self._xlabel = ""
        self._ylabel = ""
    
    @property
    def _graphics(self):
        return self.pgitem


class HasViewBox(HasDataItems):
    def __init__(self, viewbox: pg.ViewBox):
        self._viewbox = viewbox
        self._items: list[PlotDataItem] = []
        
        # prepare mouse event
        self.mouse_click_callbacks = []
        
        self._enabled = True


    def _mouse_clicked(self, e):
        # NOTE: Mouse click event needs a reference item to map coordinates.
        # Here plot items always have a linear region item as a default one,
        # we can use it as the referene.
        ev = MouseClickEvent(e, self._get_default_item())
        x, y = ev.pos()
        [xmin, xmax], [ymin, ymax] = self._viewbox.viewRange()
        
        if xmin <= x <= xmax and ymin <= y <= ymax:
            for callback in self.mouse_click_callbacks:
                callback(ev)

    @property
    def xlim(self):
        """Range limits of X-axis."""  
        [xmin, xmax], _ = self._viewbox.viewRange()
        return xmin, xmax
    
    @xlim.setter
    def xlim(self, value: tuple[float, float]):
        self._viewbox.setXRange(*value)
       
    @property
    def ylim(self):
        """Range limits of Y-axis."""
        _, [ymin, ymax] = self._viewbox.viewRange()
        return ymin, ymax
    
    @ylim.setter
    def ylim(self, value: tuple[float, float]):
        self._viewbox.setYRange(*value)

    @property
    def enabled(self) -> bool:
        """Mouse interactivity"""        
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._viewbox.setMouseEnabled(value, value)
        self._enabled = value
        
    interactive = enabled
    

class HasPlotItems(HasDataItems):
    def __init__(self, basePlotItem: pg.PlotItem | None = None):
        # prepare plot items
        if basePlotItem is None:
            basePlotItem = pg.PlotItem()
        self.pgitem = basePlotItem
        self._items: list[PlotDataItem] = []
        
        # prepare mouse event
        self.mouse_click_callbacks = []
        
        self._enabled = True

    @property
    def _graphics(self):
        return self.pgitem


    def _update_scene(self):
        # Since plot item does not have graphics scene before being added to
        # a graphical layout, mouse event should be connected afterward.
        self.pgitem.scene().sigMouseClicked.connect(self._mouse_clicked)


    def _mouse_clicked(self, e):
        # NOTE: Mouse click event needs a reference item to map coordinates.
        # Here plot items always have a linear region item as a default one,
        # we can use it as the referene.
        ev = MouseClickEvent(e, self._get_default_item())
        x, y = ev.pos()
        [xmin, xmax], [ymin, ymax] = self.pgitem.vb.viewRange()
        
        if xmin <= x <= xmax and ymin <= y <= ymax:
            for callback in self.mouse_click_callbacks:
                callback(ev)

    @property
    def xlim(self):
        """Range limits of X-axis."""  
        [xmin, xmax], _ = self.pgitem.vb.viewRange()
        return xmin, xmax
    
    @xlim.setter
    def xlim(self, value: tuple[float, float]):
        self.pgitem.vb.setXRange(*value)
       
    @property
    def ylim(self):
        """Range limits of Y-axis."""
        _, [ymin, ymax] = self.pgitem.vb.viewRange()
        return ymin, ymax
    
    @ylim.setter
    def ylim(self, value: tuple[float, float]):
        self.pgitem.vb.setYRange(*value)

    @property
    def enabled(self) -> bool:
        """Mouse interactivity"""        
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self.pgitem.vb.setMouseEnabled(value, value)
        self._enabled = value
        
    interactive = enabled


class PlotItem(HasViewBox):
    """
    A 1-D plot item that has similar API as napari Viewer.
    """
    def __init__(self, viewbox: pg.ViewBox | None = None):
        if viewbox is None:
            viewbox = pg.ViewBox()
            
        self.pgitem = pg.PlotItem(viewBox=viewbox)
        super().__init__(self.pgitem.vb)
        
        # prepare region item
        self._region = Region()
        self._region.visible = False
        self.pgitem.addItem(self._region.native, ignoreBounds=True)
        
        # prepare legend item
        self._legend = Legend()
        self._legend.native.setParentItem(self.pgitem.vb)
        self.pgitem.legend = self._legend.native
        
        # initialize private attributes
        self._xlabel = ""
        self._ylabel = ""
    
    @property
    def _graphics(self):
        return self.pgitem
    
    def _get_default_item(self):
        return self._region.native
    
    @property
    def region(self) -> Region:
        """Linear region item."""
        return self._region
    
    @property
    def legend(self) -> Legend:
        """Legend item."""
        return self._legend
    
    @property
    def xlabel(self):
        """Label of X-axis."""
        return self._xlabel
    
    @xlabel.setter
    def xlabel(self, label: str) -> str:
        self.pgitem.setLabel(BOTTOM, label)
        self._xlabel = label
    
    @property
    def ylabel(self) -> str:
        """Label of Y-axis."""        
        return self._ylabel
        
    @ylabel.setter
    def ylabel(self, label: str):
        self.pgitem.setLabel(LEFT, label)
        self._ylabel = label
    
    
    def _update_scene(self):
        # Since plot item does not have graphics scene before being added to
        # a graphical layout, mouse event should be connected afterward.
        self.pgitem.scene().sigMouseClicked.connect(self._mouse_clicked)
       

class ImageItem(HasViewBox):
    
    def __init__(self, viewbox: pg.ViewBox | None = None):
        if viewbox is None:
            viewbox = pg.ViewBox(lockAspect=True, invertY=True)
        super().__init__(viewbox)
        self._image_item = pg.ImageItem()
        tr = self._image_item.transform().translate(-0.5, -0.5)
        self._image_item.setTransform(tr)
        
        self._viewbox.addItem(self._image_item)
        
        # prepare text overlay
        self._text_overlay = TextOverlay(text="", color="gray")
        
        # prepare region item
        self._region = Roi()
        self._region.visible = False
        self._viewbox.addItem(self._region.native, ignoreBounds=True)
        
        # prepare scale bar
        self._scale_bar = ScaleBar()
        self._scale_bar.visible = False
        self._scale_bar.native.setParentItem(self._viewbox)
        self._scale_bar.native.anchor((1, 1), (1, 1), offset=(-20, -20))
        
        self._hist = pg.HistogramLUTItem(orientation="horizontal")
        self._hist.vb.setBackgroundColor([0, 0, 0, 0.2])
        self._hist.setParentItem(self._viewbox)
        self._hist.setFixedWidth(160)
        self._hist.setVisible(False)
        from pyqtgraph import icons
        self._btn = pg.ButtonItem(icons.getGraphPixmap("auto"), 14, self._viewbox)
        
        @self._btn.clicked.connect
        def _(e):
            v = not self._hist.isVisible()
            self._hist.setVisible(v)
        
        self._cmap = "gray"
        
    def _get_default_item(self):
        return self._region.native
    

    def _update_scene(self):
        # Since plot item does not have graphics scene before being added to
        # a graphical layout, mouse event should be connected afterward.
        self._image_item.scene().sigMouseClicked.connect(self._mouse_clicked)
        self._image_item.scene().addItem(self._text_overlay.native)
        self._image_item.scene().addItem(self._scale_bar.native)
        
    @property
    def text_overlay(self) -> TextOverlay:
        """Text overlay on the image."""        
        return self._text_overlay
    
    @property
    def scale_bar(self) -> ScaleBar:
        """Scale bar on the image."""
        return self._scale_bar
    
    @property
    def _graphics(self):
        return self._viewbox
    
    @property
    def image(self) -> np.ndarray | None:
        """Image data"""
        if self._image_item.image is None:
            return None
        else:
            return self._image_item.image.T
        
    @image.setter
    def image(self, image: np.ndarray):
        self._image_item.setImage(np.asarray(image).T)
        self._hist.setImageItem(self._image_item)
        self._hist._updateView()
        
        
    @image.deleter
    def image(self):
        self._image_item.clear()
    
    @property
    def contrast_limits(self) -> list[float, float]:
        """Contrast limits of image"""        
        return self._image_item.levels
    
    @contrast_limits.setter
    def contrast_limits(self, value: tuple[float, float]):
        self._hist.setLevels(*value)

    
    @property
    def cmap(self):
        """Color map"""
        return self._cmap
    
    @cmap.setter
    def cmap(self, value):
        if isinstance(value, str):
            _cmap = cmap.get(value, source="matplotlib")
        else:
            _cmap = value
        self._hist.gradient.setColorMap(_cmap)
        self._cmap = value
            

class QtPlotCanvas(FreeWidget, PlotItem):
    """
    A 1-D data viewer that have similar API as napari Viewer.
    """
    def __init__(self, **kwargs):
        # prepare widget
        PlotItem.__init__(self)
        self.layoutwidget = pg.GraphicsLayoutWidget()
        self.layoutwidget.addItem(self.pgitem)
        self._update_scene()
        
        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)


class QtImageCanvas(FreeWidget, ImageItem):
    def __init__(self, **kwargs):
        # prepare widget
        ImageItem.__init__(self)
        self.layoutwidget = pg.GraphicsLayoutWidget()
        self.layoutwidget.addItem(self._viewbox)
        self._update_scene()
        
        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)


class Qt2YPlotCanvas(FreeWidget):
    def __init__(self, **kwargs):
        self.layoutwidget = pg.GraphicsLayoutWidget()
        
        item_l = PlotItem()
        item_r = ViewBox()
        
        self.layoutwidget.addItem(item_l.pgitem)
                
        item_l.pgitem.scene().addItem(item_r.pgitem)
        item_l.pgitem.getAxis("right").linkToView(item_r.pgitem)
        item_r.pgitem.setXLink(item_l.pgitem)
        
        item_l._update_scene()
        item_l.pgitem.showAxis("right")
        
        self._plot_items: tuple[PlotItem, ViewBox] = (item_l, item_r)
        
        self.updateViews()
        item_l.pgitem.vb.sigResized.connect(self.updateViews)
        
        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)
    
    
    def __getitem__(self, k: int) -> PlotItem:
        return self._plot_items[k]
    
    
    def updateViews(self):
        item_l ,item_r = self._plot_items
        item_r.pgitem.setGeometry(item_l.pgitem.vb.sceneBoundingRect())
        item_r.pgitem.linkedViewChanged(item_l.pgitem.vb, item_r.pgitem.XAxis)
    

class QtMultiPlotCanvas(FreeWidget):
    def __init__(self, 
                 nrows: int = 0,
                 ncols: int = 0,
                 sharex: bool = False,
                 sharey: bool = False,
                 **kwargs):
        """
        Multi-plot ``pyqtgraph`` canvas widget.

        Parameters
        ----------
        nrows : int, default is 0
            Initial rows of plots.
        ncols : int, default is 0
            Initail columns of plots.
        sharex : bool, default is False
            If true, all the x-axes will be linked.
        sharey : bool, default is False
            If true, all the y-axes will be linked.
        """
        self.layoutwidget = pg.GraphicsLayoutWidget()
        self._plot_items: list[PlotItem] = []
        self._sharex = sharex
        self._sharey = sharey
        
        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)
        
        if nrows * ncols > 0:
            for r in range(nrows):
                for c in range(ncols):
                    self.add(r, c)
    
    def add(self, 
            row: int | None = None,
            col: int | None = None,
            rowspan: int = 1,
            colspan: int = 1) -> PlotItem:
        item = PlotItem()
        self._plot_items.append(item)
        self.layoutwidget.addItem(item._graphics, row, col, rowspan, colspan)
        item._update_scene()
        if self._sharex and len(self._plot_items) > 1:
            item._viewbox.setXLink(self._plot_items[0]._viewbox)
        if self._sharey and len(self._plot_items) > 1:
            item._viewbox.setYLink(self._plot_items[0]._viewbox)
        return item

    def __getitem__(self, k: int) -> PlotItem:
        return self._plot_items[k]
    
    def __delitem__(self, k: int):
        item = self._plot_items[k]
        self.layoutwidget.removeItem(item._graphics)
    
    def __iter__(self) -> Iterator[PlotItem]:
        return iter(self._plot_items)
    

class QtMultiImageCanvas(FreeWidget):
    def __init__(self, 
                 nrows: int = 0,
                 ncols: int = 0,
                 sharex: bool = False,
                 sharey: bool = False,
                 **kwargs):
        """
        Multi-plot ``pyqtgraph`` canvas widget.

        Parameters
        ----------
        nrows : int, default is 0
            Initial rows of plots.
        ncols : int, default is 0
            Initail columns of plots.
        sharex : bool, default is False
            If true, all the x-axes will be linked.
        sharey : bool, default is False
            If true, all the y-axes will be linked.
        """
        self.layoutwidget = pg.GraphicsLayoutWidget()
        self._plot_items: list[ImageItem] = []
        self._sharex = sharex
        self._sharey = sharey
        
        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)
        
        if nrows * ncols > 0:
            for r in range(nrows):
                for c in range(ncols):
                    self.add(r, c)
    
    def add(self, 
            row: int | None = None,
            col: int | None = None,
            rowspan: int = 1,
            colspan: int = 1) -> ImageItem:
        item = ImageItem()
        self._plot_items.append(item)
        self.layoutwidget.addItem(item._graphics, row, col, rowspan, colspan)
        item._update_scene()
        if self._sharex and len(self._plot_items) > 1:
            item._viewbox.setXLink(self._plot_items[0]._viewbox)
        if self._sharey and len(self._plot_items) > 1:
            item._viewbox.setYLink(self._plot_items[0]._viewbox)
        return item

    def __getitem__(self, k: int) -> PlotItem:
        return self._plot_items[k]
    
    def __delitem__(self, k: int):
        item = self._plot_items[k]
        self.layoutwidget.removeItem(item._graphics)
    
    def __iter__(self) -> Iterator[PlotItem]:
        return iter(self._plot_items)

def _check_xy(x, y):
    if y is None:
        if x is None:
            x = []
            y = []
        else:
            y = x
            x = np.arange(len(y))
    
    return x, y
    
def _check_colors(face_color, edge_color, color):
    if color is None:
        return face_color, edge_color
    else:
        if face_color is None and edge_color is None:
            return color, color
        else:
            raise ValueError("Cannot set 'color' and either 'face_color' or "
                             "'edge_color' at the same time.")