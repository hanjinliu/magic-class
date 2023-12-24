from typing_extensions import Annotated
from magicclass import (
    magicclass,
    magicmenu,
    magictoolbar,
    field,
    vfield,
    abstractapi,
    FieldGroup,
    HasFields,
)
from magicclass.fields import widget_property
from magicclass.types import Optional
from magicgui import widgets
import sys
from unittest.mock import MagicMock
import pytest

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

    @magicclass
    class D:
        a_int = field(widget_type=widgets.SpinBox)
        a_float = field(widget_type=widgets.FloatSpinBox)
        a_str = field(widget_type=widgets.LineEdit)
        a_bool = field(widget_type=widgets.CheckBox)

    @magicclass
    class E:
        a_int = field(widget_type="SpinBox")
        a_float = field(widget_type="FloatSpinBox")
        a_str = field(widget_type="LineEdit")
        a_bool = field(widget_type="CheckBox")

    answers = [widgets.SpinBox, widgets.FloatSpinBox,
               widgets.LineEdit, widgets.CheckBox]

    for cls in [A, B, C, D, E]:
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

    c = C()
    c.a_int

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

def test_enabled():
    @magicclass
    class A:
        @magicclass
        class B:
            a1 = field(int, options={"enabled": False})
            a2 = vfield(int, options={"enabled": False})
        b1 = field("b1", options={"enabled": False})
        b2 = field("b2", options={"enabled": False})

    ui = A()
    assert not ui[1].enabled
    assert not ui[2].enabled
    assert not ui.B[0].enabled
    assert not ui.B[1].enabled

def test_get_value_field_widget():
    @magicclass
    class A:
        x_1 = field(int)
        y_1 = vfield(int)
    ui = A()
    assert type(ui.y_1) is int
    assert type(ui["x_1"]) is widgets.SpinBox
    assert type(ui["y_1"]) is widgets.SpinBox

@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9+")
def test_generic_and_annotated():
    w0 = field(tuple[int, str]).to_widget()
    w1 = field(Optional[int], options={"text": "XXX", "options": {"max": 10}}).to_widget()
    w2 = field(Optional[tuple[int, str]]).to_widget()

    assert w0.widget_type == "TupleEdit"
    assert w1.widget_type == "OptionalWidget"
    assert w0[0].widget_type == "SpinBox"
    assert w0[1].widget_type == "LineEdit"
    assert w1[0].text == "XXX"
    assert w1[1].max == 10
    assert w2[1].widget_type == "TupleEdit"

def test_field_in_non_gui():
    """Test fields can be used in non-GUI classes."""
    class A:
        x = field(int)
        y = vfield(str)

        def __init__(self):
            self._x_value = None
            self._y_value = None

        @x.connect
        def _x(self):
            self._x_value = self.x.value

        @y.connect
        def _y(self):
            self._y_value = self.y

    a = A()
    assert a.x.widget_type == "SpinBox"
    a.x.value = 1
    assert a._x_value == 1
    a.y = "xxx"
    assert a._y_value == "xxx"

def test_field_group():
    from magicgui.widgets import Container

    class Params(FieldGroup):
        x = field(int)
        y = vfield(str)

    class A:
        params = Params(layout="horizontal")
        params2 = Params(layout="horizontal")

    a0 = A()
    assert isinstance(a0.params, Container)
    assert a0.params.x.widget_type == "SpinBox"
    assert a0.params.y == ""
    a0.params.x.value = 10
    a0.params.y = "t"
    assert a0.params2.x.value == 0
    assert a0.params2.y == ""


    a1 = A()
    assert a1.params.x.value == 0
    assert a1.params.y == ""

    @magicclass
    class Main:
        params = Params()

    ui = Main()
    assert ui.params is ui[0]

def test_field_group_signal():
    mock1 = MagicMock()
    mock2 = MagicMock()

    class Params(FieldGroup):
        x = field(int)
        y = vfield(str)

    class A:
        params1 = Params(layout="horizontal")
        params2 = Params(layout="horizontal")

        @params1.connect
        def _f1(self, w):
            mock1()

        @params2.connect
        def _f2(self, w):
            mock2()

    ui = A()
    mock1.assert_not_called()
    mock2.assert_not_called()
    ui.params1.x.value = 2
    mock1.assert_called_once()
    mock2.assert_not_called()
    ui.params2.y = "x"
    mock1.assert_called_once()
    mock2.assert_called_once()


def test_nesting_field_group():
    class Params(FieldGroup):
        x = field(int)
        y = vfield(str)

    class G(FieldGroup):
        p = Params()
        u = field(bool)
        v = vfield(float)

    class A:
        g = G()

        def __init__(self):
            self.out = "None"
            self.g.p.signals.x.connect(lambda: self.set_output("x"))
            self.g.p.signals.y.connect(lambda: self.set_output("y"))

        def set_output(self, out):
            self.out = out

    a0 = A()
    a1 = A()

    assert a0.g.p.x.value == 0
    assert a0.g.p.y == ""
    assert a0.g.p is a0.g.p
    assert a0.g.widgets.p is a0.g.widgets.p
    assert a0.g.p.widgets.x is a0.g.p.widgets.x
    assert a0.g.p is not a1.g.p

    a0.g.p.x.value = 1
    assert a0.out == "x"
    assert a1.out == "None"
    a0.g.p.y = "a"
    assert a0.out == "y"
    assert a1.out == "None"
    a1.g.p.y = "xx"
    assert a0.out == "y"
    assert a1.out == "y"


def test_has_fields():
    class A(HasFields):
        x = vfield(int)
        y = vfield(str)
        @property
        def value(self):
            return self.x, self.y

    a0 = A()
    a1 = A()
    assert len(A._fields) == 2

    # test repr works
    repr(a0)
    repr(a0.widgets)
    repr(a0.signals)

    a0.x = 10
    a0.y = "abc"

    assert (10, "abc") == a0.value
    assert (0, "") == a1.value

    c0 = a0.widgets.as_container()
    assert len(c0) == 2
    assert c0[0].name == "x"
    assert c0[1].name == "y"
    assert c0["x"].value == a0.x
    assert c0["y"].value == a0.y

def test_widget_property():
    from magicgui.widgets import Slider
    mock = MagicMock()

    class A(HasFields):
        def __init__(self, max=5):
            self._max = max
            self.result = None

        @widget_property
        def a(self):
            return Slider(max=self._max)

        @a.connect
        def _a(self, v):
            self.result = v

    x = A(max=10)
    y = A(max=20)

    assert x.widgets is not y.widgets
    assert x.widgets.a.max == 10
    assert y.widgets.a.max == 20

    x.a = 1
    assert x.result == 1
    assert y.result is None

def test_tooltip_magicclass():
    @magicclass
    class A:
        """
        Test class.

        Attributes
        ----------
        a : SpinBox
            Parameter-a.
        b : str
            Parameter-b.
        """
        a = field(int)
        b = vfield(str)

    ui = A()
    assert ui.a.tooltip == "Parameter-a."
    assert ui["b"].tooltip == "Parameter-b."

def test_tooltip_hasfields():
    class B(HasFields):
        """
        Test class.

        Attributes
        ----------
        a : SpinBox
            Parameter-a.
        b : str
            Parameter-b.
        """
        a = field(int)
        b = vfield(str)

    ui = B()
    assert ui.widgets.a.tooltip == "Parameter-a."
    assert ui.widgets.b.tooltip == "Parameter-b."

def test_tooltip_magicmenu():
    @magicmenu
    class A:
        """
        Test class.

        Attributes
        ----------
        a : SpinBox
            Parameter-a.
        b : str
            Parameter-b.
        """
        a = field(int)
        b = vfield(str)

    ui = A()
    assert ui.a.tooltip == "Parameter-a."
    assert ui["b"].tooltip == "Parameter-b."

def test_tooltip_magictoolbar():
    @magictoolbar
    class A:
        """
        Test class.

        Attributes
        ----------
        a : SpinBox
            Parameter-a.
        b : str
            Parameter-b.
        """
        a = field(int)
        b = vfield(str)

    ui = A()
    assert ui.a.tooltip == "Parameter-a."
    assert ui["b"].tooltip == "Parameter-b."


def test_visible_false():
    @magicclass
    class A:
        x = vfield(int, options={"visible": False})

    ui = A()
    ui.show(run=False)
    assert not ui["x"].visible
    ui.close()

def test_get_set_hooks():
    class A:
        offset = 1
        suffix = "-0"

        x = vfield(int)
        y = vfield(str)

        @x.pre_set_hook
        def _x_set(self, value):
            return value + self.offset

        @y.post_get_hook
        def _y_get(self, value):
            return value + self.suffix

    a = A()
    a.x = 10
    assert a.x == 11
    a.y = "Y"
    assert a.y == "Y-0"

def test_with_options():
    @magicclass
    class A:
        a_int = field(int).with_options(max=10)
        a_float = field(float).with_options(max=20.0)
        a_str = field(str).with_options(enabled=False)
        a_bool = field(bool).with_options(visible=False)

    ui = A()
    assert ui.a_int.max == 10
    assert ui.a_float.max == 20.0
    assert not ui.a_str.enabled
    assert not ui.a_bool.visible

def test_with_choices():
    @magicclass
    class A:
        def _get_choices(self, w):
            return [1, 2, 3]
        a_int1 = field(int).with_choices([1, 2, 3])
        b_int1 = field().with_choices(_get_choices)
        a_int2 = vfield(int).with_choices([1, 2, 3])
        b_int2 = vfield().with_choices(_get_choices)

    ui = A()
    assert ui["a_int1"].widget_type == "ComboBox"
    assert ui["b_int1"].widget_type == "ComboBox"
    assert ui["a_int2"].widget_type == "ComboBox"
    assert ui["b_int2"].widget_type == "ComboBox"

def test_box():
    from magicclass import box

    @magicclass
    class A:
        x0 = box.resizable(field(0))
        x1 = box.resizable(vfield(1))
        y0 = box.scrollable(field(2))
        y1 = box.scrollable(vfield(3))
        z0 = box.draggable(field(4))
        z1 = box.draggable(vfield(5))
        w0 = box.collapsible(field(6))
        w1 = box.collapsible(vfield(7))

    ui = A()

    assert ui.x0.widget_type == "SpinBox" and ui.x0.value == 0
    assert ui.x1 == 1
    assert ui.y0.widget_type == "SpinBox" and ui.y0.value == 2
    assert ui.y1 == 3
    assert ui.z0.widget_type == "SpinBox" and ui.z0.value == 4
    assert ui.z1 == 5
    assert ui.w0.widget_type == "SpinBox" and ui.w0.value == 6
    assert ui.w1 == 7

    ui.x0.value = 1
    ui.x1 = 2
    ui.y0.value = 3
    ui.y1 = 4
    ui.z0.value = 5
    ui.z1 = 6
    ui.w0.value = 7
    ui.w1 = 8

    assert ui.x0.value == 1
    assert ui.x1 == 2
    assert ui.y0.value == 3
    assert ui.y1 == 4
    assert ui.z0.value == 5
    assert ui.z1 == 6
    assert ui.w0.value == 7
    assert ui.w1 == 8

    assert str(ui.macro[1]) == "ui.x0.value = 1"
    assert str(ui.macro[2]) == "ui.x1 = 2"
    assert str(ui.macro[3]) == "ui.y0.value = 3"
    assert str(ui.macro[4]) == "ui.y1 = 4"
    assert str(ui.macro[5]) == "ui.z0.value = 5"
    assert str(ui.macro[6]) == "ui.z1 = 6"
    assert str(ui.macro[7]) == "ui.w0.value = 7"
    assert str(ui.macro[8]) == "ui.w1 = 8"

def test_magicclass_in_box():
    from magicclass.box import resizable

    @magicclass
    class A:
        def f(self):
            pass
        x = field(int)

    @magicclass
    class B:
        xx = field(A)
        a = resizable(field(A))

    ui = B()
    ui.a.f()
    ui.a.x.value = 123

    assert str(ui.macro[1]) == "ui.a.f()"
    assert str(ui.macro[2]) == "ui.a.x.value = 123"

def test_box_with_wraps():
    from magicclass.box import resizable

    @magicclass
    class A:
        x = abstractapi()

    @magicclass
    class B0:
        a0 = resizable(field(A))

        @a0.wraps
        def x(self):
            pass

    @magicclass
    class B1:
        a0 = resizable(A)

        @a0.wraps
        def x(self):
            pass

    B0().x()
    B1().x()

def test_nested_boxes():
    from magicclass.box import resizable, collapsible

    @magicclass
    class A:
        x = collapsible(resizable(field(2)))
        y = resizable(collapsible(vfield(3)))

    ui = A()
    assert ui.x.widget_type == "SpinBox"
    assert ui.x.value == 2
    ui.x.value = 5
    assert ui.x.value == 5
    assert ui.y == 3
    ui.y = 10
    assert ui.y == 10

def test_class_annotation():
    @magicclass
    class A:
        x: Annotated[int, {"max": 10}] = field(0)
        y: Annotated[float, {"widget_type": "FloatSlider"}] = vfield(4.0)
    ui = A()
    assert ui.x.max == 10
    assert ui["y"].widget_type == "FloatSlider"

def test_using_same_class():
    @magicclass(layout="horizontal", labels=False)
    class Laser:
        bar = vfield(0, widget_type="ProgressBar").with_options(min=0, max=100)
        percent = vfield(0, widget_type="SpinBox").with_options(min=0, max=100)

        def apply(self, value: Annotated[int, {"bind": percent}]):
            """Apply laser power."""
            self.bar = self.percent = value

    @magicclass(labels=False)
    class LaserControl:
        laser_blue = field(Laser)
        laser_green = field(Laser)
        laser_red = field(Laser)

    ui = LaserControl()

    ui.laser_blue.percent = 15
    ui.laser_blue["apply"].changed()
    assert ui.laser_blue.bar == 15
    assert ui.laser_green.bar == 0
    assert ui.laser_red.bar == 0
    ui.laser_green["apply"].changed()
    ui.laser_red["apply"].changed()
