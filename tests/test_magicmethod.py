from magicclass import magicclass, magicmenu, magictoolbar, magicmethod, field, MagicTemplate
from magicclass.gui import ClassGui
from magicclass.gui.mgui_ext import PushButtonPlus
    
def test_construction_and_macro():
    @magicclass
    class A:
        @magicmenu
        class Menu:
            @magicmethod
            class mmethod:
                a = field(int)
            def action1(self): ...
        @magictoolbar
        class Tool:
            @magicmethod
            class mmethod:
                a = field(int)
            def tool1(self): ...
        
        @magicmethod
        class mmethod:
            a = field(int)
    
    ui = A()
    assert isinstance(ui.mmethod, ClassGui)
    assert isinstance(ui.Menu.mmethod, ClassGui)
    assert isinstance(ui.Tool.mmethod, ClassGui)
    assert isinstance(ui[-1], PushButtonPlus)
    ui.Menu.mmethod.a.value = 10
    assert str(ui.macro[-1]) == "ui.Menu.mmethod.a.value = 10"
    ui.Tool.mmethod.a.value = 10
    assert str(ui.macro[-1]) == "ui.Tool.mmethod.a.value = 10"
    ui.mmethod.a.value = 10
    assert str(ui.macro[-1]) == "ui.mmethod.a.value = 10"


def test_template_inheritance():
    @magicclass
    class A(MagicTemplate):
        @magicmenu
        class Menu(MagicTemplate):
            @magicmethod
            class mmethod(MagicTemplate):
                a = field(int)
            def action1(self): ...
        @magictoolbar
        class Tool(MagicTemplate):
            @magicmethod
            class mmethod(MagicTemplate):
                a = field(int)
            def tool1(self): ...
        
        @magicmethod
        class mmethod(MagicTemplate):
            a = field(int)
    
    ui = A()
    assert isinstance(ui.mmethod, ClassGui)
    assert isinstance(ui.Menu.mmethod, ClassGui)
    assert isinstance(ui.Tool.mmethod, ClassGui)
    assert isinstance(ui[-1], PushButtonPlus)
    ui.Menu.mmethod.a.value = 10
    assert str(ui.macro[-1]) == "ui.Menu.mmethod.a.value = 10"
    ui.Tool.mmethod.a.value = 10
    assert str(ui.macro[-1]) == "ui.Tool.mmethod.a.value = 10"
    ui.mmethod.a.value = 10
    assert str(ui.macro[-1]) == "ui.mmethod.a.value = 10"
    

def test_doc():
    @magicclass
    class A:
        @magicmethod
        class f:
            """doc"""
            a = field(str)
            def func(self): ...
    
    ui = A()
    assert ui[0].tooltip == "doc"