from __future__ import annotations
import numpy as np
from numpy.typing import ArrayLike
from vispy.scene import visuals, ViewBox
from ._base import LayerItem

_SYMBOL_MAP = {
    "s": "square",
    "D": "diamond",
}


class Curve(LayerItem):
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
