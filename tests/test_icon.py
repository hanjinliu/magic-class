from pathlib import Path
from magicclass import magicclass, magictoolbar, magicmenu, field, set_design, Icon
from qtpy.QtGui import QIcon

def _icon_byte(a):
    icon: QIcon = a.native.icon()
    return icon.pixmap(10,10).toImage().sizeInBytes()

def test_icon():

    path = Path(__file__).parent / "icons" / "star.png"

    @magicclass
    class A:
        @magicmenu
        class Menu:
            a = field(bool, options={"icon": path})
            @set_design(icon=path)
            def func(self): ...

    ui = A()

    assert _icon_byte(ui.Menu.a) > 0
    assert _icon_byte(ui.Menu["func"]) > 0

    @magicclass
    class A:
        @magictoolbar
        class Menu:
            a = field(bool, options={"icon": path})
            @set_design(icon=path)
            def func(self): ...

    ui = A()

    assert _icon_byte(ui.Menu.a) > 0
    assert _icon_byte(ui.Menu["func"]) > 0

def test_standard_icon():

    @magicclass
    class A:
        @magicmenu
        class Menu:
            a = field(bool, options={"icon": Icon.FileIcon})
            @set_design(icon=Icon.FileIcon)
            def func(self): ...

    ui = A()

    assert _icon_byte(ui.Menu.a) > 0
    assert _icon_byte(ui.Menu["func"]) > 0

    @magicclass
    class A:
        @magictoolbar
        class Menu:
            a = field(bool, options={"icon": Icon.FileIcon})
            @set_design(icon=Icon.FileIcon)
            def func(self): ...

    ui = A()

    assert _icon_byte(ui.Menu.a) > 0
    assert _icon_byte(ui.Menu["func"]) > 0

def test_icon_in_class_construction():
    @magicclass(icon=Icon.ArrowUp)
    class A:
        @magicmenu
        class Menu:
            @magicmenu(icon=Icon.ArrowBack)
            class X:
                pass

    ui = A()
    assert ui.native.windowIcon().pixmap(10,10).toImage().sizeInBytes() > 0
    assert _icon_byte(ui.Menu.X) > 0
