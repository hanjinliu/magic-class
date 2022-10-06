from magicclass import magicclass
from magicclass.utils import partial
from unittest.mock import MagicMock
import pytest

def test_partial_call():
    def f(i: int, j: int):
        return i + j

    pf0 = partial(f, 1)

    assert pf0(2) == 3
    assert pf0(j=2) == 3
    with pytest.raises(TypeError):
        pf0(i=3)
    with pytest.raises(TypeError):
        pf0()

    pf1 = partial(f, j=10)

    assert pf1(2) == 12
    assert pf1(i=4) == 14
    with pytest.raises(TypeError):
        pf1(j=4)
    with pytest.raises(TypeError):
        pf1()

def test_partial_gui():
    mock = MagicMock()
    @magicclass
    class A:
        def f(self, i: int):
            mock(i)

    ui = A()
    ui.append(partial(ui.f, i=1, function_text="f(1)"))
    mock.assert_not_called()
    ui[-1].changed()
    mock.assert_called_once_with(1)
    assert str(ui.macro[-1]) == "ui.f(i=1)"
    ui.append(partial(ui.f, i=2, function_text="f(2)"))
    ui[-1].changed()
    mock.assert_called_with(2)
    assert str(ui.macro[-1]) == "ui.f(i=2)"
