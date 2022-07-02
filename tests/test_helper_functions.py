from magicclass import magicclass, magicmenu, field, vfield, get_function_gui

def test_get_function_gui():
    @magicclass
    class A:
        @magicmenu
        class B:
            def b(self): ...
        def f(self): ...

    ui = A()
    f = get_function_gui(ui, "f")
    b = get_function_gui(ui.B, "b")
    assert f is ui["f"].mgui
    assert b is ui.B["b"].mgui


def test_update_widget_state():
    from magicclass import update_widget_state

    @magicclass
    class A:
        x = field(0)
        y = vfield("s")
        def f(self, x: int, y: float = 1.0):
            pass

    ui = A()
    fgui = get_function_gui(ui, "f")
    assert ui.x.value == 0
    assert ui.y == "s"
    assert fgui.asdict() == {"x": 0, "y": 1.0}

    macro = "\n".join([
        "ui.x.value = 10",
        "ui.y = 'new'",
        "ui.f(x=20, y=5.0)",
    ])

    update_widget_state(ui, macro)
    assert ui.x.value == 10
    assert ui.y == "new"
    assert fgui.asdict() == {"x": 20, "y": 5.0}
