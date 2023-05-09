from __future__ import annotations
import numpy as np

from vispy import scene
from vispy.scene import visuals, ViewBox

from .layer2d import Curve, Scatter, Histogram
from ._base import HasViewBox, SceneCanvas, MultiPlot

from .._doc import write_docs
from magicclass.widgets import FreeWidget
from magicclass._app import get_app


class Has2DViewBox(HasViewBox):
    @property
    def xrange(self) -> tuple[float, float]:
        """Range of X dimension."""
        return self._viewbox.camera._xlim

    @xrange.setter
    def xrange(self, rng: tuple[float, float]):
        x0, x1 = rng
        self._viewbox.camera.set_range(x=(x0, x1))

    @property
    def yrange(self) -> tuple[float, float]:
        """Range of Y dimension."""
        return self._viewbox.camera._ylim

    @yrange.setter
    def yrange(self, rng: tuple[float, float]):
        y0, y1 = rng
        self._viewbox.camera.set_range(y=(y0, y1))

    @write_docs
    def add_curve(
        self,
        x=None,
        y=None,
        face_color=None,
        edge_color=None,
        color=None,
        size: float = 7,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",
        symbol=None,
    ):
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
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        if isinstance(edge_color, np.ndarray) and edge_color.ndim == 1:
            edge_color = np.stack([edge_color] * y.size, axis=0)
        line = Curve(
            self._viewbox,
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
        self._layerlist.append(line)
        if len(self._layerlist) == 1:
            self.xrange = (np.min(x), np.max(x))
            self.yrange = (np.min(y), np.max(y))
        return line

    @write_docs
    def add_scatter(
        self,
        x=None,
        y=None,
        face_color=None,
        edge_color=None,
        color=None,
        size: float = 7,
        name: str | None = None,
        symbol=None,
    ):
        """
        Add a scatter plot like ``plt.scatter(x, y)``.

        Parameters
        ----------
        {x}{y}{face_color}{edge_color}{color}
        size: float, default is 7
            Symbol size.
        {name}{symbol}

        Returns
        -------
        Scatter
            A plot item of a scatter.
        """
        x, y = _check_xy(x, y)
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        if isinstance(edge_color, np.ndarray) and edge_color.ndim == 1:
            edge_color = np.stack([edge_color] * y.size, axis=0)
        scatter = Scatter(
            self._viewbox,
            x,
            y,
            face_color=face_color,
            edge_color=edge_color,
            size=size,
            name=name,
            symbol=symbol,
        )
        self._layerlist.append(scatter)
        if len(self._layerlist) == 1:
            self.xrange = (np.min(x), np.max(x))
            self.yrange = (np.min(y), np.max(y))
        return scatter

    @write_docs
    def add_hist(
        self,
        data,
        bins: int = 10,
        face_color=None,
        edge_color=None,
        color="white",
        name: str | None = None,
    ) -> Histogram:
        """
        Add a histogram like ``plt.hist(x)``.

        Parameters
        ----------
        data: array-like
            Input 1D data.
        bins: int, default is 10
            Number of bins to draw the histogram.
        {face_color}{edge_color}{color}{name}

        Returns
        -------
        Histogram
            A plot item of a histogram.
        """
        data = np.asarray(data)
        face_color, edge_color = _check_colors(face_color, edge_color, color)

        hist = Histogram(
            self._viewbox,
            data=data,
            bins=bins,
            face_color=face_color,
            edge_color=edge_color,
            name=name,
        )
        self._layerlist.append(hist)
        if len(self._layerlist) == 1:
            self.xrange = (np.min(data), np.max(data))
        return hist


class PlotItem(Has2DViewBox):
    def __init__(self, viewbox: ViewBox):
        grid = viewbox.add_grid()
        grid.spacing = 0
        _viewbox = grid.add_view(row=1, col=1, camera="panzoom")
        super().__init__(_viewbox)

        title = scene.Label("", color="white", font_size=7)
        title.height_max = 40
        grid.add_widget(title, row=0, col=0, col_span=2)
        self._title = title
        x_axis = scene.AxisWidget(
            orientation="bottom",
            anchors=("center", "bottom"),
            font_size=6,
            axis_label_margin=40,
            tick_label_margin=5,
            axis_label="",
        )
        x_axis.height_min = 65
        x_axis.height_max = 80
        x_axis.stretch = (1, 0.1)
        self._x_axis = x_axis
        grid.add_widget(x_axis, row=2, col=1)
        x_axis.link_view(self._viewbox)
        y_axis = scene.AxisWidget(
            orientation="left",
            anchors=("right", "middle"),
            font_size=6,
            axis_label_margin=50,
            tick_label_margin=5,
            axis_label="",
        )
        y_axis.width_max = 80
        y_axis.stretch = (0.1, 1)
        grid.add_widget(y_axis, row=1, col=0)
        y_axis.link_view(self._viewbox)
        self._y_axis = y_axis

    @property
    def title(self) -> str:
        """The title string."""
        return self._title.text

    @title.setter
    def title(self, text: str):
        self._title.text = text

    @property
    def xlabel(self) -> str:
        """The x-label string."""
        return self._x_axis.axis.axis_label

    @xlabel.setter
    def xlabel(self, text: str):
        self._x_axis.axis.axis_label = text
        height = self._x_axis.height
        if text:
            self._x_axis.size = (height, 75.0)
        else:
            self._x_axis.size = (height, 75.0)

    @property
    def ylabel(self) -> str:
        """The y-label string."""
        return self._y_axis.axis.axis_label

    @xlabel.setter
    def ylabel(self, text: str):
        self._y_axis.axis.axis_label = text


class ImageItem(Has2DViewBox):
    def __init__(
        self,
        viewbox: ViewBox | None = None,
        lock_contrast_limits: bool = False,
    ):
        grid = viewbox.add_grid()
        grid.spacing = 0
        _viewbox = grid.add_view(row=1, col=1, camera="panzoom")
        super().__init__(_viewbox)

        self._viewbox.camera.aspect = 1.0
        self._viewbox.camera.flip = (False, True, False)

        self._image = visuals.Image(cmap="gray", parent=self._viewbox.scene)
        self._lock_contrast_limits = lock_contrast_limits

        title = scene.Label("", color="white", font_size=7)
        title.height_max = 40
        grid.add_widget(title, row=0, col=0, col_span=2)
        self._title = title
        x_axis = scene.Label("", color="white", font_size=7)
        x_axis.height_min = 35
        x_axis.height_max = 40
        x_axis.stretch = (1, 0.1)
        self._x_axis = x_axis
        grid.add_widget(x_axis, row=2, col=1)

        y_axis = scene.Label("", rotation=-90, color="white", font_size=7)
        y_axis.width_max = 40
        y_axis.stretch = (0.1, 1)
        grid.add_widget(y_axis, row=1, col=0)

        self._y_axis = y_axis

    @property
    def image(self):
        return self._image._data

    @image.setter
    def image(self, img):
        no_image = self._image._data is None
        if isinstance(img, np.ndarray):
            if img.dtype == "float64":
                img = img.astype("float32")
        else:
            img = np.asarray(img, dtype=np.float32)

        self._image.set_data(img)
        if not self._lock_contrast_limits:
            self._image.clim = "auto"
        if no_image:
            self.yrange = (0, self._image._data.shape[0])
            self.xrange = (0, self._image._data.shape[1])

    @image.deleter
    def image(self):
        self._image._data = None
        self._image.update()

    @property
    def cmap(self):
        return self._image.cmap

    @cmap.setter
    def cmap(self, c):
        self._image.cmap = c

    @property
    def title(self) -> str:
        """The title string."""
        return self._title.text

    @title.setter
    def title(self, text: str):
        self._title.text = text

    @property
    def xlabel(self) -> str:
        """The x-label string."""
        return self._x_axis.text

    @xlabel.setter
    def xlabel(self, text: str):
        self._x_axis.text = text

    @property
    def ylabel(self) -> str:
        """The y-label string."""
        return self._y_axis.text

    @xlabel.setter
    def ylabel(self, text: str):
        self._y_axis.text = text

    @property
    def contrast_limits(self) -> tuple[float, float]:
        """Contrast limits of the image."""
        return self._image.clim

    @contrast_limits.setter
    def contrast_limits(self, val: tuple[float, float]):
        self._image.clim = val


class VispyPlotCanvas(FreeWidget, PlotItem):
    """A Vispy based 2-D plot canvas for curve, histogram, bar plot etc."""

    def __init__(self, **kwargs):
        app = get_app()

        # prepare widget
        _scene = SceneCanvas(keys="interactive")
        _scene.create_native()
        viewbox = _scene.central_widget.add_view()
        PlotItem.__init__(self, viewbox)
        super().__init__(**kwargs)
        self.set_widget(_scene.native)


class VispyImageCanvas(FreeWidget, ImageItem):
    """A Vispy based 2-D plot canvas for images."""

    def __init__(self, **kwargs):
        app = get_app()

        # prepare widget
        _scene = SceneCanvas(keys="interactive")
        _scene.create_native()
        viewbox = _scene.central_widget.add_view()
        ImageItem.__init__(self, viewbox)
        super().__init__(**kwargs)
        self.set_widget(_scene.native)


class VispyMultiPlotCanvas(MultiPlot):
    """A multiple Vispy based 2-D plot canvas."""

    _base_class = PlotItem


class VispyMultiImageCanvas(MultiPlot):
    """A multiple Vispy based 2-D plot canvas for images."""

    _base_class = ImageItem


def _check_xy(x, y):
    if y is None:
        if x is None:
            x = np.array([])
            y = np.array([])
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
