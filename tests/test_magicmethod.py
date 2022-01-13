from unittest.mock import MagicMock
from magicclass import (
    magicclass,
    magicmenu,
    magictoolbar,
    magicmethod,
    field,
    MagicTemplate,
    set_design
    )
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
    

def test_doc_and_design():
    @magicclass
    class A:
        @set_design(text="new text")
        @magicmethod
        class f:
            """doc"""
            a = field(str)
            def func(self): ...
    
    ui = A()
    assert ui[0].tooltip == "doc"
    assert ui[0].text == "new text"

def test_wraps():
    @magicclass
    class A:
        @magicmenu
        class Menu:
            def f(self): ...
        
        @Menu.wraps
        @magicmethod
        class f:
            a = field(str)
            def func(self): ...
    
    ui = A()
    ui.Menu[0].changed()
    assert ui.f.visible
    ui.f.hide()
    
    mock = MagicMock()
    
    @magicclass
    class A:
        @magicmethod
        class f:
            a = field(str)
            def func(self): ...
        
        @f.wraps
        def func(self):
            mock()
    
    ui = A()
    ui.f["func"].changed()
    mock.assert_called_once()
