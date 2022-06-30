from magicclass import magicclass, field
from magicclass.types import Bound

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

        def g(self, x: Bound[B._get_value]):
            x.capitalize()
            self.out = x

    ui = A()
    ui["f"].changed()
    assert ui.out == 2
    ui["g"].changed()
    assert ui.out == "2"
