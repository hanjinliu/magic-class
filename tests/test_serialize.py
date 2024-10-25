from pathlib import Path
from magicgui import magicgui
from magicclass import magicclass, magicmenu, magictoolbar, field, vfield, MagicTemplate
from magicclass.serialize import serialize, deserialize

def test_serialize_mgui():
    @magicgui
    def func(x: int = 1, y: str = "t"):
        pass

    assert serialize(func) == {"x": 1, "y": "t"}
    deserialize(func, {"x": 2, "y": "s"})
    assert func.x.value == 2
    assert func.y.value == "s"

def test_serialize_class():
    @magicclass(layout="horizontal")
    class B(MagicTemplate):
        left = vfield(0.0)
        right = vfield(0.0)
        def print(self):
            print(self.left, self.right)

    @magicclass
    class A(MagicTemplate):
        b = field(B)
        x = vfield(3)
        y = vfield("aa")

    ui = A()
    assert serialize(ui) == {"b": {"left": 0.0, "right": 0.0}, "x": 3, "y": "aa"}
    deserialize(ui, {"b": {"left": 1.0, "right": 2.0}, "x": 4, "y": "bb"})
    assert ui.x == 4
    assert ui.y == "bb"
    assert ui.b.left == 1.0
    assert ui.b.right == 2.0

def test_serialize_guiclass():
    from magicgui.experimental import guiclass, button

    @guiclass
    class A:
        x: int = 1
        y: str = "a"
        @button
        def print(self):
            print(self.x, self.y)

    a = A()
    assert serialize(a.gui) == {"x": 1, "y": "a"}
    deserialize(a.gui, {"x": 2, "y": "b"})
    assert a.x == 2
    assert a.y == "b"

def test_serialize_value_like_widget():
    @magicclass
    class A(MagicTemplate):
        tup = vfield((3, "t"))
        path = vfield(Path("path/file.txt"))

    ui = A()
    assert serialize(ui) == {"tup": (3, "t"), "path": Path("path/file.txt")}

def test_serialize_class_with_menu():
    @magicmenu
    class B(MagicTemplate):
        left = vfield(0.0)
        right = vfield(0.0)
        def print(self):
            print(self.left, self.right)

    @magicclass
    class A(MagicTemplate):
        b = field(B)
        x = vfield(3)
        y = vfield("aa")

    ui = A()
    assert serialize(ui) == {"b": {"left": 0.0, "right": 0.0}, "x": 3, "y": "aa"}
    deserialize(ui, {"b": {"left": 1.0, "right": 2.0}, "x": 4, "y": "bb"})
    assert ui.x == 4
    assert ui.y == "bb"
    assert ui.b.left == 1.0
    assert ui.b.right == 2.0

def test_serialize_class_with_toolbar():
    @magictoolbar
    class B(MagicTemplate):
        left = vfield(0.0)
        right = vfield(0.0)
        def print(self):
            print(self.left, self.right)

    @magicclass
    class A(MagicTemplate):
        b = field(B)
        x = vfield(3)
        y = vfield("aa")

    ui = A()
    assert serialize(ui) == {"b": {"left": 0.0, "right": 0.0}, "x": 3, "y": "aa"}
    deserialize(ui, {"b": {"left": 1.0, "right": 2.0}, "x": 4, "y": "bb"})
    assert ui.x == 4
    assert ui.y == "bb"
    assert ui.b.left == 1.0
    assert ui.b.right == 2.0

def test_serialize_custom():
    @magicclass
    class A(MagicTemplate):
        x = vfield(3)
        y = vfield("aa")
        def __magicclass_serialize__(self):
            return {"x": self.x}

        def __magicclass_deserialize__(self, data):
            self.x = int(data["x"])

    ui = A()
    assert serialize(ui) == {"x": 3}
    deserialize(ui, {"x": "4"})
    assert ui.x == 4

def test_not_recursion():
    @magicclass
    class A(MagicTemplate):
        x = vfield(3)
        y = vfield("aa")
        def __magicclass_serialize__(self):
            out = serialize(self)
            out["z"] = -1
            return out

        def __magicclass_deserialize__(self, data):
            data.pop("z")
            deserialize(self, data)

    ui = A()
    assert serialize(ui) == {"x": 3, "y": "aa", "z": -1}
    deserialize(ui, {"x": 4, "y": "bb", "z": -5})
    assert ui.x == 4

def test_serialize_with_empty_choices():
    @magicclass
    class A(MagicTemplate):
        def __init__(self):
            self._choices = []

        def _get_choices(self, _):
            return self._choices

        c = field(int).with_choices(_get_choices)
        i = vfield(1)

        def _set_choices(self, choices):
            self._choices = choices
            self.reset_choices()

    ui = A()
    assert serialize(ui) == {"i": 1}
    ui._set_choices([1, 2, 3])
    assert serialize(ui) == {"c": 1, "i": 1}

def test_serialize_value_like_magicclass():
    # this is value-like widget
    @magicclass
    class Params(MagicTemplate):
        x = vfield(1)
        y = vfield("a")

        @property
        def value(self):
            return self.x, self.y

        @value.setter
        def value(self, value):
            self.x, self.y = value

    # this is not value-like widget
    @magicclass
    class X(MagicTemplate):
        x = vfield(2)
        y = vfield("b")

        @property
        def value(self):
            return self.x, self.y

    @magicclass
    class Main(MagicTemplate):
        p = field(Params)
        x = field(X)

    ui = Main()
    assert serialize(ui) == {"p": (1, "a"), "x": {"x": 2, "y": "b"}}
    deserialize(ui, {"p": (3, "c"), "x": {"x": 4, "y": "d"}})
    assert ui.p.x == 3
    assert ui.p.y == "c"
    assert ui.x.x == 4
    assert ui.x.y == "d"

def test_serialize_with_skip_if():
    @magicclass
    class A(MagicTemplate):
        x = vfield(3)
        y = vfield("aa")

        @magicclass
        class B(MagicTemplate):
            z = vfield(4)
            w = vfield("bb")

    ui = A()
    d = serialize(ui, skip_if=lambda x: isinstance(x, str))
    assert d == {"x": 3, "B": {"z": 4}}
