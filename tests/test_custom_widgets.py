from magicclass import magicclass, set_options, field
from magicclass import widgets as wdt

def test_checkbutton():
    @magicclass
    class A:
        b = field(wdt.CheckButton)
        @set_options(x={"widget_type": wdt.CheckButton})
        def f(self, x: bool):
            pass
    ui = A()
    assert isinstance(ui.b, wdt.CheckButton)
    ui.b.value = True
    assert ui.b.native.isChecked()
    ui.b.value = False
    assert not ui.b.native.isChecked()

    ui["f"].changed()
    assert isinstance(ui["f"].mgui[0], wdt.CheckButton)

# def test_figure():
#     @magicclass
#     class A:
#         plt = field(wdt.Figure)

#     ui = A()
#     ui.plt.plot([1,2,3,4])
#     ui.plt.scatter([1,2,3,4], [1,2,3,4])
#     ui.plt.xlim()
#     ui.plt.xlim(0, 2)
#     ui.plt.ylim()
#     ui.plt.ylim(0, 2)
#     ui.plt.cla()
#     ui.plt.title("title")
#     ui.plt.xlabel("x")
#     ui.plt.ylabel("y")
#     ui.plt.imshow([[0, 0], [1, 1]])
#     ui.plt.legend()
