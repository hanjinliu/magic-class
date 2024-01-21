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
