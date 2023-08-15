from __future__ import annotations

from qtpy.QtCore import Qt
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent as _MouseClickEvent
from ._const import Modifier, Button


def _factorize_modifiers(mod):
    out = []
    if mod & Qt.KeyboardModifier.ShiftModifier:
        out.append(Modifier.shift)
    if mod & Qt.KeyboardModifier.ControlModifier:
        out.append(Modifier.control)
    if mod & Qt.KeyboardModifier.AltModifier:
        out.append(Modifier.alt)
    return tuple(out)


def _factorize_buttons(mod):
    out = []
    if mod & Qt.MouseButton.LeftButton:
        out.append(Button.left)
    if mod & Qt.MouseButton.RightButton:
        out.append(Button.right)
    if mod & Qt.MouseButton.MiddleButton:
        out.append(Button.middle)
    return tuple(out)


class MouseClickEvent(_MouseClickEvent):
    """More pythonic way to access the button and modifiers"""

    def __init__(self, event: _MouseClickEvent, coord_item):
        self.accepted = event.accepted
        self.currentItem = (
            coord_item  # This enables mapping from event position to coordinates.
        )
        self._double = event._double
        self._scenePos = event._scenePos
        self._screenPos = event._screenPos
        self._button = event._button
        self._buttons = event._buttons
        self._modifiers = event._modifiers
        self._time = event._time
        self.acceptedItem = event.acceptedItem

    def pos(self) -> tuple[float, float]:
        pos = super().pos()
        return (pos.x(), pos.y())

    def lastPos(self) -> tuple[float, float]:
        pos = super().lastPos()
        return (pos.x(), pos.y())

    def modifiers(self) -> tuple[Modifier, ...]:
        modifiers = super().modifiers()
        return _factorize_modifiers(modifiers)

    def buttons(self) -> tuple[Button, ...]:
        buttons = super().buttons()
        return _factorize_buttons(buttons)

    def __repr__(self) -> str:
        cls = type(self).__name__
        return f"{cls}(pos={self.pos()}, buttons={self.buttons()}, modifiers={self.modifiers()})"
