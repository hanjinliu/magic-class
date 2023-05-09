from __future__ import annotations
from typing import overload, TYPE_CHECKING
import numpy as np
from .widgets2d import VispyPlotCanvas, VispyMultiPlotCanvas, VispyImageCanvas

if TYPE_CHECKING:
    from .widgets2d import Has2DViewBox, MultiPlot

CURRENT_MULTI_CANVAS: MultiPlot | None = None
CURRENT_CANVAS: Has2DViewBox | None = None


def gca() -> VispyPlotCanvas:
    global CURRENT_CANVAS
    if CURRENT_CANVAS is None:
        CURRENT_CANVAS = VispyPlotCanvas()
    return CURRENT_CANVAS


def _set_current_canvas(canvas):
    global CURRENT_CANVAS
    CURRENT_CANVAS = canvas
    return canvas


def _set_current_multi_canvas(multi):
    global CURRENT_MULTI_CANVAS
    CURRENT_MULTI_CANVAS = multi
    return multi


def gcf():
    if CURRENT_MULTI_CANVAS is None:
        return gca()
    return CURRENT_MULTI_CANVAS


def figure():
    _set_current_canvas(VispyPlotCanvas())
    return CURRENT_CANVAS


@overload
def subplot(pos: int):
    ...


@overload
def subplot(row: int, col: int, idx: int):
    ...


def subplot(*args):
    if len(args) == 1 and args[0] >= 111:
        if args[0] >= 1000:
            raise ValueError(f"Too large: {args[0]}")
        args = (args[0] // 100, args[0] // 10 % 10, args[0] % 10)

    row, col, idx = args
    if CURRENT_MULTI_CANVAS is None:
        _set_current_multi_canvas(VispyMultiPlotCanvas(row, col))
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
) -> VispyPlotCanvas:
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
) -> VispyPlotCanvas:
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
    data,
    bins: int = 10,
    face_color=None,
    edge_color=None,
    color="white",
    name: str | None = None,
) -> VispyPlotCanvas:
    return gca().add_hist(
        data,
        bins=bins,
        face_color=face_color,
        edge_color=edge_color,
        color=color,
        name=name,
    )


def show():
    if CURRENT_MULTI_CANVAS is not None:
        CURRENT_MULTI_CANVAS.show()
    else:
        gca().show()


def imshow(image, cmap=None, vmin=None, vmax=None):
    image = np.asarray(image)
    canvas = VispyImageCanvas()
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
