from magicclass import magicclass
from magicclass.utils import partial_gui
from unittest.mock import MagicMock

def test_partial_gui():
    mock = MagicMock()
    @magicclass
    class A:
        def f(self, i: int):
            mock(i)

    ui = A()
    ui.append(partial_gui(ui.f, i=1, function_text="f(1)"))
    mock.assert_not_called()
    ui[-1].changed()
    ui[-1].mgui()
    mock.assert_called_once_with(1)
    assert str(ui.macro[-1]) == "ui.f(i=1)"
    ui.append(partial_gui(ui.f, i=2, function_text="f(2)"))
    ui[-1].changed()
    ui[-1].mgui()
    mock.assert_called_with(2)
    assert str(ui.macro[-1]) == "ui.f(i=2)"
