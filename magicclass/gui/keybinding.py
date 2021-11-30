from qtpy.QtCore import Qt
from enum import Enum
from typing import Callable, NewType
import re

QtKey = NewType("QtKey", int)

class Key(Enum):
    Tab = "tab"
    Backspace = "backspace"
    Delete = "delete"
    Left = "left"
    Up = "up"
    Right = "right"
    Down = "down"
    PageUp = "pageup"
    PageDown = "PageDown"
    Shift = "shift"
    Control = "control"
    Meta = "meta"
    Alt = "alt"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"
    F8 = "F8"
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"
    Exclam = "!"
    Dollar = "$"
    Percent = "%"
    Ampersand = "&"
    Apostrophe = "'"
    ParenLeft = "("
    ParenRight = ")"
    Asterisk = "*"
    Plus = "+"
    Comma = ","
    Minus = "-"
    Period = "."
    Slash = "/"
    Colon = ":"
    Semicolon = ";"
    Less = "<"
    Equal = "="
    Greater = ">"
    Question = "?"
    At = "@"
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"
    X = "x"
    Y = "y"
    Z = "z"

KEY_MAPPING: dict[Key, QtKey] = {k: getattr(Qt, f"Key_{k}") for k in Key._member_map_.values()}
MODIFIERS = [Key.Control, Key.Alt, Key.Shift, Key.Meta]

def parse_key_combo(key_combo: str) -> QtKey:
    # For compatibility with napari
    parsed = re.split("-(?=.+)", key_combo)
    return get_qt_key_enum(*parsed)

def str2qtkey(s: str) -> QtKey:
    s = s.lower()
    if s == "ctrl":
        s = "control"
    return KEY_MAPPING[Key(s)]

def get_qt_key_enum(*args: tuple[str, ...]) -> QtKey:
    # a = args[0]
    # or_sum = KEY_MAPPING(Key(a))
    # if len(args) > 1:
    #     for a in args[1:]:
    #         or_sum |= KEY_MAPPING(Key(a))
    
    # return or_sum
    return sum(map(str2qtkey, args))

class QtKeyMap(dict[QtKey, Callable]):
    def connect(self, key_combo: tuple, function: Callable = None):
        if function is None:
            raise TypeError("function must be given")
        try:
            qtkey = get_qt_key_enum(*key_combo)
        except ValueError as e:
            if len(key_combo) != 1:
                raise e
            qtkey = parse_key_combo(key_combo[0])
        self[qtkey] = function
        return function