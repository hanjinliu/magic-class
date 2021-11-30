from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
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
    PageDown = "pagedown"
    Shift = "shift"
    Control = "control"
    Meta = "meta"
    Alt = "alt"
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"
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
    
# TODO: modifiers not working

def parse_key_combo(key_combo: str) -> QtKey:
    # For compatibility with napari
    parsed = re.split("-(?=.+)", key_combo)
    return get_qt_key_enum(*parsed)

def str2qtkey(s: str) -> QtKey:
    s = s.lower()
    if s == "ctrl":
        s = "control"
    return getattr(Qt, f"Key_{Key(s).name}")

def get_qt_key_enum(*args: tuple[str, ...]) -> QtKey:
    return sum(map(str2qtkey, args))

def as_shortcut(key_combo: tuple):
    try:
        qtkey = get_qt_key_enum(*key_combo)
    except ValueError as e:
        print(e)
        if len(key_combo) != 1:
            raise e
        qtkey = parse_key_combo(key_combo[0])
    return QKeySequence(qtkey)