from magicclass import magicclass, magictoolbar, magicmenu, MagicTemplate
from unittest.mock import MagicMock
from pathlib import Path

from magicclass.fields import field

def test_basic():
    @magicclass
    class A(MagicTemplate):
        def f1(self): ...
        def f2(self, path: Path): ...
        def _private(self): ...
        def f3(self, i: int): ...
    
    ui = A()
    assert len(ui) == 3
    assert ui[0].name == "f1"
    assert ui[1].name == "f2"
    assert ui[2].name == "f3"
    
    # test macro
    mock = MagicMock()
    ui.changed.connect(mock)
    ui[0].changed()
    assert str(ui.macro[-1]) == "ui.f1()"
    mock.assert_called()
    

def test_menu():
    @magicclass
    class A:
        @magicmenu
        class Menu:
            def m1(self): ...
            def m2(self, path: Path): ...
            @magicmenu
            class Inner:
                def inner1(self): ...
                def _private(self): ...
                def inner2(self): ...
            def m3(self, i: int): ...
        def f1(self): ...
        def f2(self, path: Path): ...
        def f3(self, i: int): ...
    
    ui = A()
    assert len(ui) == 3
    assert ui._menubar is not None
    assert len(ui.Menu) == 4
    assert len(ui.Menu.Inner) == 2
    
    # test macro
    ui["f1"].changed()
    assert str(ui.macro[-1]) == "ui.f1()"
    ui.Menu.Inner["inner1"].changed()
    assert str(ui.macro[-1]) == "ui.Menu.Inner.inner1()"

def test_toolbar():
    @magicclass
    class A:
        @magictoolbar
        class Toolbar:
            def m1(self): ...
            def m2(self, path: Path): ...
            @magicmenu
            class Menu:
                def inner1(self): ...
                def _private(self): ...
                def inner2(self): ...
            def m3(self, i: int): ...
        def f1(self): ...
        def f2(self, path: Path): ...
        def f3(self, i: int): ...
    
    ui = A()
    assert len(ui) == 3
    assert ui._menubar is None
    assert len(ui.Toolbar) == 4
    assert len(ui.Toolbar.Menu) == 2
    
    # test macro
    ui["f1"].changed()
    assert str(ui.macro[-1]) == "ui.f1()"
    ui.Toolbar.Menu["inner1"].changed()
    assert str(ui.macro[-1]) == "ui.Toolbar.Menu.inner1()"
    

def test_wraps():
    @magicclass
    class A:
        @magicclass
        class B:
            def f1(self): ...
            def f2(self): ...
            def f3(self): ...
        @B.wraps
        def f2(self):
            self.new_attr = 0
    
    ui = A()
    
    # assert the widget order is conserved
    assert ui.B[0].name == "f1"
    assert ui.B[1].name == "f2"
    assert ui.B[2].name == "f3"
    
    mock = MagicMock()
    ui.changed.connect(mock)
    ui.B["f2"].changed()
    mock.assert_called()
    assert hasattr(ui, "new_attr")
    
def test_double_wrap():
    @magicclass
    class A:
        @magicclass
        class B:
            @magicmenu
            class C:
                def f1(self): ...
                def f2(self): ...
                def f3(self): ...
        @B.C.wraps
        def f2(self):
            self.new_attr = 0
    
    ui = A()
    
    # assert the widget order is conserved
    assert ui.B.C[0].name == "f1"
    assert ui.B.C[1].name == "f2"
    assert ui.B.C[2].name == "f3"
    
    ui.B.C["f2"].changed()
    assert hasattr(ui, "new_attr")


def test_separator():
    from magicclass.widgets import Separator
    @magicclass
    class A:
        @magicmenu
        class Menu:
            def m1(self): ...
            sep = field(Separator)
            i = field(int)
            def m2(self, path: Path): ...
    
    ui = A()
    assert type(ui.Menu[1].widget) is Separator
    assert ui.Menu.sep.native is not ui.Menu[1].native
    
    @magicclass
    class A:
        @magictoolbar
        class Menu:
            def m1(self): ...
            sep = field(Separator)
            i = field(int)
            def m2(self, path: Path): ...
    
    ui = A()
    assert type(ui.Menu[1].widget) is Separator
    assert ui.Menu.sep.native is not ui.i[1].native
    