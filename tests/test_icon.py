from pathlib import Path

import pytest
from magicclass import magicclass, magictoolbar, magicmenu, field, set_design
from qtpy.QtGui import QIcon

def _icon_byte(a):
    icon: QIcon = a.native.icon()
    return icon.pixmap(10,10).toImage().sizeInBytes()

PATH_STAR = Path(__file__).parent / "icons" / "star.png"
PATH_TRIANGLE = Path(__file__).parent / "icons" / "triangle.svg"

@pytest.mark.parametrize("icon_path", [PATH_STAR, PATH_TRIANGLE])
def test_icon(icon_path: Path):
    @magicclass
    class A:
        @magicmenu
        class Menu:
            a = field(bool, options={"icon": icon_path})
            @set_design(icon=icon_path)
            def func(self): ...

    ui = A()

    assert _icon_byte(ui.Menu.a) > 0
    assert _icon_byte(ui.Menu["func"]) > 0

    @magicclass
    class A:
        @magictoolbar
        class Menu:
            a = field(bool, options={"icon": icon_path})
            @set_design(icon=icon_path)
            def func(self): ...

    ui = A()

    assert _icon_byte(ui.Menu.a) > 0
    assert _icon_byte(ui.Menu["func"]) > 0

@pytest.mark.parametrize("icon_path", [PATH_STAR, PATH_TRIANGLE])
def test_icon_in_class_construction(icon_path: Path):
    @magicclass(icon=icon_path)
    class A:
        @magicmenu
        class Menu:
            @magicmenu(icon=icon_path)
            class X:
                pass

    ui = A()
    assert ui.native.windowIcon().pixmap(10, 10).toImage().sizeInBytes() > 0
    assert _icon_byte(ui.Menu.X) > 0
