from magicclass import magicclass, set_options
from magicclass.types import Optional
from magicclass import widgets

def test_basics():
    @magicclass
    class A:
        def f(self, x: Optional[int]):
            pass
    ui = A()
    ui["f"].changed()
    opt = ui["f"].mgui[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.value is None

def test_set_options():
    @magicclass
    class A:
        @set_options(x={"text": "x-text", "options": {"min": -1}})
        def f(self, x: Optional[int] = 0):
            pass

    ui = A()
    ui["f"].changed()
    opt = ui["f"].mgui[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.text == "x-text"
    assert opt[1].visible
    assert opt[1].min == -1
