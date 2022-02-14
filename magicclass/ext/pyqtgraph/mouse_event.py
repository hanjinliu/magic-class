from __future__ import annotations

from qtpy.QtCore import Qt
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent as _MouseClickEvent
from ._const import Modifier, Button


def _factorize_modifiers(mod):
    out = []
    if mod & Qt.ShiftModifier:
        out.append(Modifier.shift)
    if mod & Qt.ControlModifier:
        out.append(Modifier.control)
    if mod & Qt.AltModifier:
        out.append(Modifier.alt)
    return tuple(out)


def _factorize_buttons(mod):
    out = []
    if mod & Qt.LeftButton:
        out.append(Button.left)
    if mod & Qt.RightButton:
        out.append(Button.right)
    if mod & Qt.MiddleButton:
        out.append(Button.middle)
    return tuple(out)


class MouseClickEvent(_MouseClickEvent):
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

    def pos(self):
        pos = super().pos()
        return (pos.x(), pos.y())

    def lastPos(self):
        pos = super().lastPos()
        return (pos.x(), pos.y())

    def modifiers(self):
        modifiers = super().modifiers()
        return _factorize_modifiers(modifiers)

    def buttons(self):
        buttons = super().buttons()
        return _factorize_buttons(buttons)
