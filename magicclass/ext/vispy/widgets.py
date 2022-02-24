from __future__ import annotations
import numpy as np
from vispy import scene

from .image import Image, IsoSurface
from ...widgets import FreeWidget


class VispyCanvas(FreeWidget):
    def __init__(self):
        super().__init__()
        self._scene = scene.SceneCanvas()
        grid = self._scene.central_widget.add_grid()
        self._viewbox = grid.add_view()
        self._viewbox.camera = scene.TurntableCamera(elevation=30, azimuth=30)
        self._layers = []

        self._scene.create_native()
        self.set_widget(self._scene.native)

    @property
    def layers(self):
        return self._layers

    @property
    def camera(self):
        return self._viewbox.camera

    def add_image(
        self,
        data: np.ndarray,
        *,
        contrast_limits=None,
        rendering="mip",
        iso_threshold=None,
        attenuation=1.0,
        cmap="grays",
        gamma=1.0,
        interpolation="linear",
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

        self._layers.append(image)
        self._viewbox.camera.scale_factor = max(data.shape)
        self._viewbox.camera.center = [s / 2 - 0.5 for s in data.shape]

    def add_isosurface(
        self,
        data: np.ndarray,
        *,
        contrast_limits=None,
        iso_threshold=None,
        wire_color=None,
        face_color=None,
    ):
        surface = IsoSurface(
            data,
            self._viewbox,
            contrast_limits=contrast_limits,
            iso_threshold=iso_threshold,
            wire_color=wire_color,
            face_color=face_color,
        )

        self._layers.append(surface)
        self._viewbox.camera.scale_factor = max(data.shape)
        self._viewbox.camera.center = [s / 2 - 0.5 for s in data.shape]
