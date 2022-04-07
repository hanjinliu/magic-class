from __future__ import annotations
import numpy as np
from vispy import scene
from vispy.scene import visuals, ViewBox
from .layer2d import Curve, Scatter
from .._doc import write_docs
from ...widgets import FreeWidget


class HasViewBox(FreeWidget):
    def __init__(self, grid_pos: tuple[int, int] = (0, 0), _scene=None, _row=0, _col=0):
        super().__init__()
        if _scene is None:
            _scene = scene.SceneCanvas(keys="interactive")
        self._scene = _scene
        grid = self._scene.central_widget.add_grid(pos=grid_pos)
        grid.spacing = 0
        self._viewbox: ViewBox = grid.add_view(row=_row, col=_col, camera="panzoom")
        self._items = []
        self._grid = grid
        self._scene.create_native()
        self.set_widget(self._scene.native)

    @property
    def xrange(self) -> tuple[float, float]:
        return self._viewbox.camera._xlim

    @xrange.setter
    def xrange(self, rng: tuple[float, float]):
        x0, x1 = rng
        self._viewbox.camera.set_range(x=(x0, x1))

    @property
    def yrange(self) -> tuple[float, float]:
        return self._viewbox.camera._ylim

    @yrange.setter
    def yrange(self, rng: tuple[float, float]):
        y0, y1 = rng
        self._viewbox.camera.set_range(y=(y0, y1))

    @property
    def layers(self):
        return self._items

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
        self._items.append(line)
        if len(self._items) == 1:
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
        {symbol}

        Returns
        -------
        Curve
            A plot item of a curve.
        """
        x, y = _check_xy(x, y)
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        if isinstance(edge_color, np.ndarray) and edge_color.ndim == 1:
            edge_color = np.stack([edge_color] * y.size, axis=0)
        line = Scatter(
            self._viewbox,
            x,
            y,
            face_color=face_color,
            edge_color=edge_color,
            size=size,
            name=name,
            symbol=symbol,
        )
        self._items.append(line)
        if len(self._items) == 1:
            self.xrange = (np.min(x), np.max(x))
            self.yrange = (np.min(y), np.max(y))
        return line


class PlotItem(HasViewBox):
    def __init__(self, grid_pos=(0, 0), _scene=None):
        super().__init__(grid_pos=grid_pos, _scene=_scene, _row=1, _col=1)

        title = scene.Label("", color="white", font_size=7)
        title.height_max = 40
        self._grid.add_widget(title, row=0, col=0, col_span=2)
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
        self._grid.add_widget(x_axis, row=2, col=1)
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
        self._grid.add_widget(y_axis, row=1, col=0)
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


class ImageItem(HasViewBox):
    def __init__(
        self, lock_contrast_limits: bool = False, grid_pos=(0, 0), _scene=None
    ):
        super().__init__(grid_pos=grid_pos, _scene=_scene)
        self._viewbox.camera.aspect = 1.0
        self._viewbox.camera.flip = (False, True, False)
        self._image = visuals.Image(cmap="gray", parent=self._viewbox.scene)
        self._lock_contrast_limits = lock_contrast_limits

    @property
    def image(self):
        return self._image._data

    @image.setter
    def image(self, img):
        self._image.set_data(img)
        if not self._lock_contrast_limits:
            self._image.clim = "auto"

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


class VispyPlotCanvas(PlotItem):
    """
    A Vispy based 2-D plot canvas for curve, histogram, bar plot etc.
    """


class VispyImageCanvas(ImageItem):
    ...


class _MultiPlot(FreeWidget):
    _base_class: type[HasViewBox]

    def __init__(self, nrows: int = 1, ncols: int = 1):
        super().__init__()
        self._canvas = []
        self._scene = scene.SceneCanvas()
        for r in range(nrows):
            for c in range(ncols):
                canvas = self._base_class(grid_pos=(r, c), _scene=self._scene)
                self._canvas.append(canvas)

        self._scene.create_native()
        self.set_widget(self._scene.native)

    def __getitem__(self, i):
        return self._canvas[i]


class VispyMultiPlotCanvas(_MultiPlot):
    _base_class = VispyPlotCanvas


class VispyMultiImageCanvas(_MultiPlot):
    _base_class = VispyImageCanvas


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
