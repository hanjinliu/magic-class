from magicclass import magicclass, WidgetType, build_help

def _make_class(t: WidgetType):
    @magicclass(widget_type=t)
    class A:
        @magicclass
        class B:
            def b1(self, a: int): ...
            def b2(self, a: int): ...
        
        def a1(self, a: int): ...
        
        @B.wraps
        def b1(self, a: int): ...
    
    return A


def test_all_works():
    for wtype in WidgetType._member_names_:
        ui = _make_class(wtype)()
        ui.show(run=False)
        ui[0]
        ui[1].changed()
        ui.B[0].changed()
        ui.B[1].changed()
        ui.close()
        help = build_help(ui)
        help.show()
        help.close()