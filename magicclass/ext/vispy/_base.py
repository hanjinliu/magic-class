from __future__ import annotations
import numpy as np
from vispy.visuals import Visual
from vispy.scene import transforms


class LayerItem:
    _visual: Visual

    @property
    def visible(self) -> bool:
        """Layer visibility."""
        return self._visual.visible

    @visible.setter
    def visible(self, v: bool) -> None:
        self._visual.visible = v

    def _get_transform(self) -> transforms.MatrixTransform:
        return self._visual.transform

    def affine_transform(self, mtx: np.ndarray):
        """Apply affine transformation to the layer."""
        self._visual.transform = transforms.MatrixTransform(mtx)

    @property
    def translate(self) -> np.ndarray:
        mtx = self._get_transform().matrix
        return mtx[:3, 4]
