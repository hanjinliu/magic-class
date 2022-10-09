from __future__ import annotations

import numpy as np
from psygnal import Signal
from vispy import scene
from magicgui.widgets import FloatSlider, Container
from ...fields import HasFields, vfield


class VispyCamera(scene.ArcballCamera):
    changed = Signal()

    def view_changed(self):
        super().view_changed()
        self.changed.emit()

    def viewbox_key_event(self, event):
        pass


class EulerAngleEdit(Container):
    def __init__(
        self,
        value: tuple[float, float, float] = (0.0, 0.0, 0.0),
        layout: str = "horizontal",
        nullable: bool = False,
        **kwargs,
    ):
        rx, ry, rz = value
        self.rx = FloatSlider(value=rx, min=-180, max=180)
        self.ry = FloatSlider(value=ry, min=-90, max=90)
        self.rz = FloatSlider(value=rz, min=-180, max=180)
        super().__init__(widgets=[self.rx, self.ry, self.rz], layout=layout, **kwargs)
        self.margins = (0, 0, 0, 0)
        for wdt in [self.rx, self.ry, self.rz]:
            wdt.changed.disconnect()
            wdt.changed.connect(self._on_changed)

    @property
    def value(self) -> tuple[float, float, float]:
        return self.rx.value, self.ry.value, self.rz.value

    @value.setter
    def value(self, angles):
        angles = tuple(angles)
        if len(angles) != 3:
            raise ValueError("Euler angles must be a 3-tuple")
        self.rx.value, self.ry.value, self.rz.value = angles

    def _on_changed(self):
        return self.changed.emit(self.value)


class Camera(HasFields):
    def __init__(self, viewbox: scene.ViewBox) -> None:
        camera = VispyCamera(fov=0)
        viewbox.camera = camera
        self._camera = camera
        camera.changed.connect(self._on_vispy_camera_change)

    # fmt: off
    fov = vfield(0.0, widget_type=FloatSlider, label="FoV (deg)", options={"max": 45})
    scale = vfield(1.0, widget_type=FloatSlider, label="Scale")
    center = vfield((0.0, 0.0, 0.0), label="Center")
    angles = vfield((0.0, 0.0, 90.0), widget_type=EulerAngleEdit, label="Angles (deg)")
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
    def _on_center_change(self):
        self._camera.center = self.center  # TupleEdit signal is wrong now
        self._camera.update()

    @angles.connect
    def _on_angles_change(self, angles: tuple[float, float, float]):
        # Create and set quaternion
        quat = self._camera._quaternion.create_from_euler_angles(
            *angles,
            degrees=True,
        )
        self._camera._quaternion = quat
        self._camera.view_changed()
        self._camera.update()

    def _on_vispy_camera_change(self):
        with self.signals.blocked():
            self.fov = self._camera.fov
            self.scale = self._camera.scale_factor
            self.center = self._camera.center
            angles = quaternion2euler(self._camera._quaternion, degrees=True)
            self.angles = angles


# copied from napari/_vispy/utils/quaternion.py
def quaternion2euler(quaternion, degrees=False) -> tuple[float, float, float]:
    """Converts VisPy quaternion into euler angle representation.

    Euler angles have degeneracies, so the output might different
    from the Euler angles that might have been used to generate
    the input quaternion.

    Euler angles representation also has a singularity
    near pitch = Pi/2 ; to avoid this, we set to Pi/2 pitch angles
    that are closer than the chosen epsilon from it.

    Parameters
    ----------
    quaternion : vispy.util.Quaternion
        Quaternion for conversion.
    degrees : bool
        If output is returned in degrees or radians.

    Returns
    -------
    angles : 3-tuple
        Euler angles in (rx, ry, rz) order.
    """
    epsilon = 1e-10

    q = quaternion

    sin_theta_2 = 2 * (q.w * q.y - q.z * q.x)
    sin_theta_2 = np.sign(sin_theta_2) * min(abs(sin_theta_2), 1)

    if abs(sin_theta_2) > 1 - epsilon:
        theta_1 = -np.sign(sin_theta_2) * 2 * np.arctan2(q.x, q.w)
        theta_2 = np.arcsin(sin_theta_2)
        theta_3 = 0.0

    else:
        theta_1 = np.arctan2(
            2 * (q.w * q.z + q.y * q.x),
            1 - 2 * (q.y * q.y + q.z * q.z),
        )

        theta_2 = np.arcsin(sin_theta_2)

        theta_3 = np.arctan2(
            2 * (q.w * q.x + q.y * q.z),
            1 - 2 * (q.x * q.x + q.y * q.y),
        )

    angles = (theta_1, theta_2, theta_3)

    if degrees:
        return tuple(np.degrees(angles))
    else:
        return angles
