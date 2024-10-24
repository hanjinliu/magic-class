try:
    from .widgets2d import (
        VispyPlotCanvas,
        VispyImageCanvas,
        VispyMultiPlotCanvas,
        VispyMultiImageCanvas,
    )
    from .widgets3d import Vispy3DCanvas, VispyMulti3DCanvas
except OSError:
    pass  # cannot run vispy in macOS and python 3.13

__all__ = [
    "VispyPlotCanvas",
    "VispyImageCanvas",
    "VispyMultiPlotCanvas",
    "VispyMultiImageCanvas",
    "Vispy3DCanvas",
    "VispyMulti3DCanvas",
]
