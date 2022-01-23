from types import MethodType
from magicclass import magicclass, set_options, set_design, do_not_record, confirm, nogui
from magicgui.widgets import PushButton

def test_set_options():
    @magicclass
    class A:
        @set_options(layout="horizontal", call_button="OK", a={"widget_type": "Slider"})
        def f1(self, a: int):
            pass
        
        @set_options(auto_call=True)
        def f2(self, a: int):
            self.a = a
    
    ui = A()
    ui["f1"].changed()
    assert ui["f1"].mgui._layout == "horizontal"
    assert ui["f1"].mgui._call_button.text == "OK"
    assert ui["f1"].mgui["a"].widget_type == "Slider"
    
    ui["f2"].changed()
    assert ui["f2"].mgui._auto_call == True
    ui["f2"].mgui["a"].value = 2
    assert ui.a == 2
    assert str(ui.macro[-1]) == "ui.f2(a=2)"
    assert ui["f2"].mgui.visible
    ui["f2"].mgui["a"].value = 4
    assert ui.a == 4
    assert str(ui.macro[-1]) == "ui.f2(a=4)"
    assert str(ui.macro[-2]) != "ui.f2(a=2)" # for auto_call, macro should be recorded once.

def test_set_design():
    @magicclass
    class A:
        @set_design(text="new-text")
        def f1(self, a: int):
            pass
        
    ui = A()
    assert ui["f1"].text == "new-text"

def test_do_not_record():
    @magicclass
    class A:
        @do_not_record
        def f(self): pass
    
    ui = A()
    ui["f"].changed()
    assert len(ui.macro) == 1

def test_confirm():
    @magicclass
    class A:
        @confirm("really?")
        def f(self):
            self.a = 0
    
    ui = A()
    ui["f"].changed()
    assert ui["f"].mgui[0].value == "really?"
    ui["f"].mgui[-1].changed()
    assert str(ui.macro[-1]) == "ui.f()"

def test_nogui():
    @magicclass
    class A:
        @nogui
        def f(self):
            pass
        
        def g(self):
            pass
    
    ui = A()
    assert isinstance(ui["f"], MethodType)
    assert isinstance(ui["g"], PushButton)