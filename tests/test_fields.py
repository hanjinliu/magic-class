from magicclass import magicclass, magicmenu, magictoolbar, field, vfield, set_design
from magicgui import widgets
from pathlib import Path

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
    # test field
    @magicclass
    class A:
        @magicclass
        class B:
            def f1(self): ...
            i = field(str)
        x = field(int)
    
    ui = A()
    ui.x.value = 10
    assert str(ui.macro[-1]) == "ui.x.value = 10"
    ui.B.i.value = "aaa"
    assert str(ui.macro[-1]) == "ui.B.i.value = 'aaa'"
    
    # test vfield
    @magicclass
    class A:
        @magicclass
        class B:
            def f1(self): ...
            i = vfield(str)
        x = vfield(int)
    
    ui = A()
    ui.x = 10
    assert str(ui.macro[-1]) == "ui.x = 10"
    ui.B.i = "aaa"
    assert str(ui.macro[-1]) == "ui.B.i = 'aaa'"
    
    # test field
    @magicclass
    class A:
        @magicclass
        class B:
            @magictoolbar
            class Tool:
                a2 = field(int)
            a1 = field(int)
        a0 = field(int)
    
    ui = A()
    ui.a0.value = 10
    assert str(ui.macro[-1]) == "ui.a0.value = 10"
    ui.B.Tool.a2.value = 10
    assert str(ui.macro[-1]) == "ui.B.Tool.a2.value = 10"
    
    
    # test vfield
    @magicclass
    class A:
        @magicclass
        class B:
            @magictoolbar
            class Tool:
                a2 = vfield(int)
            a1 = vfield(int)
        a0 = vfield(int)
    
    ui = A()
    ui.a0 = 10
    assert str(ui.macro[-1]) == "ui.a0 = 10"
    ui.B.Tool.a2 = 10
    assert str(ui.macro[-1]) == "ui.B.Tool.a2 = 10"
    

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
    
    @magicclass
    class A:
        @magictoolbar
        class B:
            a_int = field(0)
            a_float = field(0.0)
            a_int_sl = field(0, widget_type="Slider")
            a_float_sl = field(0, widget_type="FloatSlider")
            a_str = field("0")
            a_bool = field(False)
    
    ui = A()

    @magicclass
    class A:
        @magicmenu
        class B:
            a_int = vfield(0)
            a_float = vfield(0.0)
            a_int_sl = vfield(0, widget_type="Slider")
            a_float_sl = vfield(0, widget_type="FloatSlider")
            a_str = vfield("0")
            a_bool = vfield(False)
    
    ui = A()
    
    @magicclass
    class A:
        @magictoolbar
        class B:
            a_int = vfield(0)
            a_float = vfield(0.0)
            a_int_sl = vfield(0, widget_type="Slider")
            a_float_sl = vfield(0, widget_type="FloatSlider")
            a_str = vfield("0")
            a_bool = vfield(False)
    
    ui = A()
    
    
def test_dont_record():
    @magicclass
    class A:
        t = field(int, record=True)
        f = field(int, record=False)
    
    ui = A()
    ui.t.value = 10
    assert str(ui.macro[-1]) == "ui.t.value = 10"
    ui.f.value = 10
    assert str(ui.macro[-1]) == "ui.t.value = 10"
    ui.t.value = 20
    assert str(ui.macro[-2]) != "ui.t.value = 10"
    assert str(ui.macro[-1]) == "ui.t.value = 20"
    
    @magicclass
    class A:
        t = vfield(int, record=True)
        f = vfield(int, record=False)
    
    ui = A()
    ui.t = 10
    assert str(ui.macro[-1]) == "ui.t = 10"
    ui.f = 10
    assert str(ui.macro[-1]) == "ui.t = 10"
    ui.t = 20
    assert str(ui.macro[-2]) != "ui.t = 10"
    assert str(ui.macro[-1]) == "ui.t = 20"
    

def test_icon():
    def _icon_byte(a):
        return a.native.icon().pixmap(10,10).toImage().byteCount()
    path = Path(__file__).parent / "icons" / "star.png"
    
    @magicclass
    class A:
        @magicmenu
        class Menu:
            a = field(bool, options={"icon_path": path})
            @set_design(icon_path=path)
            def func(self): ...
    
    ui = A()
    
    assert _icon_byte(ui.Menu.a) > 0
    assert _icon_byte(ui.Menu["func"]) > 0
    
    @magicclass
    class A:
        @magictoolbar
        class Menu:
            a = field(bool, options={"icon_path": path})
            @set_design(icon_path=path)
            def func(self): ...
    
    ui = A()
    
    assert _icon_byte(ui.Menu.a) > 0
    assert _icon_byte(ui.Menu["func"]) > 0