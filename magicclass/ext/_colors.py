from __future__ import annotations

from magicclass.types import Color
from magicclass.widgets.color import get_color_converter

# NOTE: not used yet


class AbstractColorManager:
    pass


norm_color = get_color_converter()


class ConstantColorManager(AbstractColorManager):
    def __init__(self, color: Color) -> None:
        self._color = norm_color(color)

    def __eq__(self, other) -> bool:
        if isinstance(other, ConstantColorManager):
            other = other._color
        c1 = norm_color(other)
        return all(abs(c1 - c2) < 1e-4 for c2 in self._color)


class ArrayColorManager(AbstractColorManager):
    def __init__(self, colors) -> None:
        import numpy as np

        _color = np.asarray(colors)
        _kind = _color.dtype.kind
        if _kind == "f":
            if _color.min() < -1e-6 or _color.max() > 1 + 1e-6:
                raise ValueError("Color value must be in [0, 1]")
            self._color = _color.astype(np.float32, copy=False)
        elif _kind in "ui":
            if _color.min() < 0 or _color.max() > 255:
                raise ValueError("Color value must be in [0, 255]")
            self._color = _color.astype(np.float32) / 255.0
        elif _kind in "UO":
            if _color.ndim != 1:
                raise ValueError("Color must be 1D array if string is given.")
            self._color = np.asarray([norm_color(c) for c in _color], dtype=np.float32)
        else:
            raise ValueError("Invalid color type.")
