from __future__ import annotations
import numpy as np
from vispy.scene import visuals, ViewBox
from vispy.visuals import (
    VolumeVisual,
    ImageVisual,
    IsosurfaceVisual,
    MeshVisual,
)
from vispy.visuals.filters import WireframeFilter
from ._base import LayerItem

from magicgui.widgets import FloatSlider
from ...widgets import FloatRangeSlider
from ...fields import HasFields, vfield
from ...types import Color


class Image(LayerItem, HasFields):
    RENDERINGS = [
        "translucent",
        "mip",
        "minip",
        "attenuated_mip",
        "additive",
        "iso",
        "average",
    ]
    INTERPOLATIONS = ["nearest", "linear"]

    def __init__(
        self,
        data,
        viewbox: ViewBox,
        contrast_limits: tuple[float, float] | None = None,
        rendering: str = "mip",
        iso_threshold: float | None = None,
        attenuation: float = 1.0,
        cmap: str = "grays",
        gamma: str = 1.0,
        interpolation: str = "linear",
    ):
        self._data = data
        self._cache_lims()

        if contrast_limits is None:
            contrast_limits = np.min(self._data), np.max(self._data)
        if iso_threshold is None:
            iso_threshold = np.mean(contrast_limits)

        self._viewbox = viewbox
        self._create_visual(
            self._data,
            clim=contrast_limits,
            cmap=cmap,
            rendering=rendering,
            iso_threshold=iso_threshold,
            attenuation=attenuation,
            gamma=gamma,
            interpolation=interpolation,
        )

        self.contrast_limits = contrast_limits
        self.rendering = rendering
        self.iso_threshold = iso_threshold
        self.attenuation = attenuation
        self._cmap = cmap
        self.gamma = gamma
        self.interpolation = interpolation

    def _create_visual(
        self,
        data: np.ndarray,
        clim: tuple[float, float],
        cmap: str,
        rendering: str,
        iso_threshold: float,
        attenuation: float,
        gamma: float,
        interpolation: str | None = None,
    ):
        if data.ndim == 2:
            if interpolation is None:
                interpolation = "nearest"
            self._visual: ImageVisual = visuals.Image(
                data,
                clim=clim,
                method="auto",
                cmap=cmap,
                gamma=gamma,
                interpolation=interpolation,
                parent=self._viewbox.scene,
            )

        elif data.ndim == 3:
            if interpolation is None:
                interpolation = "linear"
            self._visual: VolumeVisual = visuals.Volume(
                data,
                clim=clim,
                method=rendering,
                threshold=iso_threshold,
                attenuation=attenuation,
                cmap=cmap,
                gamma=gamma,
                interpolation=interpolation,
                parent=self._viewbox.scene,
            )
        else:
            raise ValueError("Only 2D and 3D images are supported.")

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value) -> None:
        value = np.asarray(value)
        if self._visual is None or value.ndim != self._data.ndim:
            self._visual.parent = None
            del self._visual
            self._create_visual(value, None)
        else:
            self._visual.set_data(value)
        self._data = value
        self._cache_lims()
        self._visual.update()

    def _cache_lims(self):
        self._lims = np.min(self._data), np.max(self._data)
        self.widgets.contrast_limits.min = self._lims[0]
        self.widgets.contrast_limits.max = self._lims[1]
        self.widgets.iso_threshold.min = self._lims[0]
        self.widgets.iso_threshold.max = self._lims[1]

    # fmt: off
    rendering = vfield(str, options={"choices": RENDERINGS, "value": "mip"})
    contrast_limits = vfield(tuple[float, float], widget_type=FloatRangeSlider)
    iso_threshold = vfield(float, widget_type=FloatSlider)
    gamma = vfield(float, widget_type=FloatSlider, options={"min": 0., "max": 1.})
    attenuation = vfield(float, widget_type=FloatSlider, options={"min": 0., "max": 1.})
    interpolation = vfield(str, options={"choices": INTERPOLATIONS})
    # fmt: on

    @contrast_limits.connect
    def _on_constrast_limits_change(self, value):
        self._visual.clim = value
        self._visual.update()

    @rendering.connect
    def _on_rendering_change(self, value):
        self._visual.method = value
        self._visual.update()

    @iso_threshold.connect
    def _on_iso_threshold_change(self, value):
        self._visual.threshold = max(value, self._lims[0] + 1e-6)
        self._visual.update()

    @gamma.connect
    def _on_gamma_change(self, value):
        self._visual.gamma = value
        self._visual.update()

    @attenuation.connect
    def _on_attenuation_change(self, value):
        self._visual.attenuation = value
        self._visual.update()

    @interpolation.connect
    def _on_interpolation_change(self, value):
        self._visual.interpolation = value
        self._visual.update()


class _SurfaceBase(LayerItem):
    _visual: visuals.Mesh | visuals.Isosurface
    _wireframe: WireframeFilter

    def __init__(
        self,
        data,
        viewbox: ViewBox,
        face_color=None,
        edge_color=None,
        shading="none",
        **kwargs,
    ):
        self._viewbox = viewbox
        self._create_visual(data, **kwargs)
        self._wireframe = WireframeFilter()
        self._visual.attach(self._wireframe)
        self._data = data

        if edge_color is None:
            edge_color = [0.7, 0.7, 0.7, 1.0]
        self.edge_color = edge_color

        if face_color is None:
            face_color = [0.7, 0.7, 0.7, 1.0]
        self.face_color = face_color

        self.shading = shading

    def _create_visual(self, data):
        raise NotImplementedError()

    def _on_face_color_change(self, color):
        self._visual.color = color

    def _on_edge_color_change(self, color):
        self._wireframe.color = color
        self._visual.update()

    color = property(fget=None)

    @color.setter
    def color(self, color):
        self.face_color = color
        self.edge_color = color

    def _on_edge_width_change(self, value):
        self._wireframe.width = value
        self._visual.update()

    def _on_shading_change(self, v):
        if v == "none":
            v = None
        self._visual._shading = v


class IsoSurface(_SurfaceBase, HasFields):
    def __init__(
        self,
        data,
        viewbox: ViewBox,
        contrast_limits=None,
        iso_threshold=None,
        face_color=None,
        edge_color=None,
        shading="smooth",
    ):
        data = np.asarray(data)
        data = data.transpose(list(range(data.ndim))[::-1])

        if contrast_limits is None:
            contrast_limits = np.min(data), np.max(data)

        if iso_threshold is None:
            iso_threshold = np.mean(contrast_limits)

        super().__init__(
            data,
            viewbox=viewbox,
            face_color=face_color,
            edge_color=edge_color,
            shading=shading,
            iso_threshold=iso_threshold,
        )
        self._cache_lims()

        self.contrast_limits = contrast_limits
        self.iso_threshold = iso_threshold

    def _create_visual(self, data, iso_threshold):
        self._visual: IsosurfaceVisual = visuals.Isosurface(
            data, level=iso_threshold, parent=self._viewbox.scene
        )
        return None

    def _cache_lims(self):
        self._lims = np.min(self._data), np.max(self._data)
        self.widgets.contrast_limits.min = self._lims[0]
        self.widgets.contrast_limits.max = self._lims[1]
        self.widgets.iso_threshold.min = self._lims[0]
        self.widgets.iso_threshold.max = self._lims[1]

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value) -> None:
        value = np.asarray(value)
        self._visual.set_data(value)
        self._data = value
        self._visual.update()
        self._cache_lims()

    # fmt: off
    contrast_limits = vfield(tuple[float, float], widget_type=FloatRangeSlider)
    shading = vfield(str, options={"choices": ["none", "float", "smooth"], "value": "smooth"})
    iso_threshold = vfield(float, widget_type=FloatSlider)
    face_color = vfield(Color)
    edge_color = vfield(Color)
    edge_width = vfield(float, widget_type=FloatSlider, options={"min": 0.5, "max": 10.0, "value": 1.0})
    # fmt: on

    @contrast_limits.connect
    def _on_contrast_limits_change(self, value):
        self._visual.clim = value
        self._visual.update()

    @iso_threshold.connect
    def _on_iso_threshold_change(self, value):
        self._visual.level = max(self.iso_threshold, self._lims[0] + 1e-6)
        self._visual.update()

    shading.connect(_SurfaceBase._on_shading_change)
    face_color.connect(_SurfaceBase._on_face_color_change)
    edge_color.connect(_SurfaceBase._on_edge_color_change)
    edge_width.connect(_SurfaceBase._on_edge_width_change)


class Surface(_SurfaceBase, HasFields):
    def __init__(
        self,
        data,
        viewbox: ViewBox,
        face_color=None,
        edge_color=None,
        shading="none",
    ):
        super().__init__(
            data, viewbox, face_color=face_color, edge_color=edge_color, shading=shading
        )

    def _create_visual(self, data):
        self._visual: MeshVisual = visuals.Mesh(
            vertices=data[0], faces=data[1], parent=self._viewbox.scene
        )
        self.data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value) -> None:
        if len(value) == 2:
            verts, faces = value
            vals = None
        elif len(value) == 3:
            verts, faces, vals = value
        else:
            raise ValueError("Data must be vertices, faces (, values).")
        self._visual.set_data(vertices=verts, faces=faces, vertex_values=vals)
        self._data = (verts, faces, vals)
        self._visual.update()

    shading = vfield(
        str, options={"choices": ["none", "float", "smooth"], "value": "smooth"}
    )
    face_color = vfield(Color)
    edge_color = vfield(Color)
    edge_width = vfield(
        float, widget_type=FloatSlider, options={"min": 0.5, "max": 10.0, "value": 1.0}
    )

    shading.connect(_SurfaceBase._on_shading_change)
    face_color.connect(_SurfaceBase._on_face_color_change)
    edge_color.connect(_SurfaceBase._on_edge_color_change)
    edge_width.connect(_SurfaceBase._on_edge_width_change)
