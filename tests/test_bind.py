from typing import Tuple
from typing_extensions import Annotated
from magicclass import magicclass, set_options, set_design, field, vfield, magictoolbar, get_button, magicmenu, abstractapi
from magicclass.types import Bound, Optional

def test_bind_value():
    # test binding an invariable
    @magicclass
    class A:
        @set_options(x={"bind": 10})
        def func(self, x):
            pass

    ui = A()
    get_button(ui.func).changed()
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

    get_button(ui0.func).changed()
    assert str(ui0.macro[-1]) == "ui.func(x=1)"
    get_button(ui0.func).changed()
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
    get_button(ui.func_a).changed()
    assert str(ui.macro[-1]) == "ui.func_a(a=0)"
    ui.a.value = 10
    get_button(ui.func_a).changed()
    assert str(ui.macro[-1]) == "ui.func_a(a=10)"

    get_button(ui.func_b).changed()
    assert str(ui.macro[-1]) == "ui.func_b(b=0)"
    ui.b = 10
    get_button(ui.func_b).changed()
    assert str(ui.macro[-1]) == "ui.func_b(b=10)"


def test_bind_at_same_level():
    @magicclass
    class A:
        @magicclass
        class B:
            a = vfield(5)

            def f2(self, a: Bound[a]):
                self.new_attr = a

    ui = A()
    get_button(ui.B.f2).changed()
    assert ui.B.new_attr == 5

def test_bind_at_same_level_external():
    @magicclass
    class B:
        a = vfield(5)

        def f2(self, a: Bound[a]):
            self.new_attr = a
    @magicclass
    class A:
        b = field(B)

    ui = A()
    get_button(ui.b.f2).changed()
    assert ui.b.new_attr == 5


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

        def func(self, x: Annotated[int, {"bind": b.x}]):
            self._a = x

    ui = A()
    assert ui._a == -1
    ui.b.x.value = 10
    assert ui._a == 1
    ui["func"].changed()
    assert ui._a == 10

def test_wrapped_with_external_field():
    @magicclass
    class B:
        @magicmenu
        class C:
            x = abstractapi()
        x = abstractapi(location=C)
        y = abstractapi()

    @magicclass
    class A:
        _x = -1
        _y = -1
        b = B
        def _get_value(self, *_):
            return 10

        @set_design(location=b)
        def x(self, v: Annotated[int, {"bind": _get_value}]):
            self._x = v

        @set_design(location=b)
        def y(self, v: Annotated[int, {"bind": _get_value}]):
            self._y = v

    ui = A()
    btn_x = get_button(ui.x)
    assert ui._x == -1
    btn_x.changed()
    assert ui._x == 10

    btn_y = get_button(ui.y)
    assert ui._y == -1
    btn_y.changed()
    assert ui._y == 10

def test_wrapped_with_external_field_via_field():
    @magicclass
    class B:
        @magicmenu
        class C:
            x = abstractapi()
        x = abstractapi(location=C)
        y = abstractapi()

    @magicclass
    class A:
        _x = -1
        _y = -1
        b = field(B)
        def _get_value(self, *_):
            return 10

        @set_design(location=b)
        def x(self, v: Annotated[int, {"bind": _get_value}]):
            self._x = v

        @set_design(location=b)
        def y(self, v: Annotated[int, {"bind": _get_value}]):
            self._y = v

    ui = A()
    btn_x = get_button(ui.x)
    assert ui._x == -1
    btn_x.changed()
    assert ui._x == 10

    btn_y = get_button(ui.y)
    assert ui._y == -1
    btn_y.changed()
    assert ui._y == 10

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

def test_bind_with_string():
    @magicclass
    class A:
        _out = None
        def f(self, x0: Bound["x"], y0: Bound["_get"]):
            self._out = (x0, y0)
        x = field(3)

        def _get(self, w=None):
            return 0

        def g(self, x0: Bound["B.bx"], y0: Bound["B._b_get"]):
            self._out = (x0, y0)

        @magicclass
        class B:
            bx = field(4)
            def _b_get(self, w=None):
                return 1

    ui = A()
    ui["f"].changed()
    assert ui._out == (3, 0)
    ui["g"].changed()
    assert ui._out == (4, 1)
