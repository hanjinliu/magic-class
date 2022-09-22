from typing import Annotated
from magicclass import magicclass, set_options, get_function_gui
from magicclass.types import Optional
from magicclass import widgets

def test_basics():
    @magicclass
    class A:
        def f(self, x: Optional[int]):
            pass
    ui = A()
    ui["f"].changed()
    opt = get_function_gui(ui, "f")[0]

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
    opt = get_function_gui(ui, "f")[0]

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
    opt = get_function_gui(ui, "f")[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.text == "x-text"
    assert not opt[1].visible
    assert opt[1].min == -1
