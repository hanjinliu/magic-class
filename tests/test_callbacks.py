from magicclass import magicclass, magicmenu, MagicTemplate, field, vfield
from unittest.mock import MagicMock
import pytest

def test_simple_callback():
    mock_x = MagicMock()
    mock_y = MagicMock()
    
    @magicclass
    class A(MagicTemplate):
        x = field(int)
        y = vfield(str)
        
        @x.connect
        def _callback_x(self):
            mock_x()
        
        @y.connect
        def _callback_y(self):
            mock_y()
    
    ui = A()
    ui.x.value
    ui.y
    mock_x.assert_not_called()
    mock_y.assert_not_called()
    ui.x.value += 1
    mock_x.assert_called_once()
    mock_y.assert_not_called()
    ui.y = "y"
    mock_x.assert_called_once()
    mock_y.assert_called_once()

def test_macro_blocked():    
    @magicclass
    class A(MagicTemplate):
        x = field(int)
        y = vfield(str)
        
        @x.connect
        def _callback_x(self):
            self.some_function()
            self.y = "changed"
        
        @y.connect
        def _callback_y(self):
            self.some_function()
            self.x.value = 100
        
        def some_function(self):
            pass
    
    ui = A()
    ui.x.value = 1
    assert ui.y == "changed"
    assert str(ui.macro[-1]) == "ui.x.value = 1"
    ui.y = "y"
    assert ui.x.value == 100
    assert str(ui.macro[-1]) == "ui.y = 1"
    

def test_callback_in_parent():
    mock = MagicMock()
    mock2 = MagicMock()
    
    @magicclass
    class A(MagicTemplate):
        @magicclass
        class B(MagicTemplate):
            b_x = field(int)
            b_y = vfield(int)
            @magicmenu
            class M(MagicTemplate):
                m_x = field(int)
                m_y = vfield(int)
            
            @M.m_x.connect
            def _callback_m_x(self):
                mock(name="m_x/B")
            
            @M.m_y.connect
            def _callback_m_y(self):
                mock(name="m_y/B")

        @B.M.m_x.connect
        def _callback_m_x(self):
            mock2(name="m_x/A")
        
        @B.M.m_y.connect
        def _callback_m_y(self):
            mock2(name="m_y/A")
            
        @B.b_x.connect
        def _callback_b_x(self):
            mock(name="b_x/A")
        
        @B.b_y.connect
        def _callback_b_y(self):
            mock(name="b_y/A")
        
    ui = A()
    mock.assert_not_called()
    ui.B.b_x.value += 1
    mock.assert_called_once_with(name="b_x/A")
    ui.B.b_y += 1
    mock.assert_called_with(name="b_y/A")
    ui.B.M.m_x.value += 1
    mock2.assert_called_with(name="m_x/A")
    mock.assert_called_with(name="m_x/B")
    ui.B.M.m_y += 1
    mock2.assert_called_with(name="m_y/A")
    mock.assert_called_with(name="m_y/B")


def test_warning():
    # Should warn if widgets that does not have signal instance is connected with
    # callbacks
    from magicclass.widgets import Separator
    @magicclass
    class A:
        a = field(Separator)
        @a.connect
        def _callback(self):
            pass
            
    with pytest.warns(UserWarning):
        ui = A()

def test_container_callback():
    from magicclass.widgets import GroupBoxContainer, LineEdit
    mock = MagicMock()
    @magicclass
    class A:
        a = field(GroupBoxContainer)
        def __post_init__(self):
            self.line = LineEdit()
            self.a.append(self.line)
            
        @a.connect
        def _callback(self):
            mock()
    
    ui = A()
    mock.assert_not_called()
    ui.a[0].value = "xxx"
    mock.assert_called()