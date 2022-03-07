from magicclass import magicclass, magicmenu, field, vfield, set_design
from magicclass.types import Bound
from unittest.mock import MagicMock

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
