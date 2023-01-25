from magicclass import (
    get_function_gui,
    magicclass,
    set_options,
    set_design,
    nogui,
    do_not_record,
    bind_key,
    confirm,
    field
)
from magicclass.utils import copy_info, thread_worker
from magicclass.testing import MockConfirmation
from magicgui import magicgui
from types import MethodType

def test_basic_usage():
    conf = MockConfirmation()
    class _T:
        """main widget

        Attributes
        ----------
        x : int
            field-x
        """
        class X:
            @set_options(x={"min": 1}, layout="horizontal")
            @set_design(text="Text")
            def f(self, x: float):
                """doc-f"""

        @do_not_record
        def g(self, y: str):
            """doc-g

            Parameters
            ----------
            y : str
                param-y
            """

        @bind_key("T")
        def h(self):
            ...

        @nogui
        def i(self):
            ...

        @confirm(text="conf-k", callback=conf)
        def k(self):
            ...


    @magicclass
    @copy_info(_T)
    class T:
        _out = None
        @magicclass
        class X:
            def f(self, x: float):
                self._out = x

        def g(self, y: str):
            self._out = y

        def h(self):
            self._out = 0

        def i(self):
            """doc-i"""
            pass

        @magicgui
        def j(self, x: int):
            ...

        def k(self):
            ...

        x = field(int)

    ui = T()
    assert ui.X["f"].text == "Text"
    assert ui.X["f"].tooltip == "doc-f"
    assert get_function_gui(ui.X.f).x.min == 1
    assert get_function_gui(ui.X.f).layout == "horizontal"
    assert ui["g"].tooltip == "doc-g"
    assert get_function_gui(ui.g).y.tooltip == "param-y"
    assert isinstance(ui["i"], MethodType)
    assert ui.i.__doc__ == "doc-i"
    ui["k"].changed()
    conf.assert_value("conf-k")
    assert ui.x.tooltip == "field-x"

def test_thread_worker():
    class _T:
        @set_options(x={"min": 1})
        @set_design(text="Text")
        def f(self, x: int):
            """doc-f"""

    @magicclass
    @copy_info(_T)
    class T:
        @thread_worker
        def f(self, x: int):
            ...

    ui = T()
    assert isinstance(T.f, thread_worker)
    assert ui["f"].tooltip == "doc-f"
    assert ui["f"].text == "Text"
    assert get_function_gui(ui.f).x.min == 1

def test_wraps():
    @magicclass
    class _T:
        def f(self):
            """doc"""

    @magicclass
    @copy_info(_T)
    class T:
        @magicclass
        class A:
            def f(self): ...

        @A.wraps
        def f(self):
            ...

    ui = T()
    assert ui.A["f"].tooltip == "doc"
