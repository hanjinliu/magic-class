from magicclass import magicclass, magicmenu, magiccontext, field, vfield, MagicTemplate
from magicgui import widgets

def test_field_types():
    @magicclass
    class A:
        a_int = field(int)
        a_float = field(float)
        a_str = field(str)
        a_bool = field(bool)
    
    @magicclass
    class B:
        a_int = field(0)
        a_float = field(0.0)
        a_str = field("0")
        a_bool = field(False)
    
    @magicclass
    class C:
        a_int = field(widgets.SpinBox)
        a_float = field(widgets.FloatSpinBox)
        a_str = field(widgets.LineEdit)
        a_bool = field(widgets.CheckBox)
    
    answers = [widgets.SpinBox, widgets.FloatSpinBox,
               widgets.LineEdit, widgets.CheckBox]
    
    for cls in [A, B, C]:
        ui = cls()
        assert len(ui) == 4
        for i in range(4):
            widget = ui[i]
            assert type(widget) is answers[i]
    
    b = B()
    assert b.a_int.value == 0
    assert b.a_float.value == 0.0
    assert b.a_str.value == "0"
    assert b.a_bool.value == False
    
    b.a_int.value = 1
    len0 = len(b.macro)
    assert str(b.macro[-1]) == "ui.a_int.value = 1"
    b.a_int.value = 2
    len1 = len(b.macro)
    assert str(b.macro[-1]) == "ui.a_int.value = 2"
    assert len0 == len1
    

def test_vfield_types():
    @magicclass
    class A:
        a_int = vfield(int)
        a_float = vfield(float)
        a_str = vfield(str)
        a_bool = vfield(bool)
    
    @magicclass
    class B:
        a_int = vfield(0)
        a_float = vfield(0.0)
        a_str = vfield("0")
        a_bool = vfield(False)
    
    @magicclass
    class C:
        a_int = vfield(widgets.SpinBox)
        a_float = vfield(widgets.FloatSpinBox)
        a_str = vfield(widgets.LineEdit)
        a_bool = vfield(widgets.CheckBox)
    
    answers = [widgets.SpinBox, widgets.FloatSpinBox,
               widgets.LineEdit, widgets.CheckBox]
    
    for cls in [A, B, C]:
        ui = cls()
        assert len(ui) == 4
        for i in range(4):
            widget = ui[i]
            assert type(widget) is answers[i]
    
    b = B()
    assert b.a_int == 0
    assert b.a_float == 0.0
    assert b.a_str == "0"
    assert b.a_bool == False

    b.a_int = 1
    len0 = len(b.macro)
    assert str(b.macro[-1]) == "ui.a_int = 1"
    
    b.a_int = 2
    len1 = len(b.macro)
    assert str(b.macro[-1]) == "ui.a_int = 2"
    assert len0 == len1
    
    b.a_str = "x"
    assert str(b.macro[-2]) == "ui.a_int = 2"
    assert str(b.macro[-1]) == "ui.a_str = 'x'"
    
    
def test_field_options():
    tooltip = "this is int"
    name = "New Name"
    @magicclass
    class A:
        a_slider = field(1, widget_type=widgets.Slider)
        a_rename = field(1, name=name)
        a_minmax = field(1, options={"min": -10, "max": 10})
        a_tooltip = field(1, options={"tooltip": tooltip})
        
    ui = A()
    for i in range(4):
        assert ui[i].value == 1
        
    assert type(ui[0]) is widgets.Slider
    assert ui[1].name == name
    assert (ui[2].min, ui[2].max) == (-10, 10)
    ui[2].value = -5 # this should work
    assert ui[3].tooltip == tooltip

def test_fields_in_child():
    @magicclass
    class A:
        @magicclass
        class B:
            def f1(self): ...
            i = field(str)
    
    ui = A()
    ui.B.i.value = "aaa"
    assert str(ui.macro[-1]) == "ui.B.i.value = 'aaa'"


def test_widget_actions():
    @magicclass
    class A:
        @magicmenu
        class B:
            a_int = field(0)
            a_float = field(0.0)
            a_int_sl = field(0, widget_type="Slider")
            a_float_sl = field(0, widget_type="FloatSlider")
            a_str = field("0")
            a_bool = field(False)
    
    ui = A()


    