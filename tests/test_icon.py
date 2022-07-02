from pathlib import Path
from magicclass import magicclass, magictoolbar, magicmenu, field, set_design, Icon

def _icon_byte(a):
    return a.native.icon().pixmap(10,10).toImage().byteCount()

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
