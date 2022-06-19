from magicclass import magicclass, magictoolbar, magicmenu, MagicTemplate
from unittest.mock import MagicMock
from pathlib import Path
from types import MethodType

from magicclass.fields import field

def test_basic():
    @magicclass
    class A(MagicTemplate):
        def f1(self): ...
        def f2(self, path: Path): ...
        # "type" will raise error if magicgui try to interpret the annotation
        def _private(self, arg: type): ...
        def f3(self, i: int): ...

    ui = A()
    assert len(ui) == 3
    assert ui[0].name == "f1"
    assert ui[1].name == "f2"
    assert ui[2].name == "f3"
    assert isinstance(ui["_private"], MethodType)

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


def test_separator():
    from magicclass.widgets import Separator
    @magicclass
    class A:
        @magicmenu
        class Menu:
            def m1(self): ...
            sep0 = field(Separator)
            i = field(int)
            sep1 = Separator()
            def m2(self, path: Path): ...

    ui = A()
    assert type(ui.Menu[1].widget) is Separator
    assert type(ui.Menu[3].widget) is Separator

    @magicclass
    class A:
        @magictoolbar
        class Menu:
            def m1(self): ...
            sep0 = field(Separator)
            i = field(int)
            sep1 = Separator()
            def m2(self, path: Path): ...

    ui = A()
    assert type(ui.Menu[1].widget) is Separator
    assert type(ui.Menu[3].widget) is Separator


def test_tooltip():
    @magicclass(widget_type="mainwindow")
    class A:
        @magicmenu
        class Menu:
            def func(self, a: int):
                """
                Test tooltip.

                Parameters
                ----------
                a : int
                    Tooltip of a.
                """

        @magictoolbar
        class Tool:
            def func(self, a: int):
                """
                Test tooltip.

                Parameters
                ----------
                a : int
                    Tooltip of a.
                """

        def func(self, a: int):
            """
            Test tooltip.

            Parameters
            ----------
            a : int
                Tooltip of a.
            """

    _TOOLTIP = "Test tooltip."
    _PARAM_TOOLTIP = "Tooltip of a."

    ui = A()
    ui.show(False)

    assert ui["func"].tooltip == _TOOLTIP
    assert ui.Menu["func"].tooltip == _TOOLTIP
    assert ui.Tool["func"].tooltip == _TOOLTIP

    ui["func"].changed()
    ui["func"].mgui._call_button.changed()
    ui.Menu["func"].changed()
    ui.Menu["func"].mgui._call_button.changed()
    ui.Tool["func"].changed()
    ui.Tool["func"].mgui._call_button.changed()

    assert ui["func"].mgui.a.tooltip == _PARAM_TOOLTIP
    assert ui.Menu["func"].mgui.a.tooltip == _PARAM_TOOLTIP
    assert ui.Tool["func"].mgui.a.tooltip == _PARAM_TOOLTIP


def test_post_append():
    @magicclass(widget_type="mainwindow")
    class A:
        @magicmenu
        class Menu:
            def func(self, a: int): ...

        @magictoolbar
        class Tool:
            def func(self, a: int): ...

    ui = A()

    def new_func_1(): ...
    def new_func_2(): ...
    def new_func_3(): ...

    ui.append(new_func_1)
    ui.Menu.append(new_func_2)
    ui.Tool.append(new_func_3)

    ui["new_func_1"].changed()
    assert str(ui.macro[-1]) == "ui.new_func_1()"
    ui.Menu["new_func_2"].changed()
    assert str(ui.macro[-1]) == "ui.Menu.new_func_2()"
    ui.Tool["new_func_3"].changed()
    assert str(ui.macro[-1]) == "ui.Tool.new_func_3()"


def test_labels_arg():
    """Test 'labels=False' works in menubar and toolbar."""
    @magicclass
    class A:
        @magicmenu
        class Menu:
            a = field(int)

        @magictoolbar
        class Tool:
            a = field(int)

    ui = A()

    assert ui.Menu.a._labeled_widget() is not None
    assert ui.Tool.a._labeled_widget() is not None

    @magicclass
    class A:
        @magicmenu(labels=False)
        class Menu:
            a = field(int)

        @magictoolbar(labels=False)
        class Tool:
            a = field(int)

    ui = A()

    assert ui.Menu.a._labeled_widget() is None
    assert ui.Tool.a._labeled_widget() is None


@magicmenu(name="Menu 1")
class Menu1:
    def m(self): ...

@magicclass(name="My Widget")
class MyWidget:
    def f(self): ...

@magicclass
class Main:
    @magicmenu
    class Menu:
        menu1 = Menu1
    MyWidget = MyWidget

def test_names():
    ui = Main()
    assert ui.MyWidget.name == "My Widget"
    assert ui.Menu.menu1.name == "Menu 1"
    ui.MyWidget["f"].changed()
    assert str(ui.macro[-1]) == "ui.MyWidget.f()"
    ui.Menu.menu1["m"].changed()
    assert str(ui.macro[-1]) == "ui.Menu.menu1.m()"

def test_default_init():
    @magicclass
    class A:
        pass

    ui_a = A(name="a")
    ui_b = A(name="b")
    assert ui_a.name == "a"
    assert ui_b.name == "b"

    @magicclass
    class B:
        def __init__(self, param=None):
            self.param = param

    ui = B(param=10)
    assert ui.param == 10
