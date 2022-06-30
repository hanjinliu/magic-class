from magicclass import magicclass, field
from magicclass.types import Bound, Choices

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
        def f(self, x: Bound[B.f]):
            x.as_integer_ratio()
            self.out = x

        def g(self, x: Bound[B._get_value]):
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
        def f(self, x: Bound[b.f]):
            x.as_integer_ratio()
            self.out = x

        def g(self, x: Bound[b._get_value]):
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
        def f(self, x: Bound[_b.f]):
            x.as_integer_ratio()
            self.out = x

        def g(self, x: Bound[_b._get_value]):
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
        def run(self, x: Bound[_c.f]):
            x.as_integer_ratio()
            self.out = x

    ui = A()
    ui["run"].changed()
    assert ui.out == 2

def test_field():
    @magicclass
    class C:
        def _get_ints(self, w=None):
            return [1, 2, 4]

        f = field(Choices[_get_ints])

    @magicclass
    class A:
        _c = C
        out = None

        def f(self, x: Bound[_c.f]):
            x.as_integer_ratio()
            self.out = x

    ui = A()
    assert ui._c.f.choices == (1, 2, 4)
    ui["f"].changed()
    assert ui.out == 1
