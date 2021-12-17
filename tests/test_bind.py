from magicclass import magicclass, Bound, set_options, field, vfield
from magicclass.core import magictoolbar

def test_bind_value():
    # test binding an invariable
    @magicclass
    class A:
        @set_options(x={"bind": 10})
        def func(self, x):
            pass
    
    ui = A()
    ui["func"].changed()
    assert str(ui.macro[-1]) == "ui.func(x=10)"
    
def test_bind_method():
    @magicclass
    class A:
        def __init__(self):
            self.i = 0
            
        def _get_param(self, w=None):
            self.i += 1
            return self.i
        
        @set_options(x={"bind": _get_param})
        def func(self, x):
            pass
    
    ui0 = A()
    ui1 = A()
    
    ui0["func"].changed()
    assert str(ui0.macro[-1]) == "ui.func(x=1)"
    ui0["func"].changed()
    assert str(ui0.macro[-1]) == "ui.func(x=2)"
    assert ui0.i == 2
    assert ui1.i == 0

def test_bind_field():
    @magicclass
    class A:
        a = field(int)
        b = vfield(int)
        
        @set_options(a={"bind": a})
        def func_a(self, a):
            pass
        
        @set_options(b={"bind": b})
        def func_b(self, b):
            pass
    
    ui = A()
    ui["func_a"].changed()
    assert str(ui.macro[-1]) == "ui.func_a(a=0)"
    ui.a.value = 10
    ui["func_a"].changed()
    assert str(ui.macro[-1]) == "ui.func_a(a=10)"
    
    ui["func_b"].changed()
    assert str(ui.macro[-1]) == "ui.func_b(b=0)"
    ui.b = 10
    ui["func_b"].changed()
    assert str(ui.macro[-1]) == "ui.func_b(b=10)"

def test_Bound():
    @magicclass
    class A:
        def __init__(self):
            self.i = 0
            
        def _get_param(self, w=None):
            self.i += 1
            return self.i
    
        a = field("a")
        
        def func(self, x: Bound(_get_param), y: Bound(a)):
            return x, y
    
    ui = A()
    ui["func"].changed()
    assert str(ui.macro[-1]) == "ui.func(x=1, y='a')"

def test_wrapped():
    @magicclass
    class A:
        @magictoolbar
        class B:
            field_b = field("b")
            def _b(self, w=None):
                return "b"
            
            def func_2(self): ...
        
        field_a = field("a")
        def _a(self, w=None):
            return "a"
        
        def func_1(self, x: Bound(_a), y: Bound(B.field_b)):
            self.returned = x, y
        
        @B.wraps
        def func_2(self, x: Bound(field_a), y: Bound(B._b)):
            self.returned = x, y
        
    ui = A()
    ui["func_1"].changed()
    ui["func_2"].changed()
    assert str(ui.macro[-2]) == "ui.func_1(x='a', y='b')"
    assert str(ui.macro[-1]) == "ui.func_2(x='a', y='b')"