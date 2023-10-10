from magicclass import (
    magicclass, magicmenu, magictoolbar, field, vfield, set_design,
    abstractapi, get_button
)
from magicclass.types import Bound
from unittest.mock import MagicMock
import pytest
from qtpy import QT6

def test_single_wraps():
    @magicclass
    class A:
        a = vfield(int)
        @magicclass
        class B:
            def f1(self): ...
            def f2(self): ...
            def f3(self): ...
        @B.wraps
        def f2(self, a: Bound[a]):
            self.new_attr = a

    ui = A()

    # assert the widget order is conserved
    assert ui.B[0].name == "f1"
    assert ui.B[1].name == "f2"
    assert ui.B[2].name == "f3"

    mock = MagicMock()
    ui.changed.connect(mock)
    ui.B["f2"].changed()
    mock.assert_called()
    assert hasattr(ui, "new_attr")

def test_double_wrap():
    @magicclass
    class A:
        a = vfield(int)
        @magicclass
        class B:
            @magicmenu
            class C:
                def f1(self): ...
                def f2(self): ...
                def f3(self): ...
        @B.C.wraps
        def f2(self, a: Bound[a]):
            self.new_attr = a

    ui = A()

    # assert the widget order is conserved
    assert ui.B.C[0].name == "f1"
    assert ui.B.C[1].name == "f2"
    assert ui.B.C[2].name == "f3"

    ui.B.C["f2"].changed()
    assert hasattr(ui, "new_attr")

def test_copy():
    @magicclass
    class A:
        a = vfield(int)
        @magicclass
        class B:
            @magicmenu
            class C:
                def f1(self): ...
                @set_design(text="C.f2")
                def f2(self): ...
                def f3(self): ...
            @set_design(text="B.f2")
            def f2(self): ...
        @B.wraps
        @B.C.wraps
        def f2(self, a: Bound[a]):
            self.new_attr = a

    ui = A()
    assert not ui["f2"].visible
    assert ui.B["f2"].text == "B.f2"
    assert ui.B.C["f2"].text == "C.f2"

    ui.B["f2"].changed()
    assert ui.new_attr == 0
    ui.a = 1
    ui.B.C["f2"].changed()
    assert ui.new_attr == 1

def test_field_wraps():
    @magicclass
    class B:
        def f(self): ...

    @magicclass
    class A:
        b = field(B)
        a = vfield(int)

        @b.wraps
        def f(self, a: Bound[a]):
            self.new_attr = a

    ui = A()
    assert not ui["f"].visible
    ui.b["f"].changed()
    assert ui.new_attr == 0

def test_wraps_no_predefinition():
    if QT6:
        pytest.skip("insertWidget crashes in QT6. Skip for now.")
    @magicclass
    class A:
        a = vfield(int)
        @magicclass
        class B:
            @magicmenu
            class C:
                pass
            @magicclass
            class D:
                pass
            @magictoolbar
            class E:
                pass

        @B.wraps
        def fb2(self, a: Bound[a]):
            pass

        @B.wraps
        def fb1(self, a: Bound[a]):
            pass

        @B.C.wraps
        def fc2(self, a: Bound[a]):
            pass

        @B.C.wraps
        def fc1(self, a: Bound[a]):
            pass

        @B.C.wraps
        @B.D.wraps
        @B.E.wraps
        def any_func(self, a: Bound[a]):
            pass

    ui = A()

    # assert the widget order is conserved
    assert ui.B[1].name == "fb2"
    assert ui.B[2].name == "fb1"
    assert ui.B.C[0].name == "fc2"
    assert ui.B.C[1].name == "fc1"
    assert ui.B.C[2].name == "any_func"
    assert ui.B.D[0].name == "any_func"
    assert ui.B.E[0].name == "any_func"

    ui.B["fb1"].changed()
    ui.B["fb2"].changed()
    ui.B.C["fc1"].changed()
    ui.B.C["fc2"].changed()
    ui.B.C["any_func"].changed()
    ui.B.D["any_func"].changed()
    ui.B.E["any_func"].changed()

def test_wrapped_field():
    if QT6:
        pytest.skip("insertWidget crashes in QT6. Skip for now.")
    @magicclass
    class A:
        @magicclass
        class B:
            a = abstractapi()
            b = abstractapi()
        a = field(int, location=B)
        b = field(str, location=B)

    ui = A()
    assert ui.B[0].widget_type == "SpinBox"
    assert ui.B[1].widget_type == "LineEdit"
    assert ui.a.widget_type == "SpinBox"
    assert ui.b.widget_type == "LineEdit"

    ui.a.value = 2
    ui.b.value = "x"
    assert ui.B[0].value == 2
    assert ui.B[1].value == "x"
    assert ui.a.value == 2
    assert ui.b.value == "x"
    assert str(ui.macro[1]) == "ui.a.value = 2"
    assert str(ui.macro[2]) == "ui.b.value = 'x'"


def test_wrapped_vfield():
    if QT6:
        pytest.skip("insertWidget crashes in QT6. Skip for now.")
    @magicclass
    class A:
        @magicclass
        class B:
            a = abstractapi()
            b = abstractapi()
        a = vfield(int, location=B)
        b = vfield(str, location=B)

    ui = A()
    assert ui.B[0].widget_type == "SpinBox"
    assert ui.B[1].widget_type == "LineEdit"
    assert ui["a"].widget_type == "SpinBox"
    assert ui["b"].widget_type == "LineEdit"

    ui.a = 2
    ui.b = "x"
    assert ui.B[0].value == 2
    assert ui.B[1].value == "x"
    assert ui.a == 2
    assert ui.b == "x"
    assert str(ui.macro[1]) == "ui.a = 2"
    assert str(ui.macro[2]) == "ui.b = 'x'"

def test_get_button():
    @magicclass
    class A:
        @magicclass
        class B:
            @magicmenu
            class C:
                def f2(self): ...
            def f1(self): ...
        @B.wraps
        def f1(self): ...
        @B.C.wraps
        def f2(self): ...

    ui = A()
    assert get_button(ui.f1) is ui.B["f1"]
    assert get_button(ui.f2) is ui.B.C["f2"]
