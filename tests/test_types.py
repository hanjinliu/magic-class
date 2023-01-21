from typing_extensions import Annotated
from magicclass import magicclass, set_options, get_function_gui
from magicclass.types import Optional, Union, Stored
from magicclass import widgets

def test_basics():
    @magicclass
    class A:
        def f(self, x: Optional[int]):
            pass
    ui = A()
    ui["f"].changed()
    opt = get_function_gui(ui, "f")[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.value is None

def test_set_options():
    @magicclass
    class A:
        @set_options(x={"text": "x-text", "options": {"min": -1}})
        def f(self, x: Optional[int] = 0):
            x.as_integer_ratio()

    ui = A()
    ui["f"].changed()
    opt = get_function_gui(ui, "f")[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.text == "x-text"
    assert opt[1].visible
    assert opt[1].min == -1

def test_optional_with_annotated():
    T = Annotated[Optional[int], {"text": "x-text", "options": {"min": -1}}]

    @magicclass
    class A:
        def f(self, x: T = None):
            x.as_integer_ratio()

    ui = A()
    ui["f"].changed()
    opt = get_function_gui(ui, "f")[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.text == "x-text"
    assert not opt[1].visible
    assert opt[1].min == -1

def test_union():
    @magicclass
    class A:
        def f(self, x: Union[int, str]):
            pass

    ui = A()
    wdt = get_function_gui(ui, "f")[0]
    assert wdt.widget_type == "UnionWidget"
    assert wdt[0].widget_type == "SpinBox"
    assert wdt[1].widget_type == "LineEdit"

def test_union_with_default():
    @magicclass
    class A:
        def f(self, x: Union[int, str] = "a"):
            pass

    ui = A()
    wdt = get_function_gui(ui, "f")[0]
    assert wdt.widget_type == "UnionWidget"
    assert wdt[0].widget_type == "SpinBox"
    assert wdt[1].widget_type == "LineEdit"
    assert wdt.value == "a"
    assert wdt.current_index == 1

def test_union_with_set_option():
    @magicclass
    class A:
        @set_options(x={"options": [{"max": 4}, {"max": 5.0}]})
        def f(self, x: Union[int, float]):
            pass

    ui = A()
    wdt = get_function_gui(ui, "f")[0]
    assert wdt.widget_type == "UnionWidget"
    assert wdt[0].widget_type == "SpinBox"
    assert wdt[1].widget_type == "FloatSpinBox"
    assert wdt[0].max == 4
    assert wdt[1].max == 5.0

def test_stored_type():
    class X:
        def __init__(self, val):
            self.val = val

        def __eq__(self, o: object) -> bool:
            if type(o) is not X:
                return False
            return self.val == o.val

        def __repr__(self):
            return f"X({self.val!r})"

    @magicclass
    class A:
        def provide(self, x: int) -> Stored[X]:
            return X(x)

        def receive(self, s: Stored[X]):
            pass

    ui = A()
    provide = get_function_gui(ui, "provide")
    receive = get_function_gui(ui, "receive")
    provide(2)
    assert receive.s.choices == (X(2),)
    provide(2)
    assert receive.s.choices == (X(2), X(2))
    provide(5)
    # NOTE: ComboBox sometimes does not keep the order...
    # assert receive.s.choices == (X(5), X(2), X(2))
    receive()
    lefts = [str(ui.macro[i]).split("=")[0].strip() for i in (1, 2, 3)]
    assert lefts[0] != lefts[1] and lefts[1] != lefts[2]
    assert str(ui.macro[4]) == f"ui.receive(s={lefts[-1]})"
    assert X(3) == ui.provide(3), "provide did not work programmatically"

def test_stored_last_type():
    class X:
        def __init__(self, val):
            self.val = val

        def __eq__(self, o: object) -> bool:
            if type(o) is not X:
                return False
            return self.val == o.val

        def __repr__(self):
            return f"X({self.val!r})"

    @magicclass
    class A:
        def provide(self, x: int) -> Stored[X]:
            return X(x)

        def receive(self, s: Stored.Last[X]):
            pass


    ui = A()
    provide = get_function_gui(ui, "provide")
    receive = get_function_gui(ui, "receive")
    provide(2)
    assert receive.s.value == X(2)
    provide(3)
    assert receive.s.value == X(3)
