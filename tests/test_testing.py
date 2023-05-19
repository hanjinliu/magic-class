from typing import Annotated
from magicclass import magicclass, abstractapi, vfield
from magicclass.types import Bound
from magicclass.testing import check_function_gui_buildable, check_tooltip
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
        """
        x = vfield(1)
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
