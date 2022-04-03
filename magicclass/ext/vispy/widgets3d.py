from __future__ import annotations
import numpy as np
from numpy.typing import ArrayLike
from vispy import scene

from .layers3d import Image, IsoSurface, LayerItem, Surface
from ...widgets import FreeWidget
from ...types import Color


class Vispy3DCanvas(FreeWidget):
    def __init__(self):
        super().__init__()
        self._scene = scene.SceneCanvas()
        grid = self._scene.central_widget.add_grid()
        self._viewbox = grid.add_view()
        self._viewbox.camera = scene.ArcballCamera(fov=0)
        self._items: list[LayerItem] = []

        self._scene.create_native()
        self.set_widget(self._scene.native)

    @property
    def layers(self):
        return self._items

    @property
    def camera(self):
        return self._viewbox.camera

    def add_image(
        self,
        data: ArrayLike,
        *,
        contrast_limits: tuple[float, float] = None,
        rendering: str = "mip",
        iso_threshold: float | None = None,
        attenuation: float = 1.0,
        cmap: str = "grays",
        gamma: float = 1.0,
        interpolation: str = "linear",
    ):
        image = Image(
            data,
            self._viewbox,
            contrast_limits=contrast_limits,
            rendering=rendering,
            iso_threshold=iso_threshold,
            attenuation=attenuation,
            cmap=cmap,
            gamma=gamma,
            interpolation=interpolation,
        )

        self._items.append(image)
        self._viewbox.camera.scale_factor = max(data.shape)
        self._viewbox.camera.center = [s / 2 - 0.5 for s in data.shape]
        return image

    def add_isosurface(
        self,
        data: ArrayLike,
        *,
        contrast_limits: tuple[float, float] | None = None,
        iso_threshold: float | None = None,
        face_color: Color | None = None,
        edge_color: Color | None = None,
        shading: str = "smooth",
    ):
        surface = IsoSurface(
            data,
            self._viewbox,
            contrast_limits=contrast_limits,
            iso_threshold=iso_threshold,
            edge_color=edge_color,
            face_color=face_color,
            shading=shading,
        )

        self._items.append(surface)
        self._viewbox.camera.scale_factor = max(data.shape)
        self._viewbox.camera.center = [s / 2 - 0.5 for s in data.shape]
        return surface

    def add_surface(
        self,
        data: tuple[ArrayLike, ArrayLike] | tuple[ArrayLike, ArrayLike, ArrayLike],
        *,
        face_color: Color | None = None,
        edge_color: Color | None = None,
        shading: str = "smooth",
    ):
        surface = Surface(
            data,
            self._viewbox,
            face_color=face_color,
            edge_color=edge_color,
            shading=shading,
        )
        self._items.append(surface)
        mins = np.min(data[0], axis=0)
        maxs = np.max(data[0], axis=0)
        self._viewbox.camera.scale_factor = max(maxs - mins)
        self._viewbox.camera.center = [(s1 - s0) / 2 for s0, s1 in zip(mins, maxs)]
        return surface
