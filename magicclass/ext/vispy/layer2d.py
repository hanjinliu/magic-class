from __future__ import annotations
from typing import Sequence
import numpy as np
from numpy.typing import ArrayLike
from vispy.scene import visuals, ViewBox
from vispy.color import get_color_dict
from ._base import LayerItem
from .._shared_utils import convert_color_code, to_rgba


_SYMBOL_MAP = {
    "s": "square",
    "D": "diamond",
}


class PlotDataLayer(LayerItem):
    _visual: visuals.LinePlot | visuals.Markers
    _data: np.ndarray

    @property
    def xdata(self) -> np.ndarray:
        return self._data[:, 0]

    @xdata.setter
    def xdata(self, value: Sequence[float]):
        x = np.atleast_2d(value)
        y = self._data[:, 1]
        self._visual.set_data(np.concatenate([x, y], axis=1))

    @property
    def ydata(self) -> np.ndarray:
        return self._data[:, 1]

    @ydata.setter
    def ydata(self, value: Sequence[float]):
        x = self._data[:, 0]
        y = np.atleast_2d(value)
        self._visual.set_data(np.concatenate([x, y], axis=1))

    @property
    def ndata(self) -> int:
        return self.xdata.size

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = str(value)

    def add(self, points: np.ndarray | Sequence):
        """Add new points to the plot data item."""
        points = np.atleast_2d(points)
        if points.shape[1] != 2:
            raise ValueError("Points must be of the shape (N, 2).")
        data = np.concatenate([self._data, points], axis=1)
        self._visual.set_data(data)
        return None

    def remove(self, i: int | Sequence[int]):
        """Remove the i-th data."""
        if isinstance(i, int):
            i = [i]
        sl = list(set(range(self.ndata)) - set(i))
        x = self.xdata[sl]
        y = self.ydata[sl]
        self._visual.set_data(np.concatenate([x, y], axis=1))
        return None

    @property
    def edge_color(self) -> np.ndarray:
        """Edge color of the data."""
        col = self._visual._line.color
        return to_rgba(col)

    @edge_color.setter
    def edge_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self._visual.set_data(edge_color=value)

    @property
    def face_color(self) -> np.ndarray:
        """Face color of the data."""
        col = self._visual._markers._data["face_color"]
        return to_rgba(col)

    @face_color.setter
    def face_color(self, value: str | Sequence):
        value = convert_color_code(value)
        self._visual.set_data(face_color=value)

    color = property()

    @color.setter
    def color(self, value: str | Sequence):
        """Set face color and edge color at the same time."""
        self.face_color = value
        self.edge_color = value


class Curve(PlotDataLayer):
    def __init__(
        self,
        viewbox: ViewBox,
        x: ArrayLike,
        y: ArrayLike = None,
        face_color=None,
        edge_color=None,
        size: float = 7,
        name: str | None = None,
        lw: float = 1,
        ls: str = "-",  # not implemented yet
        symbol=None,
    ) -> None:
        symbol = _SYMBOL_MAP.get(symbol, symbol)
        if symbol is None:
            face_color = None
        self._viewbox = viewbox
        self._visual = visuals.LinePlot(
            np.stack([x, y], axis=1),
            color=edge_color,
            symbol=symbol,
            parent=self._viewbox.scene,
            width=lw,
            marker_size=size,
            face_color=face_color,
            edge_color=face_color,
        )
        self._name = name
        self._visual.update()


class Scatter(PlotDataLayer):
    def __init__(
        self,
        viewbox: ViewBox,
        x: ArrayLike,
        y: ArrayLike = None,
        face_color=None,
        edge_color=None,
        size: float = 7,
        name: str | None = None,
        symbol="o",
    ) -> None:
        symbol = _SYMBOL_MAP.get(symbol, symbol)
        self._viewbox = viewbox
        self._visual = visuals.Markers(
            pos=np.stack([x, y], axis=1),
            symbol=symbol,
            parent=self._viewbox.scene,
            size=size,
            face_color=face_color,
            edge_color=edge_color,
        )
        self._name = name
        self._visual.update()


class Histogram(LayerItem):
    def __init__(
        self,
        viewbox: ViewBox,
        data: np.ndarray,
        bins: int = 10,
        face_color=None,
        edge_color=None,
        name: str | None = None,
    ) -> None:
        self._viewbox = viewbox
        self._visual = visuals.Histogram(
            data,
            bins=bins,
            # color=edge_color,
            parent=self._viewbox.scene,
        )

        if isinstance(face_color, str):
            rgb_html = get_color_dict()[face_color][1:]
            face_color = np.array(
                [
                    int(rgb_html[0:2], 16) / 255,
                    int(rgb_html[2:4], 16) / 255,
                    int(rgb_html[4:6], 16) / 255,
                ]
            )

        if isinstance(edge_color, str):
            rgb_html = get_color_dict()[edge_color][1:]
            edge_color = np.array(
                [
                    int(rgb_html[0:2], 16) / 255,
                    int(rgb_html[2:4], 16) / 255,
                    int(rgb_html[4:6], 16) / 255,
                ]
            )

        self._visual.mesh_data.set_face_colors(
            np.stack([face_color] * self._visual.mesh_data.n_faces, axis=0)
        )
        self._visual.mesh_data.set_vertex_colors(
            np.stack([edge_color] * self._visual.mesh_data.n_vertices, axis=0)
        )
        self._visual.mesh_data_changed()

        self._name = name
        self._visual.update()

    @property
    def name(self):
        return self._name
