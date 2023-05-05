from magicclass import magicclass, magicmenu, magictoolbar
from magicclass.types import WidgetType
import pytest
from qtpy import QT6

def _make_class(t: WidgetType):
    @magicclass(widget_type=t)
    class A:
        @magicmenu
        class Menu:
            pass

        @magictoolbar
        class Tool1:
            pass

        @magictoolbar
        class Tool2:
            pass

        @magicclass
        class B:
            def b1(self, a: int): ...
            def b2(self, a: int): ...

        def a1(self, a: int): ...

        @B.wraps
        def b1(self, a: int): ...

    return A

@pytest.mark.parametrize("wtype", WidgetType._member_names_)
def test_all_works(wtype):
    if QT6 and wtype in ("scrollable", "draggable"):
        pytest.skip("QScrollArea crashes in QT6. Skip for now.")
    ui = _make_class(wtype)()
    ui.show(run=False)
    ui[0]
    ui[1].changed()
    ui.B[0].changed()
    ui.B[1].changed()
    if hasattr(ui, "current_index"):
        ui.current_index = 1
    ui.close()
