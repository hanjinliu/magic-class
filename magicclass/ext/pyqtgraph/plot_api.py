from __future__ import annotations

from typing import overload, TYPE_CHECKING, Sequence
import numpy as np
from .widgets import QtPlotCanvas, QtMultiPlotCanvas, QtImageCanvas

if TYPE_CHECKING:
    from .widgets import HasViewBox, _MultiPlot

CURRENT_MULTI_CANVAS: _MultiPlot | None = None
CURRENT_CANVAS: HasViewBox | None = None


def gca() -> QtPlotCanvas:
    global CURRENT_CANVAS
    if CURRENT_CANVAS is None:
        CURRENT_CANVAS = QtPlotCanvas()
    return CURRENT_CANVAS


def _set_current_canvas(canvas: HasViewBox) -> HasViewBox:
    global CURRENT_CANVAS
    CURRENT_CANVAS = canvas
    return canvas


def _set_current_multi_canvas(multi):
    global CURRENT_MULTI_CANVAS
    CURRENT_MULTI_CANVAS = multi
    return multi


def gcf() -> _MultiPlot | QtPlotCanvas:
    if CURRENT_MULTI_CANVAS is None:
        return gca()
    return CURRENT_MULTI_CANVAS


gcw = gcf


def figure() -> QtPlotCanvas:
    _set_current_canvas(QtPlotCanvas())
    return CURRENT_CANVAS


@overload
def subplot(pos: int) -> HasViewBox:
    ...


@overload
def subplot(row: int, col: int, idx: int) -> HasViewBox:
    ...


def subplot(*args):
    if len(args) == 1 and args[0] >= 111:
        if args[0] >= 1000:
            raise ValueError(f"Too large: {args[0]}")
        args = (args[0] // 100, args[0] // 10 % 10, args[0] % 10)

    row, col, idx = args
    if CURRENT_MULTI_CANVAS is None:
        _set_current_multi_canvas(QtMultiPlotCanvas(row, col))
    else:
        if not CURRENT_MULTI_CANVAS.shape == (row, col):
            raise ValueError("Shape of subplots does not match")
    return _set_current_canvas(CURRENT_MULTI_CANVAS[idx - 1])


def plot(
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
) -> QtPlotCanvas:
    return gca().add_curve(
        x=x,
        y=y,
        face_color=face_color,
        edge_color=edge_color,
        color=color,
        size=size,
        name=name,
        lw=lw,
        ls=ls,
        symbol=symbol,
    )


def scatter(
    x=None,
    y=None,
    face_color=None,
    edge_color=None,
    color=None,
    size: float = 7,
    name: str | None = None,
    symbol=None,
) -> QtPlotCanvas:
    return gca().add_scatter(
        x=x,
        y=y,
        face_color=face_color,
        edge_color=edge_color,
        color=color,
        size=size,
        name=name,
        symbol=symbol,
    )


def hist(
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
) -> QtPlotCanvas:
    return gca().add_hist(
        data,
        bins=bins,
        range=range,
        density=density,
        face_color=face_color,
        edge_color=edge_color,
        color=color,
        name=name,
        lw=lw,
        ls=ls,
    )


def show() -> None:
    if CURRENT_MULTI_CANVAS is not None:
        CURRENT_MULTI_CANVAS.show()
    else:
        gca().show()


def imshow(image, cmap=None, vmin=None, vmax=None):
    image = np.asarray(image)
    canvas = QtImageCanvas()
    _set_current_canvas(canvas)
    canvas.image = image

    if cmap is not None:
        canvas.cmap = cmap

    if vmin is not None or vmax is not None:
        if vmin is None:
            vmin = image.min()
        if vmax is None:
            vmax = image.max()

        canvas.contrast_limits = (vmin, vmax)

    return canvas
