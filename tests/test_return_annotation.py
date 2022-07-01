from magicclass import magicclass, get_function_gui
from magicgui import register_type
from unittest.mock import MagicMock

mock = MagicMock()

register_type(int, return_callback=mock)
register_type(str, return_callback=mock)

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
    assert str(ui.macro[1]) == "ui['f'](x=0)"
    assert str(ui.macro[2]) == "ui['g'](s='s')"
