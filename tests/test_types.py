from typing_extensions import Annotated

import pytest
from magicclass import magicclass, set_options, get_function_gui
from magicclass.types import Optional, Union, Path
from magicclass import widgets

def test_basics():
    @magicclass
    class A:
        def f(self, x: Optional[int]):
            pass
    ui = A()
    ui["f"].changed()
    opt = get_function_gui(ui.f)[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.value is None

def test_set_options():
    @magicclass
    class A:
        @set_options(x={"text": "x-text", "options": {"min": -1}})
        def f(self, x: Optional[int] = 0):
            x.as_integer_ratio()

    ui = A()
    ui["f"].changed()
    opt = get_function_gui(ui.f)[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.text == "x-text"
    assert opt[1].visible
    assert opt[1].min == -1

def test_optional_with_annotated():
    T = Annotated[Optional[int], {"text": "x-text", "options": {"min": -1}}]

    @magicclass
    class A:
        def f(self, x: T = None):
            x.as_integer_ratio()

    ui = A()
    ui["f"].changed()
    opt = get_function_gui(ui.f)[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.text == "x-text"
    assert not opt[1].visible
    assert opt[1].min == -1

def test_union():
    @magicclass
    class A:
        def f(self, x: Union[int, str]):
            pass

    ui = A()
    wdt = get_function_gui(ui.f)[0]
    assert wdt.widget_type == "UnionWidget"
    assert wdt[0].widget_type == "SpinBox"
    assert wdt[1].widget_type == "LineEdit"

def test_union_with_default():
    @magicclass
    class A:
        def f(self, x: Union[int, str] = "a"):
            pass

    ui = A()
    wdt = get_function_gui(ui.f)[0]
    assert wdt.widget_type == "UnionWidget"
    assert wdt[0].widget_type == "SpinBox"
    assert wdt[1].widget_type == "LineEdit"
    assert wdt.value == "a"
    assert wdt.current_index == 1

def test_union_with_set_option():
    @magicclass
    class A:
        @set_options(x={"options": [{"max": 4}, {"max": 5.0}]})
        def f(self, x: Union[int, float]):
            pass

    ui = A()
    wdt = get_function_gui(ui.f)[0]
    assert wdt.widget_type == "UnionWidget"
    assert wdt[0].widget_type == "SpinBox"
    assert wdt[1].widget_type == "FloatSpinBox"
    assert wdt[0].max == 4
    assert wdt[1].max == 5.0

@pytest.mark.parametrize(
    "typ, mode",
    [(Path, "r"), (Path.Read, "r"), (Path.Save, "w"), (Path.Dir, "d"), (Path.Multiple, "rm")]
)
def test_path_annotation(typ, mode):
    from magicgui.types import FileDialogMode
    @magicclass
    class A:
        def f0(self, x: typ):
            pass
    ui = A()
    wdt = get_function_gui(ui.f0).x
    assert type(wdt) is widgets.FileEdit
    assert wdt.mode == FileDialogMode(mode)

@pytest.mark.parametrize(
    "typ, mode",
    [(Path, "r"), (Path.Read, "r"), (Path.Save, "w"), (Path.Dir, "d"), (Path.Multiple, "rm")]
)
def test_path_filter(typ, mode):
    from magicgui.types import FileDialogMode
    @magicclass
    class A:
        def f0(self, x: typ["*.py"]):
            pass
    ui = A()
    wdt = get_function_gui(ui.f0).x
    assert type(wdt) is widgets.FileEdit
    assert wdt.mode == FileDialogMode(mode)
    assert wdt.filter == "*.py"
