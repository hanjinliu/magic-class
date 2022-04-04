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


class Image(LayerItem):
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

        self._contrast_limits = contrast_limits
        self._rendering = rendering
        self._iso_threshold = iso_threshold
        self._attenuation = attenuation
        self._cmap = cmap
        self._gamma = gamma
        self._interpolation = interpolation

        self._viewbox = viewbox
        self._visual: VolumeVisual | ImageVisual = None
        self._create_visual(self._data, self._interpolation)

    def _create_visual(self, data: np.ndarray, interpolation: str | None = None):
        if data.ndim == 2:
            if interpolation is None:
                interpolation = "nearest"
            self._visual = visuals.Image(
                data,
                clim=self._contrast_limits,
                method="auto",
                cmap=self._cmap,
                gamma=self._gamma,
                interpolation=interpolation,
                parent=self._viewbox.scene,
            )

        elif data.ndim == 3:
            if interpolation is None:
                interpolation = "linear"
            self._visual = visuals.Volume(
                data,
                clim=self._contrast_limits,
                method=self._rendering,
                threshold=self._iso_threshold,
                attenuation=self._attenuation,
                cmap=self._cmap,
                gamma=self._gamma,
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

    @property
    def contrast_limits(self) -> tuple[float, float]:
        return self._contrast_limits

    @contrast_limits.setter
    def contrast_limits(self, value) -> None:
        self._visual.clim = value
        self._contrast_limits = value
        self._visual.update()

    @property
    def rendering(self) -> str:
        return self._rendering

    @rendering.setter
    def rendering(self, value: str) -> None:
        self._visual.method = value
        self._rendering = value
        self._visual.update()

    @property
    def iso_threshold(self) -> float:
        return self._iso_threshold

    @iso_threshold.setter
    def iso_threshold(self, value) -> None:
        self._iso_threshold = float(value)
        self._visual.threshold = self._iso_threshold
        self._visual.update()

    @property
    def gamma(self) -> float:
        return self._gamma

    @gamma.setter
    def gamma(self, value) -> None:
        self._gamma = float(value)
        self._visual.gamma = self._gamma
        self._visual.update()

    @property
    def attenuation(self) -> float:
        return self._attenuation

    @attenuation.setter
    def attenuation(self, value) -> None:
        self._attenuation = float(value)
        self._visual.attenuation = self._attenuation
        self._visual.update()

    @property
    def interpolation(self) -> float:
        return self._interpolation

    @interpolation.setter
    def interpolation(self, value) -> None:
        self._interpolation = float(value)
        self._visual.interpolation = self._interpolation
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
        self.data = data

        if edge_color is None:
            edge_color = [0.7, 0.7, 0.7, 1.0]
        self.edge_color = edge_color

        if face_color is None:
            face_color = [0.7, 0.7, 0.7, 1.0]
        self.face_color = face_color

        self.shading = shading

    def _create_visual(self, data):
        raise NotImplementedError()

    @property
    def face_color(self) -> np.ndarray:
        raise NotImplementedError()

    @property
    def edge_color(self) -> np.ndarray:
        return self._wireframe.color

    @edge_color.setter
    def edge_color(self, color) -> None:
        self._wireframe.color = color
        self._visual.update()

    color = property(fget=None)

    @color.setter
    def color(self, color):
        self.face_color = color
        self.edge_color = color

    @property
    def shading(self) -> str:
        """Return current shading mode of the layer."""
        return self._visual.shading or "none"

    @shading.setter
    def shading(self, v):
        if v == "none":
            v = None
        self._visual.shading = v


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

        self._contrast_limits = contrast_limits

        if iso_threshold is None:
            c0, c1 = self._contrast_limits
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

    @property
    def contrast_limits(self) -> tuple[float, float]:
        return self._contrast_limits

    @contrast_limits.setter
    def contrast_limits(self, value) -> None:
        self._visual.clim = value
        self._contrast_limits = value
        self._visual.update()

    @property
    def iso_threshold(self) -> float:
        return self._iso_threshold

    @iso_threshold.setter
    def iso_threshold(self, value) -> None:
        self._iso_threshold = float(value)
        self._visual.level = self._iso_threshold
        self._visual.update()


class Surface(_SurfaceBase):
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

    @property
    def face_color(self) -> np.ndarray:
        return self._visual.color

    @face_color.setter
    def face_color(self, color) -> None:
        verts, faces, vals = self._data
        self._visual.set_data(
            vertices=verts, faces=faces, vertex_values=vals, color=color
        )
        self._visual.update()
