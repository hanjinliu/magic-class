from magicclass import magicclass, magicmenu, magictoolbar, field, MagicTemplate

def test_find_ancestor():
    @magicclass
    class B(MagicTemplate):
        def f(self):
            parent = self.find_ancestor(A)
            parent.i.value = 10

    @magicclass
    class A(MagicTemplate):
        i = field(int)
        b = field(B)

    ui = A()
    assert ui.i.value == 0
    ui.b.f()
    assert ui.i.value == 10

def test_add_dock_widget():
    @magicclass(widget_type="mainwindow")
    class Main(MagicTemplate):
        pass

    @magicclass
    class A(MagicTemplate):
        i = field(int)

    ui = Main()
    ui.add_dock_widget(A())
    ui.add_dock_widget(A())
    ui.add_dock_widget(A())


def test_post_append():
    from types import MethodType

    @magicclass
    class A:
        a = 0
        @magicmenu
        class Menu:
            pass
        @magictoolbar
        class Tool:
            pass

        def f(self):
            self.a = 1

    ui = A()

    @ui.append
    def g(): pass
    @ui.Menu.append
    def g(): pass
    @ui.Tool.append
    def g(): pass

    assert isinstance(ui.g, MethodType)
    ui["g"]
    assert isinstance(ui.Menu.g, MethodType)
    ui.Menu["g"]
    assert isinstance(ui.Tool.g, MethodType)
    ui.Tool["g"]

    @ui.append
    def f(): pass

    # the original method should not be updated
    ui.f()
    assert ui.a == 1
