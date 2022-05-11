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

from psygnal import SignalGroup, Signal
from magicgui.widgets import ComboBox, FloatSlider
from ...widgets import ColorEdit, FloatRangeSlider
from ...fields import HasFields, widget_property


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
        contrast_limits=None,
        rendering="mip",
        iso_threshold=None,
        attenuation=1.0,
        cmap="grays",
        gamma=1.0,
        interpolation="linear",
    ):
        self._data = data

        if contrast_limits is None:
            contrast_limits = np.min(self._data), np.max(self._data)
        if iso_threshold is None:
            iso_threshold = np.median(contrast_limits)

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
            self._visual = visuals.Image(
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
            self._visual = visuals.Volume(
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
        self._visual.update()

    @widget_property
    def rendering(self):
        return ComboBox(choices=Image.RENDERINGS, value="mip")

    @widget_property
    def contrast_limits(self):
        return FloatRangeSlider(min=self.data.min(), max=self.data.max())

    @widget_property
    def iso_threshold(self):
        return FloatSlider(min=self.data.min(), max=self.data.max())

    @widget_property
    def gamma(self):
        return FloatSlider(min=0.0, max=1.0)

    @widget_property
    def attenuation(self):
        return FloatSlider(min=0.0, max=1.0)

    @widget_property
    def interpolation(self):
        return ComboBox(choices=Image.INTERPOLATIONS)

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
        self._visual.threshold = value
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
    ):
        self._viewbox = viewbox
        self._create_visual(data)
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


class IsoSurfaceSignals(SignalGroup):
    data = Signal(np.ndarray)
    contrast_limits = Signal(tuple[float, float])
    iso_threshold = Signal(float)
    shading = Signal(str)
    face_color = Signal(tuple)
    edge_color = Signal(tuple)
    edge_width = Signal(float)


class IsoSurface(_SurfaceBase):
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

        self.contrast_limits = contrast_limits

        if iso_threshold is None:
            c0, c1 = self.contrast_limits
            iso_threshold = (c0 + c1) / 2

        self._iso_threshold = iso_threshold

        super().__init__(
            data,
            viewbox=viewbox,
            face_color=face_color,
            edge_color=edge_color,
            shading=shading,
        )

    def _create_visual(self, data):
        self._visual: IsosurfaceVisual = visuals.Isosurface(
            data, level=self.iso_threshold, parent=self._viewbox.scene
        )
        return None

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value) -> None:
        value = np.asarray(value)
        self._visual.set_data(value)
        self._data = value
        self._visual.update()

    @widget_property
    def contrast_limits(self):
        return FloatRangeSlider(min=self.data.min(), max=self.data.max())

    @widget_property
    def shading(self):
        return ComboBox(choices=["none", "float", "smooth"], value="smooth")

    @widget_property
    def iso_threshold(self):
        return FloatSlider(min=self.data.min(), max=self.data.max())

    @widget_property
    def face_color(self):
        return ColorEdit()

    @widget_property
    def edge_color(self) -> ColorEdit:
        return ColorEdit()

    @widget_property
    def edge_width(self) -> FloatSlider:
        return FloatSlider(min=0.5, max=10.0, value=1.0)

    @contrast_limits.connect
    def _on_contrast_limits_change(self, value):
        self._visual.clim = value
        self._visual.update()

    @iso_threshold.connect
    def _on_iso_threshold_change(self, value):
        self._visual.level = self.iso_threshold
        self._visual.update()

    shading.connect(_SurfaceBase._on_shading_change)
    face_color.connect(_SurfaceBase._on_face_color_change)
    edge_color.connect(_SurfaceBase._on_edge_color_change)
    edge_width.connect(_SurfaceBase._on_edge_width_change)


class Surface(_SurfaceBase):
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
