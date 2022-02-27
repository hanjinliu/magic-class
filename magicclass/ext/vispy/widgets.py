from __future__ import annotations
import numpy as np
from vispy import scene

from ...widgets import FreeWidget


class VispyPlotCanvas(FreeWidget):
    def __init__(self):
        super().__init__()
        self._scene = scene.SceneCanvas()
        grid = self._scene.central_widget.add_grid()
        self._viewbox = grid.add_view(row=0, col=1, camera="panzoom")
        x_axis = scene.AxisWidget(orientation="bottom")
        x_axis.stretch = (1, 0.1)
        grid.add_widget(x_axis, row=1, col=1)
        x_axis.link_view(self._viewbox)
        y_axis = scene.AxisWidget(orientation="left")
        y_axis.stretch = (0.1, 1)
        grid.add_widget(y_axis, row=0, col=0)
        y_axis.link_view(self._viewbox)
        self._items = []

        self._scene.create_native()
        self.set_widget(self._scene.native)

    @property
    def layers(self):
        return self._items

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
        from vispy.scene.visuals import Line

        x, y = _check_xy(x, y)
        face_color, edge_color = _check_colors(face_color, edge_color, color)
        if isinstance(edge_color, np.ndarray) and edge_color.ndim == 1:
            edge_color = np.stack([edge_color] * y.size, axis=0)
        line = Line(
            np.stack([x, y], axis=1),
            color=edge_color,
            parent=self._viewbox.scene,
            width=lw,
        )
        return line


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
