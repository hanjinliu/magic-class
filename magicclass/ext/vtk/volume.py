from __future__ import annotations
import vedo
import numpy as np
from .components import VtkProperty, VtkComponent
from .const import Mode, Rendering


class Volume(VtkComponent, base=vedo.Volume):
    _obj: vedo.Volume

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
        self.color = "gray"

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
        return self._color

    @color.setter
    def color(self, col):
        self._obj.color(
            col, vmin=self._contrast_limits[0], vmax=self._contrast_limits[0]
        )
        self._update_actor()
        self._color = col

    @property
    def rendering(self):
        return self._rendering.name

    @rendering.setter
    def rendering(self, v):
        r: Rendering = getattr(Rendering, v)
        self._obj.mode(r.value)
        self._rendering = r
        self._update_actor()

    @property
    def iso_threshold(self) -> float:
        return self._iso_threshold

    @iso_threshold.setter
    def iso_threshold(self, v):
        self._iso_threshold = float(v)
        if self._mode in (Mode.iso, Mode.wireframe):
            self._update_actor()

    def _update_actor(self):
        if self._mode == Mode.volume:
            actor = self._obj
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
            actor = self._obj.legosurface(
                vmin=self._contrast_limits[0], vmax=self._contrast_limits[1]
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
        return self._mode.value

    @mode.setter
    def mode(self, v):
        self._mode = Mode(v)
        self._update_actor()

    @property
    def contrast_limits(self) -> tuple[float, float]:
        return self._contrast_limits

    @contrast_limits.setter
    def contrast_limits(self, v):
        x0, x1 = v
        self._contrast_limits = (x0, x1)
        if self._mode == Mode.lego:
            self._update_actor()
