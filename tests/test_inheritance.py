from magicclass import magicclass, field, MagicTemplate

def test_predefinition():
    class Base(MagicTemplate):
        a = field(int)
        def shared_func_1(self, a: int):
            self.a.value = a
        def abstract_func(self): pass
        def shared_func_2(self, a: int):
            self.a.value = a

    @magicclass
    class A(Base):
        a = field(int)  # field needs re-definition
        def abstract_func(self): pass
        def func_a(self): pass

    @magicclass
    class B(Base):
        def func_b(self): pass
        a = field(int)
        def abstract_func(self): pass

    a = A()
    b = B()
    
    assert a[0].name == "a"
    assert a[1].name == "shared_func_1"
    assert a[2].name == "abstract_func"
    assert a[3].name == "shared_func_2"
    assert a[4].name == "func_a"
    
    assert b[0].name == "a"
    assert b[1].name == "shared_func_1"
    assert b[2].name == "abstract_func"
    assert b[3].name == "shared_func_2"
    assert b[4].name == "func_b"
    
    # test value change
    
    a.shared_func_1(10)
    assert a.a.value == 10
    assert b.a.value == 0
    
    b.shared_func_2(15)
    assert a.a.value == 10
    assert b.a.value == 15
