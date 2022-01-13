from magicclass import magicclass, set_options, field
from magicclass import widgets as wdt

def test_checkbutton():
    @magicclass
    class A:
        b = field(wdt.CheckButton)
        @set_options(x={"widget_type": wdt.CheckButton})
        def f(self, x: bool):
            print(x)
    ui = A()
    assert isinstance(ui.b, wdt.CheckButton)
    ui.b.changed()
    assert ui.b.value
    ui.b.changed()
    assert not ui.b.value
    
    ui["f"].changed()
    assert isinstance(ui["f"].mgui[0], wdt.CheckButton)