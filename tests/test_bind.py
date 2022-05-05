from typing import Tuple
from magicclass import magicclass, set_options, field, vfield, magictoolbar
from magicclass.types import Bound, Optional

def test_bind_value():
    # test binding an invariable
    @magicclass
    class A:
        @set_options(x={"bind": 10})
        def func(self, x):
            pass

    ui = A()
    ui["func"].changed()
    assert str(ui.macro[-1]) == "ui.func(x=10)"

def test_bind_method():
    @magicclass
    class A:
        def __init__(self):
            self.i = 0

        def _get_param(self, w=None):
            self.i += 1
            return self.i

        @set_options(x={"bind": _get_param})
        def func(self, x):
            pass

    ui0 = A()
    ui1 = A()

    ui0["func"].changed()
    assert str(ui0.macro[-1]) == "ui.func(x=1)"
    ui0["func"].changed()
    assert str(ui0.macro[-1]) == "ui.func(x=2)"
    assert ui0.i == 2
    assert ui1.i == 0

def test_bind_field():
    @magicclass
    class A:
        a = field(int)
        b = vfield(int)

        @set_options(a={"bind": a})
        def func_a(self, a):
            pass

        @set_options(b={"bind": b})
        def func_b(self, b):
            pass

    ui = A()
    ui["func_a"].changed()
    assert str(ui.macro[-1]) == "ui.func_a(a=0)"
    ui.a.value = 10
    ui["func_a"].changed()
    assert str(ui.macro[-1]) == "ui.func_a(a=10)"

    ui["func_b"].changed()
    assert str(ui.macro[-1]) == "ui.func_b(b=0)"
    ui.b = 10
    ui["func_b"].changed()
    assert str(ui.macro[-1]) == "ui.func_b(b=10)"

def test_Bound():
    @magicclass
    class A:
        def __init__(self):
            self.i = 0

        def _get_param(self, w=None):
            self.i += 1
            return self.i

        a = field("a")

        def func(self, x: Bound[_get_param], y: Bound[a]):
            return x, y

    ui = A()
    ui["func"].changed()
    assert str(ui.macro[-1]) == "ui.func(x=1, y='a')"

def test_wrapped():
    @magicclass
    class A:
        @magictoolbar
        class B:
            field_b = field("b")
            def _b(self, w=None):
                return "b"

            def func_2(self): ...

        field_a = field("a")
        def _a(self, w=None):
            return "a"

        def func_1(self, x: Bound[_a], y: Bound[B.field_b]):
            self.returned = x, y

        @B.wraps
        def func_2(self, x: Bound[field_a], y: Bound[B._b]):
            self.returned = x, y

    ui = A()
    ui["func_1"].changed()
    ui["func_2"].changed()
    assert str(ui.macro[-2]) == "ui.func_1(x='a', y='b')"
    assert str(ui.macro[-1]) == "ui.func_2(x='a', y='b')"

def test_nesting():
    @magicclass
    class A:
        @magicclass
        class B:
            def __init__(self):
                self._a = 0

            def _get_value(self, w=None):
                return self._a

            def func(self, x: Bound[_get_value]):
                self.returned = x

        def func(self, x: Bound[B._get_value]):
            self.returned = x

    ui = A()
    ui["func"].changed()
    ui.B["func"].changed()
    assert ui.returned == 0
    assert ui.B.returned == 0
    ui.B._a = 1
    ui["func"].changed()
    ui.B["func"].changed()
    assert ui.returned == 1
    assert ui.B.returned == 1

def test_external_field():
    @magicclass
    class B:
        x = field(int)

    @magicclass
    class A:
        _a = -1
        b = B
        @b.x.connect
        def _callback(self):
            self._a = 1

        def func(self, x: Bound[b.x]):
            self._a = x

    ui = A()
    assert ui._a == -1
    ui.b.x.value = 10
    assert ui._a == 1
    ui["func"].changed()
    assert ui._a == 10

def test_multi_gui():
    @magicclass
    class A:
        def _bind(self, w=None):
            return id(self)

        def f(self, a: Bound[_bind]):
            self._a = a

    a0 = A()
    a1 = A()


    a0["f"].changed()
    a1["f"].changed()

    assert a0._a == id(a0)
    assert a1._a == id(a1)

def test_annotated():
    @magicclass
    class A:
        x = field(Optional[float])
        y = field(Tuple[int, str])
        _out = None
        def f(self, x0: Bound[x], y0: Bound[y]):
            self._out = (x0, y0)

    ui = A()
    ui.x.value = 0.5
    ui.y.value = (1, "z")
    ui["f"].changed()
    assert ui._out is not None
    assert ui._out == (0.5, (1, "z"))
