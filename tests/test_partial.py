from magicclass import magicclass, get_function_gui
from magicclass.utils import partial_gui
from unittest.mock import MagicMock

def test_partial_gui():
    mock = MagicMock()
    @magicclass
    class A:
        def f(self, i: int):
            mock(i)

    ui = A()
    ui.append(partial_gui(ui.f, i=1, function_name="f(1)"))
    mock.assert_not_called()
    get_function_gui(ui, "f(1)")()
    mock.assert_called_once_with(1)
    assert str(ui.macro[-1]) == "ui.f(i=1)"
    ui.append(partial_gui(ui.f, i=2, function_name="f(2)"))
    get_function_gui(ui, "f(2)")()
    mock.assert_called_once_with(2)
    assert str(ui.macro[-1]) == "ui.f(i=2)"
