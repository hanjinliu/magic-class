from __future__ import annotations
from typing import Sequence
import vtk
import vedo
from vedo.utils import numpy2vtk
import numpy as np
from magicgui.widgets import FloatSlider

from .components import VtkComponent
from .const import Mode, Rendering

from ...fields import vfield
from ...widgets import FloatRangeSlider
from ...types import Color


def split_rgba(col: str | Sequence[float]) -> tuple[str | Sequence[float], float]:
    if not isinstance(col, str):
        if len(col) == 3:
            rgb, alpha = col, 255
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
        rgb, alpha = col, 255
    return [int(c * 255) for c in rgb], alpha * 255


class Volume(VtkComponent, base=vedo.Volume):
    _obj: vedo.Volume

    def __init__(self, data, _parent):
        super().__init__(data, _parent=_parent, _emit=False)
        self._current_obj = self._obj
        self.rendering = Rendering.composite
        self.mode = Mode.volume
        self.color = np.array([0.7, 0.7, 0.7])
        self.data = data
        self.contrast_limits = self._lims
        self.iso_threshold = np.mean(self._lims)
        self.widgets.emit_all()

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, v):
        self._data = np.asarray(v)
        self._cache_lims()
        vimg = vtk.vtkImageData()
        varr = numpy2vtk(self._data.ravel(order="F"), dtype=float)
        varr.SetName("input_scalars")
        vimg.SetDimensions(self._data.shape)
        vimg.GetPointData().AddArray(varr)
        vimg.GetPointData().SetActiveScalars(varr.GetName())
        self._obj._update(vimg)
        self._update_actor()

    def _cache_lims(self):
        self._lims = self._data.min(), self._data.max()
        self.widgets.contrast_limits.min = self._lims[0]
        self.widgets.contrast_limits.max = self._lims[1]
        self.widgets.iso_threshold.min = self._lims[0]
        self.widgets.iso_threshold.max = self._lims[1]

    color = vfield(Color)
    mode = vfield(Mode.volume)
    rendering = vfield(Rendering.mip)
    iso_threshold = vfield(float, widget_type=FloatSlider)
    contrast_limits = vfield(tuple[float, float], widget_type=FloatRangeSlider)
    visible = vfield(True, name="visibility")

    @visible.connect
    def _on_visible_change(self, v: bool):
        if v:
            self._current_obj.on()
        else:
            self._current_obj.off()
        self._update()

    @color.connect
    def _on_color_change(self, col):
        rgb, alpha = split_rgba(col)
        vmin, vmax = self.contrast_limits
        self._obj.color(rgb, vmin=vmin, vmax=vmax)
        self._obj.alpha([0, alpha])
        self._update_cmap()

    @rendering.connect
    def _on_rendering_change(self, v: Rendering):
        self._obj.mode(v.value)
        self._update_cmap()

    @iso_threshold.connect
    def _on_iso_threshold_change(self, v):
        if self.mode in (Mode.iso, Mode.wireframe):
            self._update_actor()

    @mode.connect
    def _on_mode_change(self, v):
        self._update_actor()

    @contrast_limits.connect
    def _on_contrast_limits_change(self, v):
        self._update_cmap()

    def _update_cmap(self):
        vmin, vmax = self.contrast_limits
        rgb, alpha = split_rgba(self.color)
        if self.mode == Mode.volume:
            self._current_obj.color(
                [[0, 0, 0], rgb],
                alpha=[0, alpha],
                vmin=vmin,
                vmax=vmax,
            )
        else:
            self._current_obj.color(
                rgb,
                alpha=alpha,
            )
        self._update()

    def _update_actor(self):
        vmin, vmax = self.contrast_limits
        rgb, alpha = split_rgba(self.color)
        if self.mode == Mode.volume:
            actor = self._obj
        elif self.mode == Mode.mesh:
            actor = self._obj.tomesh()
        elif self.mode == Mode.iso:
            actor = self._obj.isosurface(threshold=self.iso_threshold)
        elif self.mode == Mode.wireframe:
            actor = (
                self._obj.isosurface(threshold=self.iso_threshold)
                .color(rgb, alpha=alpha)
                .wireframe()
            )
        elif self.mode == Mode.lego:
            actor = self._obj.legosurface(vmin=vmin, vmax=vmax)
        else:
            raise RuntimeError()

        plotter = self._parent_ref()
        plotter.remove(self._current_obj)
        plotter.add(actor)
        plotter.window.Render()
        self._current_obj = actor
        self._update_cmap()
        return None
