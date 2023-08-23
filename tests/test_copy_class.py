from typing_extensions import Annotated
from unittest.mock import MagicMock
from magicclass import magicclass, field, MagicTemplate, abstractapi
from magicclass.types import OneOf

@magicclass
class B:
    f = field(2)
    def _get_value(self, w=None) -> str:
        return str(self.f.value)

def test_getter_of_same_name():
    @magicclass
    class A:
        B = B
        out = None
        def f(self, x: Annotated[int, {"bind": B.f}]):
            x.as_integer_ratio()
            self.out = x

        def g(self, x: Annotated[int, {"bind": B._get_value}]):
            x.capitalize()
            self.out = x

    ui = A()
    ui["f"].changed()
    assert ui.out == 2
    ui["g"].changed()
    assert ui.out == "2"


def test_getter_of_different_name():
    @magicclass
    class A:
        b = B
        out = None
        def f(self, x: Annotated[int, {"bind": b.f}]):
            x.as_integer_ratio()
            self.out = x

        def g(self, x: Annotated[str, {"bind": b._get_value}]):
            x.capitalize()
            self.out = x

    ui = A()
    ui["f"].changed()
    assert ui.out == 2
    ui["g"].changed()
    assert ui.out == "2"

def test_getter_of_private_name():
    @magicclass
    class A:
        _b = B
        out = None
        def f(self, x: Annotated[int, {"bind": _b.f}]):
            x.as_integer_ratio()
            self.out = x

        def g(self, x: Annotated[str, {"bind": _b._get_value}]):
            x.capitalize()
            self.out = x

    ui = A()
    ui["f"].changed()
    assert ui.out == 2
    ui["g"].changed()
    assert ui.out == "2"



def test_getter_and_wraps():
    @magicclass
    class C:
        f = field(2)
        def _get_value(self, w=None) -> str:
            return str(self.f.value)

        def run(self): ...

    @magicclass
    class A:
        _c = C
        out = None
        @_c.wraps
        def run(self, x: Annotated[int, {"bind": _c.f}]):
            x.as_integer_ratio()
            self.out = x

    ui = A()
    ui["run"].changed()
    assert ui.out == 2

def test_field():
    @magicclass
    class C:
        _value = None
        def _get_ints(self, w=None):
            return [1, 2, 4]

        f = field(OneOf[_get_ints])

        @f.connect
        def _on_change(self):
            self._value = self.f.value

    @magicclass
    class A:
        _c = C
        out = None

        def f(self, x: Annotated[int, {"bind": _c.f}]):
            x.as_integer_ratio()
            self.out = x

    ui = A()
    assert ui._c.f.choices == (1, 2, 4)
    ui["f"].changed()
    assert ui.out == 1

    # check value-changed event
    ui._c.f.value = 2
    assert ui._c._value == 2

def test_reuse_class():
    mock = MagicMock()

    @magicclass
    class Parent(MagicTemplate):
        top = field(int)

        @top.connect
        def _top_changed(self, v) -> None:
            mock(self, v)

        bottom = abstractapi()

    @magicclass
    class A(MagicTemplate):
        p = Parent
        @p.wraps
        def bottom(self):
            self.p.top.value = 100

    @magicclass
    class B(MagicTemplate):
        p = Parent
        @p.wraps
        def bottom(self):
            self.p.top.value = 200

    a = A()
    b = B()

    a.p.top.value = 1
    mock.assert_called_once_with(a.p, 1)
    assert b.p.top.value == 0
    a["bottom"].changed()
    assert a.p.top.value == 100
    assert b.p.top.value == 0
    b["bottom"].changed()
    assert a.p.top.value == 100
    assert b.p.top.value == 200
