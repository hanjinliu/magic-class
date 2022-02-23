from __future__ import annotations
import numpy as np
from vispy.visuals import VolumeVisual, MeshVisual
from vispy import scene
from vispy.scene import visuals
from skimage.measure import marching_cubes


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
        if not isinstance(data, np.ndarray):
            raise TypeError("Only ndarray is supported.")
        if data.ndim != 3:
            raise ValueError("data must be 3D.")
        if data.dtype == np.float64:
            data = data.astype(np.float32)
        if contrast_limits is None:
            contrast_limits = "auto"
        elif len(contrast_limits) != 2:
            raise TypeError("'contrast_limits' must be two floats")

        self._data = data
        self._contrast_limits = contrast_limits
        self._rendering = rendering
        self._iso_threshold = iso_threshold
        self._attenuation = attenuation
        self._cmap = cmap
        self._gamma = gamma
        self._interpolation = interpolation

        self._viewbox = viewbox

        self._current_visual: VolumeVisual | MeshVisual = None
        if rendering == "mesh":
            self._as_mesh()
        else:
            self._as_volume()

    def _as_volume(self):
        if self._is_mesh():
            self._current_visual.parent = None
            del self._current_visual
        self._current_visual = visuals.Volume(
            self._data,
            clim=self._contrast_limits,
            method=self._rendering,
            threshold=self._iso_threshold,
            attenuation=self._attenuation,
            cmap=self._cmap,
            gamma=self._gamma,
            interpolation=self._interpolation,
            parent=self._viewbox.scene,
        )

    def _as_mesh(self):
        if self._is_volume():
            self._current_visual.parent = None
            del self._current_visual

        self._current_visual = self._create_mesh(self._data, self._iso_threshold)

    def _is_volume(self) -> bool:
        return isinstance(self._current_visual, VolumeVisual)

    def _is_mesh(self) -> bool:
        return isinstance(self._current_visual, MeshVisual)

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value) -> None:
        if self._is_volume():
            self._data = value
            self._current_visual.set_data(value)
        elif self._is_mesh():
            self._data = value
            self._update_mesh(value)
        else:
            raise NotImplementedError(type(self._current_visual))

    @property
    def contrast_limits(self) -> tuple[float, float]:
        return self._contrast_limits

    @contrast_limits.setter
    def contrast_limits(self, value) -> None:
        self._current_visual.clim = value
        self._contrast_limits = value

    @property
    def rendering(self) -> str:
        return self._rendering

    @rendering.setter
    def rendering(self, value: str) -> None:
        if value == "mesh" and not self._is_mesh():
            self._as_mesh()
        else:
            if not self._is_volume():
                self._as_volume()
            self._current_visual.method = value
        self._rendering = value

    @property
    def iso_threshold(self) -> float:
        return self._iso_threshold

    @iso_threshold.setter
    def iso_threshold(self, value) -> None:
        self._iso_threshold = float(value)
        if self.rendering == "mesh":
            self._update_mesh()
        else:
            self._current_visual.threshold = self._iso_threshold
        self._current_visual.update()

    def _create_mesh(self, volume, level, *, step_size=1):
        verts, faces, normals, values = marching_cubes(
            volume,
            level=level,
            step_size=step_size,
        )
        n_verts = verts.shape[0]
        n_faces = faces.shape[0]

        return visuals.Mesh(
            verts[:, ::-1],
            faces[:, ::-1],
            color=(1, 0, 0, 1),
            # vertex_colors=np.stack([np.ones(4)]*n_verts, axis=0),
            face_colors=np.zeros((n_faces, 4)),
            parent=self._viewbox._scene,
        )

    def _update_mesh(self, step_size=1):
        verts, faces, _, values = marching_cubes(
            self._data,
            level=self._iso_threshold,
        )
        n_verts = verts.shape[0]
        n_faces = faces.shape[0]
        self._current_visual.set_data(
            verts[:, ::-1],
            faces[:, ::-1],
            color=(1, 0, 0, 1),
            # vertex_colors=np.stack([np.ones(4)]*n_verts, axis=0),
            face_colors=np.zeros((n_faces, 4)),
        )
