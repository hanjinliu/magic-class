from magicclass import magicclass, set_options, field, vfield
from magicgui.widgets import Select, ComboBox
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
    ui["func"].changed()
    assert ui["func"].mgui.x.widget_type == widget_type
    assert ui["func"].mgui.x.choices == (0, 1, 2)
    ui._a = [3, 4]
    ui.reset_choices()
    assert ui["func"].mgui.x.choices == (3, 4)

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
    assert ui["func"].mgui.x.widget_type == widget_type
    assert ui["func"].mgui.x.choices == (0, 1, 2)
    assert ui.B["func"].mgui.x.widget_type == widget_type
    assert ui.B["func"].mgui.x.choices == (0, 1, 2)
    ui.B._a = [3, 4]
    ui.reset_choices()
    assert ui["func"].mgui.x.choices == (3, 4)
    assert ui.B["func"].mgui.x.choices == (3, 4)


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
    assert ui["func"].mgui.x.widget_type == "ComboBox"
    assert ui["func"].mgui.x.choices == (0, 1, 2)
    ui._a = [3, 4]
    ui.reset_choices()
    assert ui["func"].mgui.x.choices == (3, 4)

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

    a0["f"].changed()
    a1["f"].changed()

    assert a0["f"].mgui.c.choices[0] == id(a0)
    assert a1["f"].mgui.c.choices[0] == id(a1)
    assert a0["f"].mgui.c.choices[1] != a1["f"].mgui.c.choices[1]
