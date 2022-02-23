from __future__ import annotations
import numpy as np
from vispy.visuals import VolumeVisual, ImageVisual
from vispy import scene
from vispy.scene import visuals


class Image:
    def __init__(
        self,
        data,
        viewbox: scene.ViewBox,
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
