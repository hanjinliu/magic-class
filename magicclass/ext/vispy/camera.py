from __future__ import annotations

from psygnal import Signal
from vispy import scene
from vispy.visuals import transforms as tr
from magicgui.widgets import FloatSlider
from ...widgets import FloatRangeSlider
from ...fields import HasFields, vfield


class VispyCamera(scene.ArcballCamera):
    changed = Signal()

    def view_changed(self):
        super().view_changed()


class Camera(HasFields):
    def __init__(self, viewbox: scene.ViewBox) -> None:
        camera = VispyCamera(fov=0)
        viewbox.camera = camera
        self._camera = camera
        camera.transform = tr.MatrixTransform()
        camera.changed.connect(self._on_vispy_camera_change)

    # fmt: off
    fov = vfield(0.0, widget_type=FloatSlider, label="FoV (deg)", options={"max": 45})
    scale = vfield(1.0, widget_type=FloatSlider, label="Scale")
    center = vfield((0.0, 0.0, 0.0), label="Center")
    # fmt: on

    @fov.connect
    def _on_fov_change(self, fov: float):
        self._camera.fov = fov
        self._camera.update()

    @scale.connect
    def _on_scale_change(self, scale: float):
        self._camera.scale_factor = scale
        self._camera.update()

    @center.connect
    def _on_center_change(self, center: tuple[float, float, float]):
        self._camera.center = center
        self._camera.update()

    def _on_vispy_camera_change(self):
        with self.signals.blocked():
            self.fov = self._camera.fov
            self.scale = self._camera.scale_factor
            self.center = self._camera.center
