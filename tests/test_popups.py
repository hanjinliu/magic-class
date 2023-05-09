from magicclass import magicclass, PopUpMode
import pytest

from magicclass._gui.mgui_ext import PushButtonPlus

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

@pytest.mark.parametrize("popup_mode", PopUpMode._member_names_)
def test_all_works(popup_mode):
    if popup_mode == "dock":
        ui = _make_class(popup_mode, "mainwindow")()
    elif popup_mode == "dialog":
        # TODO: how to test dialog?
        return
    elif popup_mode == "parentsub":
        ui = _make_class(popup_mode, "subwindows")()
    else:
        ui = _make_class(popup_mode)()
    ui.show(run=False)
    for btn in [ui["a1"], ui["b1"], ui.B["b2"]]:
        btn: PushButtonPlus
        btn.changed()
        assert btn.mgui.visible
        btn.mgui.call_button.changed()
        assert not btn.mgui.visible
        btn.changed()
        assert btn.mgui.visible
        btn.mgui.close()

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
    ui["a2"].mgui.close()
    ui["a5"].mgui.close()


def test_last():
    ui = _make_class_2(PopUpMode.last)()
    l = len(ui)

    ui["a2"].changed()
    assert len(ui) == l + 1
    assert ui[-1] is ui["a2"].mgui

    ui["a5"].changed()
    assert len(ui) == l + 2
    assert ui[-1] is ui["a5"].mgui
    ui["a2"].mgui.close()
    ui["a5"].mgui.close()
