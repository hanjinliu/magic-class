from typing import Annotated
from magicclass import magicclass, abstractapi, vfield
from magicclass._gui._base import MagicGuiBuildError
from magicclass.testing import assert_function_gui_buildable
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

    assert_function_gui_buildable(ui)
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

    with pytest.raises(TypeError):
        assert_function_gui_buildable(ui)

def test_not_buildable_due_to_bind_args():
    def _bind(a, b, c):
        return 0

    @magicclass
    class A:
        def f(self, i: Annotated[int, {"bind": _bind}]):
            ...

    ui = A()

    with pytest.raises(TypeError):
        assert_function_gui_buildable(ui)

def test_not_buildable_due_to_error_in_bind():
    def _bind(*_):
        raise ValueError

    @magicclass
    class A:
        def f(self, i: Annotated[int, {"bind": _bind}]):
            ...

    ui = A()

    with pytest.raises(ValueError):
        assert_function_gui_buildable(ui)

def test_not_buildable_due_to_choices():
    def _get_choices(a, b, c):
        return []

    @magicclass
    class A:
        def f(self, i: Annotated[int, {"choices": _get_choices}]):
            ...

    ui = A()

    with pytest.raises(MagicGuiBuildError):
        assert_function_gui_buildable(ui)

def test_not_buildable_due_to_error_in_choices():
    def _get_choices(*_):
        raise ValueError

    @magicclass
    class A:
        def f(self, i: Annotated[int, {"choices": _get_choices}]):
            ...

    ui = A()

    with pytest.raises(MagicGuiBuildError):
        assert_function_gui_buildable(ui)
