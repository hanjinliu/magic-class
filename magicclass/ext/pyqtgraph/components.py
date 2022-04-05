from __future__ import annotations
from typing import Sequence, Tuple
import numpy as np
import pyqtgraph as pg
from psygnal import Signal
from .._shared_utils import convert_color_code, to_rgba


class GraphicComponent:
    native: pg.GraphicsObject

    @property
    def visible(self) -> bool:
        """Linear region visibility."""
        return self.native.isVisible()

    @visible.setter
    def visible(self, value: bool):
        self.native.setVisible(value)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self.__class__, k):
                raise AttributeError(f"Cannot set attribute {k} to TextOverlay.")
        for k, v in kwargs.items():
            setattr(self, k, v)


class Region(GraphicComponent):
    """A linear region with magicgui-like API"""

    changed = Signal(Tuple[float, float])
    native: pg.LinearRegionItem

    def __init__(self):
        self.native = pg.LinearRegionItem()

        @self.native.sigRegionChanged.connect
        def _(e=None):
            self.changed.emit(self.native.getRegion())

    @property
    def value(self) -> tuple[float, float]:
        """Get the limits of linear region."""
        return self.native.getRegion()

    @value.setter
    def value(self, value: tuple[float, float]):
        self.native.setRegion(value)

    @property
    def enabled(self) -> bool:
        return self.native.movable

    @enabled.setter
    def enabled(self, value: bool):
        self.native.setMovable(value)

    @property
    def color(self):
        return to_rgba(self.native.brush)

    @color.setter
    def color(self, value):
        value = convert_color_code(value)
        self.native.setBrush(value)


class Roi(GraphicComponent):
    native: pg.ROI

    def __init__(self, pos=(0, 0)):
        self.native = pg.ROI(pos)
        self.native.setZValue(10000)
        self.native.addScaleHandle([1, 1], [0, 0])

    @property
    def border(self):
        return to_rgba(self.native.pen)

    @border.setter
    def border(self, value):
        value = convert_color_code(value)
        self.native.setPen(pg.mkPen(value))
        self.native._updateView()


class TextItem(GraphicComponent):
    """A text item with napari-like API."""

    native: pg.TextItem

    def __init__(
        self, text: str, color: Sequence[float] | str, anchor=(0, 0), angle: float = 0
    ) -> None:
        self.native = pg.TextItem(
            text, color=convert_color_code(color), anchor=anchor, angle=angle
        )

    @property
    def color(self):
        rgba = self.native.color.getRgb()
        return np.array(rgba) / 255

    @color.setter
    def color(self, value):
        value = convert_color_code(value)
        self.native.setText(self.text, value)

    @property
    def background_color(self):
        return to_rgba(self.native.fill)

    @background_color.setter
    def background_color(self, value):
        value = convert_color_code(value)
        self.native.fill = pg.mkBrush(value)
        self.native._updateView()

    @property
    def border(self):
        return to_rgba(self.native.border)

    @border.setter
    def border(self, value):
        value = convert_color_code(value)
        self.native.border = pg.mkPen(value)
        self.native._updateView()

    @property
    def text(self):
        return self.native.toPlainText()

    @text.setter
    def text(self, value: str):
        self.native.setText(value)

    @property
    def pos(self) -> np.ndarray:
        pos = self.native.pos()
        return np.array([pos.x(), pos.y()])

    @pos.setter
    def pos(self, value):
        self.native.setPos(*value)

    @property
    def anchor(self) -> np.ndarray:
        anchor = self.native.anchor
        return np.array([anchor.x(), anchor.y()])

    @anchor.setter
    def anchor(self, value):
        self.native.setAnchor(value)


class ScaleBar(GraphicComponent):
    """A scale bar with napari-like API"""

    native: pg.ScaleBar

    def __init__(self):
        self._unit = ""
        self.native = pg.ScaleBar(10, suffix=self._unit)
        self.native

    @property
    def color(self):
        return to_rgba(self.native.brush)

    @color.setter
    def color(self, value):
        value = convert_color_code(value)
        self.native.brush = pg.mkBrush(value)
        self.native.bar.setBrush(self.native.brush)

    @property
    def unit(self) -> str:
        return self._unit

    @unit.setter
    def unit(self, value: str):
        value = str(value)
        self.native.text.setText(pg.siFormat(self.native.size, suffix=value))
        self._unit = value


class Legend(GraphicComponent):
    native: pg.LegendItem

    def __init__(self, offset=(0, 0)):
        self.native = pg.LegendItem(offset=offset)

    @property
    def color(self):
        """Text color."""
        color = self.native.labelTextColor()
        if color is None:
            color = pg.mkPen(None).color()
        rgba = color.getRgb()
        return np.array(rgba) / 255

    @color.setter
    def color(self, value):
        value = convert_color_code(value)
        self.native.setLabelTextColor(value)

    @property
    def size(self) -> int:
        """Text size."""
        return self.native.labelTextSize()

    @size.setter
    def size(self, value: int):
        self.native.setLabelTextSize(value)

    @property
    def border(self):
        """Border color."""
        return to_rgba(self.native.pen())

    @border.setter
    def border(self, value):
        value = convert_color_code(value)
        self.native.setPen(pg.mkPen(value))

    @property
    def background_color(self):
        """Background color."""
        return to_rgba(self.native.brush())

    @background_color.setter
    def background_color(self, value):
        value = convert_color_code(value)
        self.native.setBrush(pg.mkBrush(value))
