from magicclass import magicclass, set_options, field, vfield, get_function_gui
from magicgui.widgets import Select
import pytest

@pytest.mark.parametrize("widget_type", ["ComboBox", "RadioButtons", "Select"])
def test_get_choices(widget_type):
    @magicclass
    class A:
        def __init__(self):
            self._a = [0, 1, 2]

        def _get_choices(self, w=None):
            return self._a

        @set_options(x={"widget_type": widget_type, "choices": _get_choices})
        def func(self, x):
            pass

    ui = A()
    fgui = get_function_gui(ui.func)
    ui["func"].changed()
    assert fgui.x.widget_type == widget_type
    assert fgui.x.choices == (0, 1, 2)
    ui._a = [3, 4]
    ui.reset_choices()
    assert fgui.x.choices == (3, 4)
    fgui.close()

@pytest.mark.parametrize("widget_type", ["ComboBox", "RadioButtons", "Select"])
def test_nesting(widget_type):
    @magicclass
    class A:
        @magicclass
        class B:
            def __init__(self):
                self._a = [0, 1, 2]

            def _get_choices(self, w=None):
                return self._a

            @set_options(x={"widget_type": widget_type, "choices": _get_choices})
            def func(self, x):
                pass

        @set_options(x={"widget_type": widget_type, "choices": B._get_choices})
        def func(self, x):
            pass

    ui = A()
    ui["func"].changed()
    ui.B["func"].changed()
    fgui0 = get_function_gui(ui.func)
    fgui1 = get_function_gui(ui.B.func)
    assert fgui0.x.widget_type == widget_type
    assert fgui0.x.choices == (0, 1, 2)
    assert fgui1.x.widget_type == widget_type
    assert fgui1.x.choices == (0, 1, 2)
    ui.B._a = [3, 4]
    ui.reset_choices()
    assert fgui0.x.choices == (3, 4)
    assert fgui1.x.choices == (3, 4)
    fgui0.close()
    fgui1.close()

def test_wraps():
    @magicclass
    class A:
        def __init__(self):
            self._a = [0, 1, 2]
        @magicclass
        class B:
            def func(self): ...

        def _get_choices(self, w=None):
            return self._a

        @B.wraps
        @set_options(x={"widget_type": "ComboBox", "choices": _get_choices})
        def func(self, x):
            pass

    ui = A()
    ui["func"].changed()
    fgui = get_function_gui(ui.func)
    assert fgui.x.widget_type == "ComboBox"
    assert fgui.x.choices == (0, 1, 2)
    ui._a = [3, 4]
    ui.reset_choices()
    assert fgui.x.choices == (3, 4)
    fgui.close()

def test_field():
    @magicclass
    class A:
        def __init__(self):
            self._a = [0, 1, 2]

        def _get_choices(self, w=None):
            return self._a

        a = field(Select, options={"choices": _get_choices})
        b = vfield(options={"choices": _get_choices})
        c = field(Select, options={"choices": [0, 1]})

    ui = A()
    assert ui[0].choices == (0, 1, 2)
    assert ui[1].choices == (0, 1, 2)
    assert ui[2].choices == (0, 1)
    ui._a = [3]
    ui.reset_choices()
    assert ui[0].choices == (3,)
    assert ui[1].choices == (3,)
    assert ui[2].choices == (0, 1)

def test_multi_gui():
    @magicclass
    class A:
        def _get_choices(self, w=None):
            return [id(self), id(w)]
        choices = field(widget_type="Select", options={"choices": _get_choices})
        @set_options(c={"choices": _get_choices})
        def f(self, c):
            pass

    a0 = A()
    a1 = A()

    assert a0.choices.choices[0] == id(a0)
    assert a1.choices.choices[0] == id(a1)
    assert a0.choices.choices[1] != a1.choices.choices[1]

    fgui0 = get_function_gui(a0.f)
    fgui1 = get_function_gui(a1.f)

    assert fgui0.c.choices[0] == id(a0)
    assert fgui1.c.choices[0] == id(a1)
    assert fgui0.c.choices[1] != fgui1.c.choices[1]

def test_choices_with_string():
    @magicclass
    class A:
        choices = field(widget_type="Select", options={"choices": "_get_choices"})
        @set_options(c={"choices": "_get_choices"})
        def f(self, c):
            pass
        def _get_choices(self, w=None):
            return [id(self), id(w)]

    ui = A()
    assert ui.choices.choices[0] == id(ui)
    fgui = get_function_gui(ui.f)
    assert fgui.c.choices[0] == id(ui)

    @magicclass
    class A:
        choices = field(widget_type="Select", options={"choices": "B._get_choices"})
        @set_options(c={"choices": "B._get_choices"})
        def f(self, c):
            pass

        @magicclass
        class B:
            def _get_choices(self, w=None):
                return [1, 2]

    ui = A()
    assert ui.choices.choices[0] == 1
    fgui = get_function_gui(ui.f)
    assert fgui.c.choices[0] == 1

def test_choices_type():
    from magicclass.types import OneOf

    @magicclass
    class A:
        @magicclass
        class B:
            def _get_choices(self, w=None):
                return [1, 2]

            def _get_choices_with_name(self, w=None) -> list[tuple[str, int]]:
                return [("a", 1), ("b", 2)]

        def f(self, c: OneOf[B._get_choices], d: OneOf[B._get_choices_with_name]):
            c.bit_length()
            d.bit_length()

        def g(self, c: OneOf[("a", 0), ("b", 1)]):
            c.bit_length()

    ui = A()
    cbox = get_function_gui(ui.f).c
    assert cbox.choices == (1, 2)
    cbox = get_function_gui(ui.g).c
    assert cbox.choices == (0, 1)

def test_someof_type():
    from magicclass.types import SomeOf

    @magicclass
    class A:
        @magicclass
        class B:
            def _get_choices(self, w=None):
                return [1, 2]

            def _get_choices_with_name(self, w=None) -> list[tuple[str, int]]:
                return [("a", 1), ("b", 2)]

        def f(self, c: SomeOf[B._get_choices], d: SomeOf[B._get_choices_with_name]):
            c[0].bit_length()
            d[0].bit_length()

        def g(self, c: SomeOf[("a", 0), ("b", 1)]):
            c[0].bit_length()

    ui = A()
    cbox = get_function_gui(ui.f).c
    assert cbox.choices == (1, 2)
    cbox = get_function_gui(ui.g).c
    assert cbox.choices == (0, 1)

def test_slice_choices():
    from magicclass.types import OneOf

    @magicclass
    class A:
        def f(self, x: OneOf[3:6], y: OneOf[0.1:0.3:0.05]):
            x.bit_length()
            y.is_integer()

    ui = A()
    fgui = get_function_gui(ui.f)
    assert fgui.x.choices == (3, 4, 5)
    assert fgui.y.choices == (0.1, 0.15, 0.2, 0.25)
