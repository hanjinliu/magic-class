from magicclass import magicclass, MagicTemplate
from magicgui import magicgui, widgets

def test_magicgui():
    @magicclass
    class A(MagicTemplate):
        @magicgui
        def f(self, a: int, b: str = "x"):
            self.a = a

    ui = A()
    ui.show(run=False)
    assert type(ui[0]) is widgets.FunctionGui
    assert ui[0].a.value == 0
    assert ui[0].b.value == "x"
    assert ui[0].visible

    # macro should be recorded after called
    ui[0].a.value = 10
    assert len(ui.macro) == 1
    ui[0]()
    assert len(ui.macro) == 2
    assert str(ui.macro[-1]) == "ui.f(a=10, b='x')"
    assert hasattr(ui, "a")
    ui[0].a.value = 20
    ui[0]()
    assert len(ui.macro) == 3
    assert str(ui.macro[-1]) == "ui.f(a=20, b='x')"
    assert str(ui.macro[-2]) == "ui.f(a=10, b='x')"
    ui.close()

def test_autocall_macro():
    """Auto-called macro should be recorded once."""
    @magicclass
    class A(MagicTemplate):
        @magicgui(auto_call=True)
        def f(self, a: int, b: str = "x"):
            self.a = a

    ui = A()
    ui[0].a.value = 1
    assert str(ui.macro[-1]) == "ui.f(a=1, b='x')"
    ui[0].a.value = 2
    assert str(ui.macro[-1]) == "ui.f(a=2, b='x')"

def test_wraps():
    @magicclass
    class A(MagicTemplate):
        @magicclass
        class B:
            def f1(self): ...
            def f2(self): ...
            def f3(self): ...

        @B.wraps
        @magicgui
        def f2(self, a: int, b: str = "x"):
            self.a = a

    ui = A()
    ui.show(run=False)
    assert len(ui.B) == 3
    assert type(ui.B[1]) is widgets.FunctionGui
    assert ui.B[1].a.value == 0
    assert ui.B[1].b.value == "x"
    assert ui.B[1].visible

    # macro should be recorded after called
    ui.B[1].a.value = 10
    assert len(ui.macro) == 1
    ui.B[1]()
    assert len(ui.macro) == 2
    assert str(ui.macro[-1]) == "ui.f2(a=10, b='x')"
    assert hasattr(ui, "a")
    ui.B[1].a.value = 20
    ui.B[1]()
    assert len(ui.macro) == 3
    assert str(ui.macro[-1]) == "ui.f2(a=20, b='x')"
    assert str(ui.macro[-2]) == "ui.f2(a=10, b='x')"
    ui.close()

def test_multi_gui():
    @magicclass
    class A:
        @magicgui
        def f(self, x: int):
            return id(self)

        @magicgui
        def g(self, x: float):
            return -id(self)

    ui0 = A()
    ui1 = A()
    ui0.show(run=False)
    ui1.show(run=False)
    assert ui0["f"] is not ui1["f"]
    assert ui0["g"] is not ui1["g"]
    assert ui0["f"] is not ui0["g"]
    assert ui0["f"](x=0) == -ui0["g"](x=0)
    assert ui1["f"](x=0) == -ui1["g"](x=0)
    assert ui0["f"](x=0) == id(ui0)
    assert ui1["f"](x=0) == id(ui1)
    assert ui0["f"].visible
    assert ui0["g"].visible
    assert ui1["f"].visible
    assert ui1["g"].visible
    ui0.close()
    ui1.close()
