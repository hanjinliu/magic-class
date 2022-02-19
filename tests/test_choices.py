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

        @set_options(x={"widget_type": widget_type, "choices": B._get_choices})
        def func(self, x):
            pass

    ui = A()
    ui["func"].changed()
    assert ui["func"].mgui.x.widget_type == widget_type
    assert ui["func"].mgui.x.choices == (0, 1, 2)
    ui.B._a = [3, 4]
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
        b = vfield(ComboBox, options={"choices": _get_choices})
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
