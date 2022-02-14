from magicclass import magicclass, PopUpMode

def _make_class(mode: PopUpMode, widget_type="none"):
    @magicclass(popup_mode=mode, widget_type=widget_type)
    class A:
        @magicclass(popup_mode=mode)
        class B:
            def b1(self, a: int): ...
            def b2(self, a: int): ...

        def a1(self, a: int): ...

        @B.wraps
        def b1(self, a: int): ...

    return A

def test_all_works():
    for mode in PopUpMode._member_names_:
        if mode == "dock":
            ui = _make_class(mode, "mainwindow")()
        else:
            ui = _make_class(mode)()
        ui.show(run=False)
        ui[1].changed()
        ui.B[0].changed()
        ui.B[1].changed()
        ui.close()


def _make_class_2(mode: PopUpMode):
    @magicclass(popup_mode=mode)
    class A:
        @magicclass(popup_mode=mode)
        class B:
            def b1(self, a: int): ...
            def b2(self, a: int): ...
            def b3(self, a: int): ...
            def b4(self, a: int): ...
            def b5(self, a: int): ...
            def b6(self, a: int): ...

        def a1(self, a: int): ...
        def a2(self, a: int): ...
        def a3(self, a: int): ...
        def a4(self, a: int): ...
        def a5(self, a: int): ...
        def a6(self, a: int): ...

        @B.wraps
        def b3(self, a: int): ...

    return A

def test_first():
    ui = _make_class_2(PopUpMode.first)()
    l = len(ui)

    ui["a2"].changed()
    assert len(ui) == l + 1
    assert ui[0] is ui["a2"].mgui

    ui["a5"].changed()
    assert len(ui) == l + 2
    assert ui[0] is ui["a5"].mgui


def test_last():
    ui = _make_class_2(PopUpMode.last)()
    l = len(ui)

    ui["a2"].changed()
    assert len(ui) == l + 1
    assert ui[-1] is ui["a2"].mgui

    ui["a5"].changed()
    assert len(ui) == l + 2
    assert ui[-1] is ui["a5"].mgui
