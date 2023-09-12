from typing_extensions import Annotated
from unittest.mock import MagicMock
from magicclass import magicclass, abstractapi, field, vfield, confirm, impl_preview
from magicclass.types import Bound
from magicclass.testing import (
    check_function_gui_buildable, check_tooltip, FunctionGuiTester, MockConfirmation
)
import pytest

def test_fgui():
    @magicclass
    class A:
        x = vfield(1)

        @magicclass
        class B:
            def f(self, i: int):
                ...
            bf = abstractapi()

        def g(self):
            ...
        @B.wraps
        def bf(self):
            ...

    ui = A()

    check_function_gui_buildable(ui)
    assert ui["g"].mgui is not None
    assert ui["bf"].mgui is not None
    assert ui.B["f"].mgui is not None

def test_not_buildable_due_to_typing():
    class Undef:
        """Undefined type"""

    @magicclass
    class A:
        def f(self, i: Undef):
            ...

    ui = A()

    with pytest.raises(AssertionError):
        check_function_gui_buildable(ui)

def test_not_buildable_due_to_bind_args():
    def _bind(a, b, c):
        return 0

    @magicclass
    class A:
        def f(self, i: Annotated[int, {"bind": _bind}]):
            ...

    ui = A()

    with pytest.raises(AssertionError):
        check_function_gui_buildable(ui)

def test_not_buildable_due_to_error_in_bind():
    def _bind(*_):
        raise ValueError

    @magicclass
    class A:
        def f(self, i: Annotated[int, {"bind": _bind}]):
            ...

    ui = A()

    with pytest.raises(AssertionError):
        check_function_gui_buildable(ui)

def test_not_buildable_due_to_choices():
    def _get_choices(a, b, c):
        return []

    @magicclass
    class A:
        def f(self, i: Annotated[int, {"choices": _get_choices}]):
            ...

    ui = A()

    with pytest.raises(AssertionError):
        check_function_gui_buildable(ui)

def test_not_buildable_due_to_error_in_choices():
    def _get_choices(*_):
        raise ValueError

    @magicclass
    class A:
        def f(self, i: Annotated[int, {"choices": _get_choices}]):
            ...

    ui = A()

    with pytest.raises(AssertionError):
        check_function_gui_buildable(ui)

def test_bound():
    @magicclass
    class A:
        def _get_value(self, *_):
            return 0

        def f(self, i: Bound[_get_value]):
            ...

        def g(self, i: Bound[_get_value] = None):
            ...

    ui = A()
    check_function_gui_buildable(ui)


def test_tooltip_check():

    @magicclass
    class A:
        """
        description

        Attributes
        ----------
        x : int
            description about x
        y : str
            description about y
        """
        x = vfield(1)
        y = field(str)

        def f(self, i: int):
            """
            description

            Parameters
            ----------
            i : int
                parameter.
            """
            ...

    ui = A()
    check_tooltip(ui)

def test_tooltip_check_fails_by_attribute():

    @magicclass
    class A:
        """
        description

        Attributes
        ----------
        y : int
            Does not exist.
        """
        x = vfield(1)

    ui = A()
    with pytest.raises(AssertionError):
        check_tooltip(ui)

def test_tooltip_check_fails_by_parameter_name():
    @magicclass
    class A:
        def f(self, i: int):
            """
            description

            Parameters
            ----------
            j : int
                parameter that does not exist.
            """
            ...

    ui = A()
    with pytest.raises(AssertionError):
        check_tooltip(ui)

def test_check_confirm():
    mock_conf = MockConfirmation()
    mock = MagicMock()

    @magicclass
    class A:
        @confirm(text="text", condition="x>3", callback=mock_conf)
        def f(self, x: int):
            mock(x)

    ui = A()
    testf = FunctionGuiTester(ui.f)
    mock.assert_not_called()
    testf.call(1)
    mock.assert_called_once()
    mock.reset_mock()
    mock_conf.assert_not_called()
    assert testf.has_confirmation
    assert not testf.has_preview
    assert testf.confirm_count == 0
    mock.assert_not_called()
    testf.call(10)
    mock_conf.assert_not_called()
    assert testf.confirm_count == 1
    mock.assert_called_once()
    mock.reset_mock()

def test_check_preview():
    mock = MagicMock()
    hist = []

    @magicclass
    class A:
        def f(self, x: int):
            mock(x)

        @impl_preview(f)
        def _preview(self, x: int):
            hist.append(0)
            yield
            hist.append(1)

    ui = A()
    testf = FunctionGuiTester(ui.f)
    assert testf.has_preview
    assert not testf.has_confirmation
    assert hist == []
    mock.assert_not_called()
    testf.call(1)
    mock.assert_called_once()
    assert hist == []
    testf.click_preview()
    assert hist == [0]
    testf.click_preview()
    assert hist == [0, 1, 0]
    testf.click_preview()
    assert hist == [0, 1, 0, 1, 0]
    testf.call(2)
    assert hist == [0, 1, 0, 1, 0, 1]
    testf.click_preview()
    assert hist == [0, 1, 0, 1, 0, 1, 0]
    testf.click_preview()
    assert hist == [0, 1, 0, 1, 0, 1, 0, 1, 0]

def test_check_preview_autocall():

    mock = MagicMock()
    hist = []

    @magicclass
    class A:
        def f(self, x: int):
            mock(x)

        @impl_preview(f, auto_call=True)
        def _preview(self, x: int):
            hist.append(0)
            yield
            hist.append(1)

    ui = A()
    testf = FunctionGuiTester(ui.f)
    assert testf.has_preview
    assert not testf.has_confirmation
    testf.update_parameters(x=1)
    assert hist == []
    testf.click_preview()
    assert hist == [0]
    testf.update_parameters(x=2)
    assert hist == [0, 1, 0]
    testf.click_preview()
    assert hist == [0, 1, 0, 1]
    testf.update_parameters(x=4)
    assert hist == [0, 1, 0, 1]

def test_error_detectable():
    @magicclass
    class A:
        def f(self, raises=True):
            if raises:
                raise ValueError("error")

    ui = A()
    testf = FunctionGuiTester(ui.f)
    with pytest.raises(ValueError):
        testf.call()

def test_error_during_preview():
    @magicclass
    class A:
        def f(self, raises=True):
            pass

        @impl_preview(f)
        def _preview(self):
            raise ValueError("error")

    ui = A()
    testf = FunctionGuiTester(ui.f)
    with pytest.raises(ValueError):
        testf.click_preview()
