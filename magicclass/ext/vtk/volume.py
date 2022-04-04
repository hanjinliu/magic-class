from __future__ import annotations
from typing import Sequence
import weakref
import vedo
import numpy as np
from functools import cached_property
from psygnal import Signal, SignalGroup
from magicgui.widgets import FloatSlider, ComboBox
from magicclass.widgets import ColorEdit

from .components import VtkProperty, VtkComponent
from .const import Mode, Rendering


class VolumeSignalGroup(SignalGroup):
    """Signal group for a volume."""

    color = Signal(tuple)
    mode = Signal(int)
    rendering = Signal(int)
    iso_threshold = Signal(float)


class WidgetGroup:
    def __init__(self, vol: Volume):
        self._vol = weakref.ref(vol)

    @property
    def volume(self) -> Volume:
        return self._vol()

    @cached_property
    def color(self) -> ColorEdit:
        coloredit = ColorEdit(value=self.volume.color, name="color")
        coloredit.changed.connect_setattr(self.volume, "color")
        self.volume.events.rendering.connect_setattr(coloredit, "value")
        return coloredit

    @cached_property
    def mode(self) -> ComboBox:
        cbox = ComboBox(choices=Mode, value=Mode(self.volume.mode), name="mode")

        @cbox.changed.connect
        def _(v):
            self.volume.mode = Mode(v)

        self.volume.events.mode.connect_setattr(cbox, "value")
        return cbox

    @cached_property
    def rendering(self) -> ComboBox:
        cbox = ComboBox(
            choices=Rendering, value=self.volume.rendering, name="rendering"
        )
        cbox.changed.connect_setattr(self.volume, "rendering")
        self.volume.events.rendering.connect_setattr(cbox, "value")
        return cbox

    @cached_property
    def iso_threshold(self) -> FloatSlider:
        vmin, vmax = self.volume.contrast_limits
        sl = FloatSlider(
            name="iso threshold", min=vmin, max=vmax, value=self.volume.iso_threshold
        )
        sl.changed.connect_setattr(self.volume, "iso_threshold")
        self.volume.events.iso_threshold.connect_setattr(sl, "value")
        return sl


def split_rgba(col: str | Sequence[float]) -> tuple[str | Sequence[float], float]:
    if not isinstance(col, str):
        if len(col) == 3:
            rgb, alpha = col, 1.0
        else:
            rgb, alpha = col[:3], col[3]
    elif col.startswith("#"):
        l = len(col)
        if l == 9:
            rgb = int(col[1:7], base=16) / 255
            alpha = int(col[7:], base=16) / 255
        elif l == 7:
            rgb = int(col[1:7], base=16) / 255
            alpha = 1.0
        else:
            raise ValueError(f"Informal color code: {col}.")
    else:
        rgb, alpha = col, 1.0
    return rgb, alpha


class Volume(VtkComponent, base=vedo.Volume):
    _obj: vedo.Volume
    events = VolumeSignalGroup()

    def __init__(self, data, _parent):
        super().__init__(data, _parent=_parent)
        self._data = data
        self._current_obj = self._obj
        self._color = None
        self._alpha = None
        self._rendering = Rendering.composite
        self._mode = Mode.volume
        self._contrast_limits = (self._data.min(), self._data.max())
        self._iso_threshold = np.mean(self._contrast_limits)
        self.color = np.array([0.7, 0.7, 0.7])
        self.widgets = WidgetGroup(self)

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, v):
        self._obj._update(v)
        self._update_actor()
        self._data = v

    # fmt: off
    shade: VtkProperty[Volume, np.ndarray] = VtkProperty(vtk_fname="Shade", converter=bool, doc="Turn on/off shading.")  # noqa
    jittering: VtkProperty[Volume, bool] = VtkProperty("jittering", converter=bool, doc="Turn on/off jittering.")  # noqa
    # fmt: on

    @property
    def color(self) -> np.ndarray:
        """Color of the volume."""
        return self._color

    @color.setter
    def color(self, col):
        rgb, alpha = split_rgba(col)
        self._obj.color(
            rgb, vmin=self._contrast_limits[0], vmax=self._contrast_limits[0]
        )
        # self._obj.alpha(alpha)
        self._color = rgb
        self._update_actor()

    @property
    def rendering(self):
        """Rendering mode of the volume."""
        return self._rendering.name

    @rendering.setter
    def rendering(self, v):
        r: Rendering = getattr(Rendering, v)
        self._obj.mode(r.value)
        self._rendering = r
        self._update_actor()

    @property
    def iso_threshold(self) -> float:
        """
        Threshold value to generate isosurface.

        This property only has effect on "iso" and "wireframe" rendering.
        """
        return self._iso_threshold

    @iso_threshold.setter
    def iso_threshold(self, v):
        self._iso_threshold = float(v)
        if self._mode in (Mode.iso, Mode.wireframe):
            self._update_actor()
        self.events.iso_threshold.emit(v)

    def _update_actor(self):
        vmin, vmax = self._contrast_limits
        if self._mode == Mode.volume:
            actor = self._obj.color(self.color, vmin=vmin, vmax=vmax)
        elif self._mode == Mode.mesh:
            actor = self._obj.tomesh()
        elif self._mode == Mode.iso:
            actor = self._obj.isosurface(threshold=self._iso_threshold).color(
                self._color
            )
        elif self._mode == Mode.wireframe:
            actor = (
                self._obj.isosurface(threshold=self._iso_threshold)
                .color(self._color)
                .wireframe()
            )
        elif self._mode == Mode.lego:
            actor = self._obj.legosurface(vmin=vmin, vmax=vmax).color(
                self._color, vmin=vmin, vmax=vmax
            )
        else:
            raise RuntimeError()

        plotter = self._parent_ref()
        plotter.remove(self._current_obj)
        plotter.add(actor)
        plotter.window.Render()
        self._current_obj = actor
        return None

    @property
    def mode(self) -> str:
        """Projection mode of volume."""
        return self._mode.value

    @mode.setter
    def mode(self, v):
        self._mode = Mode(v)
        self._update_actor()
        self.events.mode.emit(self._mode.value)

    @property
    def contrast_limits(self) -> tuple[float, float]:
        """Contrast limits of volume."""
        return self._contrast_limits

    @contrast_limits.setter
    def contrast_limits(self, v):
        x0, x1 = v
        self._contrast_limits = (x0, x1)

        if self._mode == Mode.lego:
            self._update_actor()
