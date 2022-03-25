from __future__ import annotations
from typing import TYPE_CHECKING
import vedo
import numpy as np
import weakref

from .const import Mode, Rendering

if TYPE_CHECKING:
    from .widgets import VtkCanvas


class Layer:
    def __init__(self, data):
        ...

    @property
    def visible(self) -> bool:
        ...

    @visible.setter
    def visible(self, v):
        ...


class Volume(Layer):
    def __init__(self, data, parent):
        self._parent_ref = weakref.ref(parent)
        data = np.asarray(data)
        self._data = data
        self._obj = vedo.Volume(data)
        self._current_obj = self._obj
        self._color = None
        self._alpha = None
        self._rendering = Rendering.composite
        self._mode = Mode.volume
        self._contrast_limits = (data.min(), data.max())
        self._iso_threshold = np.mean(self._contrast_limits)

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, v):
        self._obj._update(v)
        self._update_actor()

    @property
    def canvas(self) -> VtkCanvas:
        return self._parent_ref()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        self._current_obj.c(color=c)
        self._color = c

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, v):
        v = np.asarray(v)
        self._current_obj.alpha(v)
        self._alpha = v

    @property
    def rendering(self):
        return self._rendering.name

    @rendering.setter
    def rendering(self, v):
        r = Rendering(v)
        self._obj.mode(r.toint())
        self._rendering = r

    @property
    def iso_threshold(self) -> float:
        return self._iso_threshold

    @iso_threshold.setter
    def iso_threshold(self, v):
        self._iso_threshold = float(v)
        self._update_actor()

    def _update_actor(self):
        if self._mode == Mode.volume:
            actor = self._obj
        elif self._mode == Mode.mesh:
            actor = self._obj.tomesh()
        elif self._mode == Mode.iso:
            actor = self._obj.isosurface(threshold=self._iso_threshold)
        elif self._mode == Mode.lego:
            actor = self._obj.legosurface(
                vmin=self._contrast_limits[0], vmax=self._contrast_limits[1]
            )
        else:
            raise RuntimeError()

        canvas = self.canvas
        canvas._qwidget.remove(self._current_obj)
        canvas._qwidget.add(actor)
        self._current_obj = actor
        return None

    @property
    def mode(self) -> str:
        return self._mode.value

    @mode.setter
    def mode(self, v):
        self._mode = Mode(v)
        self._update_actor()
