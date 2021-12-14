from magicclass import magicclass, PopUpMode

def _make_class(mode: PopUpMode):
    @magicclass(popup_mode=mode)
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
            continue
        ui = _make_class(mode)()
        ui.show(run=False)
        ui[1].changed()
        ui.B[0].changed()
        ui.B[1].changed()
        ui.close()