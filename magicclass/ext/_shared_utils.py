from __future__ import annotations
import numpy as np


def convert_color_code(c):
    if not isinstance(c, str):
        c = np.asarray(c) * 255
    return c


def to_rgba(pen) -> np.ndarray:
    rgba = pen.color().getRgb()
    return np.array(rgba) / 255


def as_float_color(rgba) -> np.ndarray:
    return np.array(rgba) / 255
