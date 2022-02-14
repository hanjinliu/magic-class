from enum import Enum


class Modifier(str, Enum):
    shift = "shift"
    control = "control"
    alt = "alt"


class Button(str, Enum):
    left = "left"
    right = "right"
    middle = "middle"


class Anchor(str, Enum):
    ...
