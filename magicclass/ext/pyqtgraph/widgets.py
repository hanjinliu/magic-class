from __future__ import annotations
import warnings
import pyqtgraph as pg
from pyqtgraph import colormap as cmap
from typing import (
    Callable,
    Generic,
    Iterator,
    Sequence,
    TypeVar,
    overload,
    MutableSequence,
)
import numpy as np

from .components import Grid, Legend, Region, ScaleBar, TextItem
from .graph_items import (
    BarPlot,
    Curve,
    FillBetween,
    InfLine,
    InfCurve,
    LayerItem,
    Scatter,
    Histogram,
    Target,
    TextGroup,
)
from .mouse_event import MouseClickEvent

from psygnal import Signal, SignalInstance

from magicclass.ext._shared_utils import convert_color_code, to_rgba
from magicclass.ext._doc import write_docs
from magicclass.widgets.utils import FreeWidget
from magicclass._app import get_app

BOTTOM = "bottom"
LEFT = "left"


class LayerList(MutableSequence[LayerItem]):
    """A napari-like layer list for plot item handling."""

    def __init__(self, parent: HasDataItems):
        self.parent = parent

    def __repr__(self) -> str:
        if len(self) == 0:
            return f"{type(self).__name__}()"
        s = ",\n\t".join(repr(layer) for layer in self)
        return f"{type(self).__name__}(\n\t{s}\n)"

    def __getitem__(self, key: int | str) -> LayerItem:
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

    def append(self, item: LayerItem) -> None:
        if not isinstance(item, LayerItem):
            raise TypeError(f"Cannot append type {type(item)}.")
        self.parent._add_item(item)
        return None

    def insert(self, pos: int, item: LayerItem) -> None:
        if not isinstance(item, LayerItem):
            raise TypeError(f"Cannot insert type {type(item)}.")
        self.parent._insert_item(pos, item)
        return None

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
    _items: list[LayerItem]

    @property
    def _graphics(self) -> pg.GraphicsWidget:
        """Target widget to add graphics items."""
        raise NotImplementedError()

    @property
    def layers(self) -> LayerList:
        return LayerList(self)

    @write_docs
    def add_curve(
        self,
        x: Sequence[float] | None = None,
        y: Sequence[float] | None = None,
        face_color=None,
        edge_color=None,
        color=None,
        size: float = 7,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
        symbol: str = None,
    ) -> Curve:
        """
        Add a line plot like ``plt.plot(x, y)``.

        Parameters
        ----------
        {x}{y}{face_color}{edge_color}{color}
        size: float, default is 7
            Symbol size.
        {name}{lw}{ls}{symbol}

        Returns
        -------
        Curve
            A plot item of a curve.
        """
        x, y = _check_xy(x, y)
        name = self._find_unique_name(name or "Curve")
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = Curve(
            x,
            y,
            face_color=face_color,
            edge_color=edge_color,
            size=size,
            name=name,
            lw=lw,
            ls=ls,
            symbol=symbol,
        )
        self._add_item(item)
        return item

    @write_docs
    def add_scatter(
        self,
        x: Sequence[float] | None = None,
        y: Sequence[float] | None = None,
        face_color=None,
        edge_color=None,
        color=None,
        size: float = 7,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
        symbol="o",
    ) -> Scatter:
        """
        Add scatter plot like ``plt.scatter(x, y)``.

        Parameters
        ----------
        {x}{y}{face_color}{edge_color}{color}
        size: float, default is 7
            Symbol size.
        {name}{lw}{ls}{symbol}

        Returns
        -------
        Scatter
            A plot item of the scatter plot.
        """
        x, y = _check_xy(x, y)
        name = self._find_unique_name(name or "Scatter")
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = Scatter(
            x,
            y,
            face_color=face_color,
            edge_color=edge_color,
            size=size,
            name=name,
            lw=lw,
            ls=ls,
            symbol=symbol,
        )
        self._add_item(item)
        return item

    @write_docs
    def add_hist(
        self,
        data: Sequence[float],
        bins: int | Sequence | str = 10,
        range=None,
        density: bool = False,
        face_color=None,
        edge_color=None,
        color=None,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
    ) -> Histogram:
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
        {face_color}{edge_color}{color}{name}{lw}{ls}

        Returns
        -------
        Histogram
            A plot item of the histogram.
        """
        name = self._find_unique_name(name or "Histogram")
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = Histogram(
            data,
            bins=bins,
            range=range,
            density=density,
            face_color=face_color,
            edge_color=edge_color,
            name=name,
            lw=lw,
            ls=ls,
        )
        self._add_item(item)
        return item

    @write_docs
    def add_bar(
        self,
        x: Sequence[float] | None = None,
        y: Sequence[float] | None = None,
        width: float = 0.6,
        face_color=None,
        edge_color=None,
        color=None,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
    ) -> BarPlot:
        """
        Add a bar plot like ``plt.bar(x, y)``.

        Parameters
        ----------
        {x}{y}
        width : float, default is 0.6
            Width of each bar.
        {face_color}{edge_color}{color}{name}{lw}{ls}

        Returns
        -------
        BarPlot
            A plot item of the bar plot.
        """
        x, y = _check_xy(x, y)
        name = self._find_unique_name(name or "Bar")
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = BarPlot(
            x,
            y,
            width=width,
            face_color=face_color,
            edge_color=edge_color,
            name=name,
            lw=lw,
            ls=ls,
        )
        self._add_item(item)
        return item

    @write_docs
    def add_fillbetween(
        self,
        x: Sequence[float] | None = None,
        y1: Sequence[float] | None = None,
        y2: Sequence[float] | None = None,
        face_color=None,
        edge_color=None,
        color=None,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
    ) -> FillBetween:
        x, y1 = _check_xy(x, y1)
        name = self._find_unique_name(name or "FillBetween")
        face_color, edge_color = _check_colors(face_color, edge_color, color)

        item = FillBetween(
            x,
            y1,
            y2,
            face_color=face_color,
            edge_color=edge_color,
            name=name,
            lw=lw,
            ls=ls,
        )
        self._add_item(item)
        return item

    @overload
    def add_infline(
        self,
        slope: float,
        intercept: float,
        color=None,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
    ) -> InfLine:
        ...

    @overload
    def add_infline(
        self,
        pos: tuple[float, float],
        degree: float,
        color=None,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
    ) -> InfLine:
        ...

    def add_infline(
        self,
        *args,
        color=None,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
        **kwargs,
    ) -> InfLine:
        if kwargs:
            if "angle" in kwargs:
                # backward compatibility
                warnings.warn(
                    "`angle` keyword argument is deprecated. Please use `degree` instead."
                )
                kwargs["degree"] = kwargs.pop("angle")
            if len(args) == 1:
                if "degree" in kwargs:
                    kwargs["pos"] = args[0]
                elif "intercept" in kwargs:
                    kwargs["slope"] = args[0]
                else:
                    raise ValueError(f"{args=}, {kwargs=} is invalid input.")
            elif len(args) == 2:
                raise ValueError(f"{args=}, {kwargs=} is invalid input.")
            keys = set(kwargs.keys())
            if keys <= {"pos", "degree"}:
                args = (kwargs.get("pos", (0, 0)), kwargs.get("degree", 0))
            elif keys <= {"slope", "intercept"}:
                args = (kwargs.get("slope", (0, 0)), kwargs.get("intercept", 0))
            else:
                raise ValueError(f"{kwargs} is invalid input.")

        nargs = len(args)
        if nargs == 1:
            arg0 = args[0]
            if np.isscalar(arg0):
                angle = np.rad2deg(np.arctan(arg0))
                pos = (0, 0)
            else:
                pos = arg0
                angle = 90
        elif nargs == 2:
            arg0, arg1 = args
            if np.isscalar(arg0):
                angle = np.rad2deg(np.arctan(arg0))
                pos = (0, arg1)
            else:
                pos = arg0
                angle = arg1
        else:
            raise TypeError(
                "Arguments of 'add_infline' should be either 'add_infline(slope, intercept)' "
                "or 'add_infline(pos, degree)'."
            )

        item = InfLine(pos, angle, edge_color=color, name=name, lw=lw, ls=ls)
        self._add_item(item)
        return item

    @write_docs
    def add_infcurve(
        self,
        func: Callable[[np.ndarray], np.ndarray],
        face_color=None,
        edge_color=None,
        color=None,
        size: float = 7,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
        symbol: str = None,
    ) -> Curve:
        """
        Add a function and plot it.

        Parameters
        ----------
        func : callable
            A function that takes a 1-D array and returns a 1-D array.
        {face_color}{edge_color}{color}
        size: float, default is 7
            Symbol size.
        {name}{lw}{ls}{symbol}

        Returns
        -------
        Curve
            A plot item of a curve.
        """
        name = self._find_unique_name(name or "InfCurve")
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        item = InfCurve(
            func,
            face_color=face_color,
            edge_color=edge_color,
            size=size,
            name=name,
            lw=lw,
            ls=ls,
            symbol=symbol,
        )
        self._add_item(item)
        if xlim := getattr(self, "xlim", None):
            self.xlim = xlim
        return item

    @overload
    def add_text(
        self,
        x: float,
        y: float,
        text: str,
        color=None,
        name: str | None = None,
        size: float = 9.0,
        anchor: tuple[float, float] = (0.0, 0.0),
    ) -> TextGroup:
        ...

    @overload
    def add_text(
        self,
        x: Sequence[float],
        y: Sequence[float],
        text: Sequence[str],
        color=None,
        name: str | None = None,
        size: float = 9.0,
        anchor: tuple[float, float] = (0.0, 0.0),
    ) -> TextGroup:
        ...

    def add_text(
        self,
        x,
        y,
        text,
        color=None,
        name=None,
        size: int = 9,
        anchor: tuple[float, float] = (0.0, 0.0),
    ) -> TextGroup:
        if np.isscalar(x) and np.isscalar(y):
            x = [x]
            y = [y]
            text = [text]
        item = TextGroup(x, y, text, color, name, size=size, anchor=anchor)
        self._add_item(item)
        return item

    def add_target(self, pos, size: int = 10, color=None, name=None) -> Target:
        item = Target(pos, size=size, edge_color=color, name=name)
        self._add_item(item)
        return item

    def _add_item(self, item: LayerItem):
        item.zorder = len(self._items)
        self._graphics.addItem(item.native)
        self._items.append(item)

    def _insert_item(self, pos: int, item: LayerItem):
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

    def _remove_item(self, item: LayerItem | int | str):
        if isinstance(item, LayerItem):
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


class SignalCompat:
    def __init__(self, signal: SignalInstance, name: str):
        self.signal = signal
        self.name = name

    def _warn(self):
        warnings.warn(
            f"Use of `{self.name}.append` is deprecated. Please use `{self.signal.name}.connect` instead.",
            DeprecationWarning,
        )

    def append(self, slot):
        self._warn()
        self.signal.connect(slot)


class HasViewBox(HasDataItems):
    range_changed = Signal(object)
    mouse_clicked = Signal(MouseClickEvent)

    def __init__(self, viewbox: pg.ViewBox):
        self._viewbox = viewbox
        self._items: list[LayerItem] = []

        # prepare mouse event
        self.mouse_click_callbacks = SignalCompat(
            self.mouse_clicked, "mouse_click_callbacks"
        )

        # This ROI is not editable. Mouse click event will use it to determine
        # the origin of the coordinate system.
        self._coordinate_fiducial = pg.ROI((0, 0))
        self._coordinate_fiducial.setVisible(False)
        self._viewbox.addItem(self._coordinate_fiducial, ignoreBounds=True)

        self._enabled = True

    def _mouse_clicked(self, e):
        # NOTE: Mouse click event needs a reference item to map coordinates.
        # Here plot items always have a linear region item as a default one,
        # we can use it as the referene.
        ev = MouseClickEvent(e, self._coordinate_fiducial)
        x, y = ev.pos()
        [xmin, xmax], [ymin, ymax] = self._viewbox.viewRange()

        if xmin <= x <= xmax and ymin <= y <= ymax:
            self.mouse_clicked.emit(ev)

    def _range_changed(self):
        self.range_changed.emit(self._viewbox.viewRange())

    @property
    def xlim(self):
        """Range limits of X-axis."""
        (xmin, xmax), _ = self._viewbox.viewRange()
        return xmin, xmax

    @xlim.setter
    def xlim(self, value: tuple[float, float]):
        self._viewbox.setXRange(*value)

    @property
    def ylim(self):
        """Range limits of Y-axis."""
        _, (ymin, ymax) = self._viewbox.viewRange()
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

    def _update_scene(self):
        raise NotImplementedError()

    @property
    def border(self):
        return to_rgba(self._viewbox.border)

    @border.setter
    def border(self, value):
        value = convert_color_code(value)
        self._viewbox.setBorder(value)

    def auto_range(self):
        self._viewbox.autoRange()


class SimpleViewBox(HasViewBox):
    def __init__(self):
        super().__init__(pg.ViewBox())

    @property
    def _graphics(self):
        return self._viewbox


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
        self._legend.native.setParentItem(self._viewbox)
        self.pgitem.legend = self._legend.native

        # initialize private attributes
        self._xlabel = ""
        self._ylabel = ""

    @property
    def _graphics(self):
        return self.pgitem

    @property
    def region(self) -> Region:
        """Linear region item."""
        return self._region

    @property
    def legend(self) -> Legend:
        """Legend item."""
        return self._legend

    @property
    def xlabel(self) -> str:
        """Label of X-axis."""
        return self._xlabel

    @xlabel.setter
    def xlabel(self, label: str):
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

    @property
    def title(self) -> str:
        """Title text of the graph."""
        return self.pgitem.titleLabel.text

    @title.setter
    def title(self, value: str):
        value = str(value)
        self.pgitem.setTitle(value)

    def show_grid(self, x: bool = True, y: bool = True, alpha: float | None = None):
        """Show grid lines."""
        self.pgitem.showGrid(x, y, alpha=alpha)

    def _update_scene(self):
        # Since plot item does not have graphics scene before being added to
        # a graphical layout, mouse event should be connected afterward.
        self.pgitem.scene().sigMouseClicked.connect(self._mouse_clicked)
        self.pgitem.sigRangeChanged.connect(self._range_changed)


class ViewBoxExt(pg.ViewBox):
    def __init__(
        self,
        parent=None,
        border=None,
        lockAspect=False,
        enableMouse=True,
        invertY=False,
        enableMenu=True,
        name=None,
        invertX=False,
        defaultPadding=0.02,
    ):
        pg.ViewBox.__init__(**locals())
        from pyqtgraph import icons

        self.button = pg.ButtonItem(icons.getGraphPixmap("ctrl"), 14, self)
        self.button.hide()

    def hoverEvent(self, ev):
        try:
            if ev.enter:
                self.button.show()
            if ev.exit:
                self.button.hide()
        except RuntimeError:
            pass


class ImageItem(HasViewBox):
    def __init__(
        self, viewbox: pg.ViewBox | None = None, lock_contrast_limits: bool = False
    ):
        if viewbox is None:
            viewbox = ViewBoxExt(lockAspect=True, invertY=True)
        self._lock_contrast_limits = lock_contrast_limits
        super().__init__(viewbox)
        self._image_item = pg.ImageItem()
        tr = self._image_item.transform().translate(-0.5, -0.5)
        self._image_item.setTransform(tr)

        self._viewbox.addItem(self._image_item)

        # prepare text overlay
        self._text_overlay = TextItem(text="", color="gray")
        self._text_overlay.native.setParentItem(self._viewbox)

        # prepare scale bar
        self._scale_bar = ScaleBar()
        self._scale_bar.visible = False
        self._scale_bar.native.setParentItem(self._viewbox)
        self._scale_bar.native.anchor((1, 1), (1, 1), offset=(-20, -20))

        # prepare title and labels
        self._title = TextItem(text="", color="white", anchor=(0.5, 1.1))
        self._title.pos = [1, 0]
        self._viewbox.addItem(self._title.native)
        self._title.visible = False

        self._xlabel = TextItem(text="", color="white", anchor=(0.5, -0.1))
        self._xlabel.pos = [1, 1]
        self._viewbox.addItem(self._xlabel.native)
        self._xlabel.visible = False

        self._ylabel = TextItem(text="", color="white", anchor=(0.5, 1.1), angle=90)
        self._ylabel.pos = [0, 1]
        self._viewbox.addItem(self._ylabel.native)
        self._ylabel.visible = False

        if isinstance(viewbox, ViewBoxExt):
            # prepare LUT histogram
            self._hist = pg.HistogramLUTItem(orientation="horizontal")
            self._hist.vb.setBackgroundColor([0, 0, 0, 0.2])
            self._hist.setParentItem(self._viewbox)
            self._hist.setVisible(False)

            @viewbox.button.clicked.connect
            def _(e):
                visible = not self._hist.isVisible()
                self._hist.setVisible(visible)
                if visible:
                    self._hist._updateView()
                    width = min(160, self._viewbox.width())
                    self._hist.setFixedWidth(width)

        self._cmap = "gray"

    def _update_scene(self):
        # Since plot item does not have graphics scene before being added to
        # a graphical layout, mouse event should be connected afterward.
        self._image_item.scene().sigMouseClicked.connect(self._mouse_clicked)
        self._viewbox.sigRangeChanged.connect(self._range_changed)

    @property
    def text_overlay(self) -> TextItem:
        """Text overlay on the image."""
        return self._text_overlay

    @property
    def title(self) -> str:
        """Title text of the graph."""
        return self._title.text

    @title.setter
    def title(self, value: str):
        self._title.text = value

    @property
    def xlabel(self) -> str:
        """Label of X-axis."""
        return self._xlabel.text

    @xlabel.setter
    def xlabel(self, value: str):
        self._xlabel.text = value

    @property
    def ylabel(self) -> str:
        """Label of Y-axis."""
        return self._ylabel.text

    @xlabel.setter
    def ylabel(self, value: str):
        self._ylabel.text = value

    @property
    def scale_bar(self) -> ScaleBar:
        """Scale bar on the image."""
        return self._scale_bar

    @property
    def lock_contrast_limits(self):
        """True if enable auto-contrast."""
        return self._lock_contrast_limits

    @lock_contrast_limits.setter
    def lock_contrast_limits(self, value: bool):
        self._lock_contrast_limits = bool(value)

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
        no_image = self._image_item.image is None
        if no_image:
            auto_levels = True
        else:
            auto_levels = not self._lock_contrast_limits
            clims = self.contrast_limits
        img = np.asarray(image)
        self._image_item.setImage(img.T, autoLevels=auto_levels)
        self._hist.setImageItem(self._image_item)
        self._hist._updateView()
        if no_image:
            self._viewbox.autoRange()
        if not auto_levels:
            self.contrast_limits = clims
        sy, sx = img.shape[-2:]
        self._title.pos = [sx / 2, self._title.pos[1]]
        self._title.visible = True
        self._xlabel.pos = [sx / 2, sy]
        self._xlabel.visible = True
        self._ylabel.pos = [0, sy / 2]
        self._ylabel.visible = True

    @image.deleter
    def image(self):
        self._image_item.clear()
        self._title.visible = False
        self._xlabel.visible = False
        self._ylabel.visible = False

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


class HasBackground(FreeWidget):
    @property
    def background_color(self):
        return self.layoutwidget._background

    @background_color.setter
    def background_color(self, value):
        value = convert_color_code(value)
        self.layoutwidget.setBackground(value)


class QtPlotCanvas(HasBackground, PlotItem):
    """A 1-D data viewer that have similar API as napari Viewer."""

    def __init__(self, **kwargs):
        app = get_app()
        # prepare widget
        PlotItem.__init__(self)
        self.layoutwidget = pg.GraphicsLayoutWidget()
        self.layoutwidget.addItem(self.pgitem)
        self._update_scene()

        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)


class QtImageCanvas(HasBackground, ImageItem):
    """A 2-D image viewer that have similar API as napari Viewer."""

    def __init__(self, lock_contrast_limits: bool = False, **kwargs):
        app = get_app()
        # prepare widget
        ImageItem.__init__(self, lock_contrast_limits=lock_contrast_limits)
        self.layoutwidget = pg.GraphicsLayoutWidget()
        self.layoutwidget.addItem(self._viewbox)
        self._update_scene()

        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)

    @property
    def background_color(self):
        return self.layoutwidget._background

    @background_color.setter
    def background_color(self, value):
        value = convert_color_code(value)
        self.layoutwidget.setBackground(value)


class Qt2YPlotCanvas(HasBackground):
    """A plot canvas with two Y-axis."""

    def __init__(self, **kwargs):
        app = get_app()
        self.layoutwidget = pg.GraphicsLayoutWidget()

        item_l = PlotItem()
        item_r = SimpleViewBox()

        self.layoutwidget.addItem(item_l.pgitem)

        item_l.pgitem.scene().addItem(item_r._viewbox)
        item_l.pgitem.getAxis("right").linkToView(item_r._viewbox)
        item_r._viewbox.setXLink(item_l.pgitem)

        item_l._update_scene()
        item_l.pgitem.showAxis("right")

        self._plot_items: tuple[PlotItem, SimpleViewBox] = (item_l, item_r)

        self.updateViews()
        item_l.pgitem.vb.sigResized.connect(self.updateViews)

        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)

    def __getitem__(self, k: int) -> PlotItem:
        return self._plot_items[k]

    def updateViews(self):
        item_l, item_r = self._plot_items
        item_r._viewbox.setGeometry(item_l._viewbox.sceneBoundingRect())
        item_r._viewbox.linkedViewChanged(item_l._viewbox, item_r._viewbox.XAxis)


_C = TypeVar("_C", bound=HasViewBox)


class _MultiPlot(HasBackground, Generic[_C]):
    _base_item_class: type[_C]

    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        sharex: bool = False,
        sharey: bool = False,
        **kwargs,
    ):
        """
        Multi-axes ``pyqtgraph`` canvas widget. Can contain multiple objects
        of {cls}.

        Parameters
        ----------
        nrows : int, default is 1
            Initial rows of axes.
        ncols : int, default is 1
            Initail columns of axes.
        sharex : bool, default is False
            If true, all the x-axes will be linked.
        sharey : bool, default is False
            If true, all the y-axes will be linked.
        """
        app = get_app()
        self.layoutwidget = pg.GraphicsLayoutWidget()
        self._axes: list[_C] = []
        self._sharex = sharex
        self._sharey = sharey

        super().__init__(**kwargs)
        self.set_widget(self.layoutwidget)

        if nrows * ncols > 0:
            for r in range(nrows):
                for c in range(ncols):
                    self.addaxis(r, c)
        self._shape = (nrows, ncols)

    def __init_subclass__(cls) -> None:
        """Update doc."""
        init = cls.__init__
        init.__doc__ = init.__doc__.format(cls=cls._base_item_class.__name__)

    def addaxis(
        self,
        row: int | None = None,
        col: int | None = None,
        rowspan: int = 1,
        colspan: int = 1,
    ) -> _C:
        """Add a new axis to widget."""
        item = self._base_item_class()
        self._axes.append(item)
        self.layoutwidget.addItem(item._graphics, row, col, rowspan, colspan)
        item._update_scene()
        if self._sharex and len(self._axes) > 1:
            item._viewbox.setXLink(self._axes[0]._viewbox)
        if self._sharey and len(self._axes) > 1:
            item._viewbox.setYLink(self._axes[0]._viewbox)
        return item

    def __getitem__(self, key: int | tuple[int, int]) -> _C:
        if isinstance(key, tuple):
            r, c = key
            nr, nc = self.shape
            if r >= nr or c >= nc:
                raise IndexError(f"Index out of range: {key}")
            return self._axes[r * nc + c]
        else:
            key = int(key)
        return self._axes[key]

    @property
    def shape(self) -> tuple[int, int]:
        return self._shape

    def __delitem__(self, k: int):
        item = self._axes[k]
        self.layoutwidget.removeItem(item._graphics)

    def __iter__(self) -> Iterator[_C]:
        return iter(self._axes)


class QtMultiPlotCanvas(_MultiPlot[PlotItem]):
    """A pyqtgraph-based canvas with multiple plot."""

    _base_item_class = PlotItem


class QtMultiImageCanvas(_MultiPlot[ImageItem]):
    """A pyqtgraph-based canvas with multiple images."""

    _base_item_class = ImageItem


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
            raise ValueError(
                "Cannot set 'color' and either 'face_color' or "
                "'edge_color' at the same time."
            )
