from types import MethodType
from unittest.mock import MagicMock
from magicclass import magicclass, set_options, get_function_gui
from magicclass.testing import MockConfirmation
from magicgui.widgets import PushButton


def test_set_options():
    @magicclass
    class A:
        @set_options(layout="horizontal", call_button="OK", a={"widget_type": "Slider"})
        def f1(self, a: int):
            pass

        @set_options(auto_call=True)
        def f2(self, a: int):
            self.a = a

    ui = A()
    ui["f1"].changed()
    assert ui["f1"].mgui._layout == "horizontal"
    assert ui["f1"].mgui._call_button.text == "OK"
    assert ui["f1"].mgui["a"].widget_type == "Slider"

    ui["f2"].changed()
    assert ui["f2"].mgui._auto_call == True
    ui["f2"].mgui["a"].value = 2
    assert ui.a == 2
    assert str(ui.macro[-1]) == "ui.f2(a=2)"
    assert ui["f2"].mgui.visible
    ui["f2"].mgui["a"].value = 4
    assert ui.a == 4
    assert str(ui.macro[-1]) == "ui.f2(a=4)"
    assert str(ui.macro[-2]) != "ui.f2(a=2)" # for auto_call, macro should be recorded once.

def test_mgui_options():
    @magicclass
    class A:
        @set_options(layout="horizontal", auto_call=True)
        def f(self, a: int):
            self._a = a

    ui = A()
    ui["f"].changed()
    assert ui["f"].mgui.layout == "horizontal"
    ui["f"].mgui[0].value = 3
    assert ui._a == 3
    assert str(ui.macro[-1]) == "ui.f(a=3)"
    ui["f"].mgui[0].value = 5
    assert ui._a == 5
    assert str(ui.macro[-1]) == "ui.f(a=5)"
    assert str(ui.macro[-2]) != "ui.f(a=3)"

def test_annotated():
    """Test Annotated type is correctly updated."""
    from typing_extensions import Annotated
    @magicclass
    class A:
        @set_options(a={"max": 5})
        def f(self, a: Annotated[int, {"min": -5}]):
            pass

    ui = A()
    ui["f"].changed()
    assert ui["f"].mgui.a.min == -5
    assert ui["f"].mgui.a.max == 5

def test_set_design():
    from magicclass import set_design

    @magicclass
    class A:
        @set_design(text="new-text")
        def f1(self, a: int):
            pass

    ui = A()
    assert ui["f1"].text == "new-text"

def test_do_not_record():
    from magicclass import do_not_record
    @magicclass
    class A:
        @do_not_record
        def f(self): pass

    ui = A()
    ui["f"].changed()
    assert len(ui.macro) == 1

def test_nogui():
    from magicclass import nogui
    @magicclass
    class A:
        @nogui
        def f(self):
            pass

        def g(self):
            pass

    ui = A()
    assert isinstance(ui["f"], MethodType)
    assert isinstance(ui["g"], PushButton)

def test_impl_preview():
    from magicclass import impl_preview

    mock = MagicMock()
    @magicclass
    class A:
        @impl_preview(text="preview 0")
        def f0(self, x: int, y: str = "v"):
            mock(x=x, y=y)

        @impl_preview(text="preview 1")
        def f1(self, x: int = 10):
            mock(x=x)

        @f0.set_preview
        @f1.set_preview
        def _preview(self, x):
            mock(x=x, preview=True)

    ui = A()
    f0_gui = get_function_gui(ui, "f0")
    assert f0_gui[-2].widget_type == "PushButton"
    assert f0_gui[-2].text == "preview 0"
    f1_gui = get_function_gui(ui, "f1")
    assert f1_gui[-2].widget_type == "PushButton"
    assert f1_gui[-2].text == "preview 1"

    f0_gui[-2].changed()
    mock.assert_called_with(x=0, preview=True)
    assert str(ui.macro[-1]).startswith("#")
    mock.reset_mock()

    f0_gui[-1].changed()
    mock.assert_called_with(x=0, y="v")
    assert str(ui.macro[-1]) == "ui.f0(x=0, y='v')"
    mock.reset_mock()

    f1_gui[-2].changed()
    mock.assert_called_with(x=10, preview=True)
    assert str(ui.macro[-1]) == "ui.f0(x=0, y='v')"
    mock.reset_mock()

    f1_gui[-1].changed()
    mock.assert_called_with(x=10)
    assert str(ui.macro[-1]) == "ui.f1(x=10)"

def test_impl_preview_nested():
    from magicclass import impl_preview

    mock = MagicMock()

    @magicclass
    class A:
        @magicclass
        class B:
            @impl_preview(text="preview 0")
            def f0(self, x: int, y: str = "v"):
                mock(type=type(self), x=x, y=y)

            @impl_preview(text="preview 1")
            def f1(self, x: int = 10):
                mock(type=type(self), x=x)

        @B.f0.set_preview
        @B.f1.set_preview
        def _preview(self, x):
            mock(type=type(self), x=x, preview=True)

    ui = A()
    f0_gui = get_function_gui(ui.B, "f0")
    assert f0_gui[-2].widget_type == "PushButton"
    assert f0_gui[-2].text == "preview 0"
    f1_gui = get_function_gui(ui.B, "f1")
    assert f1_gui[-2].widget_type == "PushButton"
    assert f1_gui[-2].text == "preview 1"

    f0_gui[-2].changed()
    mock.assert_called_with(type=A, x=0, preview=True)
    assert str(ui.macro[-1]).startswith("#")
    mock.reset_mock()

    f0_gui[-1].changed()
    mock.assert_called_with(type=type(ui.B), x=0, y="v")
    assert str(ui.macro[-1]) == "ui.B.f0(x=0, y='v')"
    mock.reset_mock()

    f1_gui[-2].changed()
    mock.assert_called_with(type=A, x=10, preview=True)
    mock.reset_mock()
    assert str(ui.macro[-1]) == "ui.B.f0(x=0, y='v')"

    f1_gui[-1].changed()
    mock.assert_called_with(type=type(ui.B), x=10)
    assert str(ui.macro[-1]) == "ui.B.f1(x=10)"

def test_impl_preview_using_itself():
    from magicclass import impl_preview

    mock = MagicMock()

    @magicclass
    class A:
        @impl_preview
        def f(self, i: int):
            mock(i)

    ui = A()
    f_gui = get_function_gui(ui, "f")
    assert f_gui[-2].widget_type == "PushButton"

    mock.assert_not_called()

    f_gui[-2].changed()
    mock.assert_called_with(0)
    assert str(ui.macro[-1]).startswith("#")
    mock.reset_mock()

    f_gui[-1].changed()
    mock.assert_called_with(0)
    assert str(ui.macro[-1]) == "ui.f(i=0)"


def test_confirm():
    from magicclass import confirm

    # The basic usage
    mconf = MockConfirmation()

    @magicclass
    class A:
        @confirm(text="conf-text", callback=mconf)
        def f(self, a: int):
            pass

    ui = A()

    mconf.assert_not_called()
    ui.f(0)
    mconf.assert_not_called()  # no confirmation if executed programatically
    get_function_gui(ui, "f")()
    mconf.assert_value("conf-text")

    # text formating
    mconf = MockConfirmation()

    @magicclass
    class A:
        @confirm(text="<{a}>", callback=mconf)
        def f(self, a: int):
            pass

    ui = A()

    mconf.assert_not_called()
    fgui = get_function_gui(ui, "f")
    fgui()
    mconf.assert_value("<0>")
    fgui.a.value = 16
    fgui()
    mconf.assert_value("<16>")

    # test condition

    mconf = MockConfirmation()

    @magicclass
    class A:
        @confirm(text="conf-text", condition="a>5", callback=mconf)
        def f(self, a: int):
            pass

    ui = A()

    mconf.assert_not_called()
    fgui = get_function_gui(ui, "f")
    fgui()
    mconf.assert_not_called()
    fgui.a.value = 16
    fgui()
    mconf.assert_value("conf-text")

def test_confirm_with_other_wrapper():
    from magicclass import confirm

    # The basic usage
    mconf = MockConfirmation()

    @magicclass
    class A:
        @set_options(a={"max": 10})
        @confirm(text="conf-text-1", callback=mconf)
        def f1(self, a: int):
            pass

        @confirm(text="conf-text-2", callback=mconf)
        @set_options(a={"max": 12})
        def f2(self, a: int):
            pass

    ui = A()
    fgui1 = get_function_gui(ui, "f1")
    fgui2 = get_function_gui(ui, "f2")
    assert fgui1.a.max == 10
    assert fgui2.a.max == 12

    mconf.assert_not_called()
    fgui1()
    mconf.assert_value("conf-text-1")
    fgui2()
    mconf.assert_value("conf-text-2")

def test_confirm_with_thread_worker():
    from magicclass import confirm
    from magicclass.utils import thread_worker

    mconf = MockConfirmation()

    @magicclass
    class A:
        @thread_worker
        @confirm(text="conf-text-1", callback=mconf)
        def f1(self, a: int):
            pass

        @confirm(text="conf-text-2", callback=mconf)
        @thread_worker
        def f2(self, a: int):
            pass

    ui = A()
    fgui1 = get_function_gui(ui, "f1")
    fgui2 = get_function_gui(ui, "f2")
    assert isinstance(A.f1, thread_worker)
    assert isinstance(A.f2, thread_worker)

    mconf.assert_not_called()
    fgui1()
    mconf.assert_value("conf-text-1")
    fgui2()
    mconf.assert_value("conf-text-2")
