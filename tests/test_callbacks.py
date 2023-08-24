from magicclass import magicclass, magicmenu, MagicTemplate, field, vfield, abstractapi
from magicclass.utils import thread_worker
import time
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
        result = field(str)

        @x.connect
        def _callback_x(self):
            self.some_function()
            self.result.value = "x changed"

        @y.connect
        def _callback_y(self):
            self.some_function()
            self.result.value = "y changed"

        def some_function(self):
            pass

    ui = A()
    ui.x.value = 1
    assert ui.result.value == "x changed"
    assert str(ui.macro[-1]) == "ui.x.value = 1"
    ui.y = "y"
    assert ui.result.value == "y changed"
    assert str(ui.macro[-1]) == "ui.y = 'y'"


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


def test_callback_block():
    @magicclass
    class A:
        f = field(int)
        result = field(str)

        @f.connect
        def _callback(self):
            self.result.value = str(self.f.value)

    ui = A()
    ui.f.value = 10
    assert str(ui.macro[-1]) == "ui.f.value = 10"
    assert ui.f.value == 10
    assert ui.result.value == "10"


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

def test_parametric_callback():
    @magicclass
    class A:
        a = field(int)

        @a.connect
        def _callback(self, v):
            self._v = v

    ui = A()
    ui.a.value = 1
    assert ui._v == 1

def test_callback_outside_class():
    def _cb0():
        _cb0.x = 1
    def _cb1(val):
        _cb1.x = val
    def _cb2(self, val):
        _cb2.x = val

    @magicclass
    class A:
        a = field(int)
        a.connect(_cb0)
        a.connect(_cb1)
        a.connect(_cb2)

    ui = A()
    ui.a.value = 4
    assert _cb0.x == 1
    assert _cb1.x == 4
    assert _cb2.x == 4

def test_async_callback():
    mock_x = MagicMock()
    mock_y = MagicMock()
    z = []

    @magicclass
    class A(MagicTemplate):
        x = field(int)
        y = vfield(str)

        @x.connect_async
        def _callback_x(self):
            time.sleep(0.05)
            mock_x()
            return "x"

        @y.connect_async
        def _callback_y(self):
            time.sleep(0.05)
            mock_y()
            return "y"

        @_callback_x.returned.connect
        @_callback_y.returned.connect
        def _on_returned(self, v: str):
            z.append(v)

    ui = A()
    with thread_worker.blocking_mode():
        ui.x.value = 1
        mock_x.assert_called_once()
        assert z == ["x"]
        ui.y = "zxcv"
        mock_y.assert_called_once()
        assert z == ["x", "y"]

def test_async_callback_nested():
    @magicclass
    class A(MagicTemplate):
        def __init__(self):
            self._val = None

        @magicclass
        class B(MagicTemplate):
            x = field(int)

        @B.x.connect_async
        def _x(self, v):
            self._val = self, v

    ui = A()
    with thread_worker.blocking_mode():
        ui.B.x.value = 1
        assert ui._val == (ui, 1)

def test_async_callback_wrapped():
    @magicclass
    class A(MagicTemplate):
        def __init__(self):
            self._val = None

        @magicclass
        class B(MagicTemplate):
            x = abstractapi()

        x = B.vfield(int)
        @x.connect_async
        def _x(self, v):
            self._val = self, v

    ui = A()
    with thread_worker.blocking_mode():
        ui.x = 1
        assert ui._val == (ui, 1)

def test_async_callback_generator():
    z = []
    @magicclass
    class A(MagicTemplate):
        x = field(int)

        @x.connect_async
        def _callback_x(self):
            time.sleep(0.05)
            yield
            z.append(0)
            yield
            z.append(1)
            return
    ui = A()
    with thread_worker.blocking_mode():
        ui.x.value = 1
        assert z == [0, 1]
