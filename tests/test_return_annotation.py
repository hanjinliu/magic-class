from magicclass import magicclass, get_function_gui, set_options
from magicgui import register_type
from unittest.mock import MagicMock

mock = MagicMock()

def _dummy(*args, **kwargs):
    pass

register_type(int, return_callback=mock)
register_type(str, return_callback=mock)
register_type(float, return_callback=_dummy)

def test_return_annotation():
    @magicclass
    class A:
        def f(self, x: int) -> int:
            return x + 1

        def g(self, s: str = "s") -> str:
            return s + "-0"

    ui = A()
    fgui_f = get_function_gui(ui, "f")
    fgui_g = get_function_gui(ui, "g")

    assert len(ui.macro) == 1
    mock.assert_not_called()
    fgui_f.call_button.changed()
    mock.assert_called_with(fgui_f, 1, int)
    fgui_g.call_button.changed()
    mock.assert_called_with(fgui_g, "s-0", str)
    assert len(ui.macro) == 3
    assert str(ui.macro[1]) == "ui._call_with_return_callback('f', x=0)"
    assert str(ui.macro[2]) == "ui._call_with_return_callback('g', s='s')"

def test_return_annotation_auto_call():
    @magicclass
    class A:
        @set_options(auto_call=True)
        def f(self, x: int = 1) -> float:
            return float(x)

        def g(self):
            pass

    ui = A()
    fgui_f = get_function_gui(ui, "f")

    assert len(ui.macro) == 1
    fgui_f.x.value = 2
    assert len(ui.macro) == 2
    assert str(ui.macro[-1]) == "ui._call_with_return_callback('f', x=2)"
    fgui_f.x.value = 3
    assert len(ui.macro) == 2
    assert str(ui.macro[-1]) == "ui._call_with_return_callback('f', x=3)"
    ui.g()
    fgui_f.x.value = 2
    assert len(ui.macro) == 4
    assert str(ui.macro[-1]) == "ui._call_with_return_callback('f', x=2)"
