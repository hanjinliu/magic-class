from __future__ import annotations
from typing import Tuple, NamedTuple
import numpy as np
from vispy.scene import visuals, ViewBox
from vispy.visuals import (
    VolumeVisual,
    ImageVisual,
    IsosurfaceVisual,
    MeshVisual,
    LineVisual,
    MarkersVisual,
    ArrowVisual,
)
from vispy.visuals import transforms as tr
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
        name: str = "",
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

        self._name = name

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
        if self._visual is None or value.ndim != self.data.ndim:
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

    def _get_bbox(self) -> Tuple[np.ndarray, np.ndarray]:
        return np.zeros(3, dtype=np.float32), np.array(
            self._data.shape, dtype=np.float32
        )

    # fmt: off
    rendering = vfield(str, options={"choices": RENDERINGS, "value": "mip"})
    contrast_limits = vfield(Tuple[float, float], widget_type=FloatRangeSlider)
    iso_threshold = vfield(float, widget_type=FloatSlider)
    gamma = vfield(float, widget_type=FloatSlider, options={"min": 0., "max": 1.})
    attenuation = vfield(float, widget_type=FloatSlider, options={"min": 0., "max": 1.})
    interpolation = vfield(str, options={"choices": INTERPOLATIONS})
    # fmt: on

    @contrast_limits.connect
    def _on_constrast_limits_change(self, value):
        if hasattr(self, "_visual"):
            self._visual.clim = value
            self._visual.update()

    @rendering.connect
    def _on_rendering_change(self, value):
        self._visual.method = value
        self._visual.update()

    @iso_threshold.connect
    def _on_iso_threshold_change(self, value):
        if hasattr(self, "_visual"):
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
        name: str = "",
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
        self._name = name

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
        name: str | None = None,
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
            name=name,
        )
        self._cache_lims()

        self.contrast_limits = contrast_limits
        self.iso_threshold = iso_threshold

    def _create_visual(self, data, iso_threshold):
        self._visual: IsosurfaceVisual = visuals.Isosurface(
            data, level=iso_threshold, parent=self._viewbox.scene
        )
        return None

    def _get_bbox(self) -> Tuple[np.ndarray, np.ndarray]:
        data = self._data
        mins = np.min(data[0], axis=0)
        maxs = np.max(data[0], axis=0)

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

    def _get_bbox(self) -> Tuple[np.ndarray, np.ndarray]:
        return np.zeros(3, dtype=np.float32), np.array(
            self._data.shape, dtype=np.float32
        )

    # fmt: off
    contrast_limits = vfield(Tuple[float, float], widget_type=FloatRangeSlider)
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


class SurfaceData(NamedTuple):
    """Dataset that defines a surface data."""

    verts: np.ndarray
    faces: np.ndarray
    values: np.ndarray


class Surface(_SurfaceBase, HasFields):
    def __init__(
        self,
        data,
        viewbox: ViewBox,
        face_color=None,
        edge_color=None,
        shading="none",
        name: str | None = None,
    ):
        super().__init__(
            data,
            viewbox,
            face_color=face_color,
            edge_color=edge_color,
            shading=shading,
            name=name,
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
        self._data = SurfaceData(verts, faces, vals)
        self._visual.update()

    def _get_bbox(self) -> Tuple[np.ndarray, np.ndarray]:
        verts = self._data.verts
        mins = np.min(verts, axis=0)
        maxs = np.max(verts, axis=0)
        return mins, maxs

    # fmt: off
    shading = vfield(str, options={"choices": ["none", "float", "smooth"], "value": "smooth"})
    face_color = vfield(Color)
    edge_color = vfield(Color)
    edge_width = vfield(float, widget_type=FloatSlider, options={"min": 0.5, "max": 10.0, "value": 1.0})
    # fmt: on

    shading.connect(_SurfaceBase._on_shading_change)
    face_color.connect(_SurfaceBase._on_face_color_change)
    edge_color.connect(_SurfaceBase._on_edge_color_change)
    edge_width.connect(_SurfaceBase._on_edge_width_change)


class Curve3D(LayerItem, HasFields):
    def __init__(
        self,
        data,
        viewbox: ViewBox,
        color=None,
        width=1.0,
        name: str | None = None,
    ):
        super().__init__()
        self._name = name
        self._viewbox = viewbox
        data = data[:, ::-1]  # vispy uses xyz, not zyx
        self._visual: LineVisual = visuals.Line(
            pos=data, color=color, width=width, parent=self._viewbox.scene
        )
        self.data = data

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value) -> None:
        self._visual.set_data(pos=value)
        self._data = value
        self._visual.update()

    def _get_bbox(self) -> Tuple[np.ndarray, np.ndarray]:
        mins = np.min(self.data, axis=0)
        maxs = np.max(self.data, axis=0)
        return mins, maxs

    # fmt: off
    color = vfield(Color)
    width = vfield(1.0, widget_type=FloatSlider, options={"min": 0.5, "max": 10.0})
    # fmt: on

    @color.connect
    def _on_color_change(self, value):
        return self._visual.set_data(color=value)

    @width.connect
    def _on_width_change(self, value):
        return self._visual.set_data(width=value)


class Points3D(LayerItem, HasFields):
    def __init__(
        self,
        data,
        viewbox: ViewBox,
        face_color: Color | None = None,
        edge_color: Color | None = None,
        edge_width: float = 0.0,
        size: float = 1.0,
        spherical: bool = True,
        name: str | None = None,
    ):
        super().__init__()
        self._name = name
        self._viewbox = viewbox
        # data = data[:, ::-1]  # vispy uses xyz, not zyx
        self._visual: MarkersVisual = visuals.Markers(
            scaling=True, parent=self._viewbox.scene, spherical=True
        )
        self.data = data
        self.face_color = face_color
        self.edge_color = edge_color
        self.edge_width = edge_width
        self.size = size
        self.spherical = spherical

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value) -> None:
        self._visual.set_data(pos=value)
        self._data = value
        self._visual.update()

    # fmt: off
    face_color = vfield(Color)
    edge_color = vfield(Color)
    edge_width = vfield(0.0, widget_type=FloatSlider, options={"min": 0.0, "max": 5.0})
    size = vfield(1.0, widget_type=FloatSlider, options={"min": 1.0, "max": 50.0})
    spherical = vfield(True)
    # fmt: on

    @face_color.connect
    def _on_face_color_change(self, value):
        return self._visual.set_data(
            pos=self.data,
            face_color=value,
            edge_color=self.edge_color,
            edge_width=self.edge_width,
            size=self.size,
            scaling=True,
            symbol=self._visual.symbol,
        )

    @face_color.connect
    def _on_edge_color_change(self, value):
        return self._visual.set_data(
            pos=self.data,
            face_color=self.face_color,
            edge_color=value,
            edge_width=self.edge_width,
            size=self.size,
            scaling=True,
            symbol=self._visual.symbol,
        )

    @edge_width.connect
    def _on_edge_width_change(self, value):
        return self._visual.set_data(
            pos=self.data,
            face_color=self.face_color,
            edge_color=self.edge_color,
            edge_width=value,
            size=self.size,
            scaling=True,
            symbol=self._visual.symbol,
        )

    @spherical.connect
    def _on_spherical_change(self, value):
        self._visual.spherical = value
        self._visual.update()

    @size.connect
    def _on_size_change(self, value):
        return self._visual.set_data(
            pos=self.data,
            face_color=self.face_color,
            edge_color=self.edge_color,
            edge_width=self.edge_width,
            size=value,
            scaling=True,
            symbol=self._visual.symbol,
        )


    def _get_bbox(self) -> Tuple[np.ndarray, np.ndarray]:
        mins = np.min(self.data, axis=0)
        maxs = np.max(self.data, axis=0)
        return mins, maxs


class Arrows3D(LayerItem, HasFields):
    _ARROW_TYPES = (
        "stealth",
        "curved",
        "triangle_30",
        "triangle_60",
        "triangle_90",
        "angle_30",
        "angle_60",
        "angle_90",
        "inhibitor_round",
    )

    def __init__(
        self,
        data: np.ndarray,
        viewbox: ViewBox,
        color: Color | None = None,
        width: float = 0.0,
        arrow_type: str = "stealth",
        arrow_size: float = 1.0,
        name: str | None = None,
    ):
        super().__init__()
        self._name = name
        self._viewbox = viewbox
        data = data[:, ::-1]  # vispy uses xyz, not zyx
        self._visual: ArrowVisual = visuals.Arrow(
            parent=self._viewbox.scene, connect="segments"
        )
        self.data = data
        self.color = color
        self.width = width
        self.arrow_type = arrow_type
        self.arrow_size = arrow_size

    # fmt: off
    color = vfield(Color)
    width = vfield(0.0, widget_type=FloatSlider, options={"min": 0.0, "max": 5.0})
    arrow_type = vfield("stealth", options={"choices": _ARROW_TYPES})
    arrow_size = vfield(1.0, options={"min": 0.5, "max": 100})
    # fmt: on

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value: np.ndarray) -> None:
        # value.shape == (N, P, 3)
        arrows = value[:, -2:].reshape(-1, 6)
        arrows = np.concatenate([arrows[:, 3:], arrows[:, :3]], axis=1)
        self._visual.set_data(pos=value, arrows=arrows)
        self._data = value
        self._visual.update()

    @color.connect
    def _on_color_change(self, value):
        self._visual.arrow_color = value
        return self._visual.set_data(color=value)

    @width.connect
    def _on_width_change(self, value):
        return self._visual.set_data(width=value)

    @arrow_type.connect
    def _on_arrow_type_change(self, value):
        self._visual.arrow_type = value
        self._visual.update()

    @arrow_size.connect
    def _on_arrow_size_change(self, value):
        self._visual.arrow_size = value
        self._visual.update()

    def _get_bbox(self) -> Tuple[np.ndarray, np.ndarray]:
        mins = np.min(self.data, axis=(0, 1))
        maxs = np.max(self.data, axis=(0, 1))
        return mins, maxs
