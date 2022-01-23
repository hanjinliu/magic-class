from magicclass import magicclass, field, MagicTemplate

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
    