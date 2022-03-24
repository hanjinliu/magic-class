from magicclass import magicclass, field, set_options, set_design
from magicclass.core import magicmenu
from magicclass.fields import vfield
from magicclass.types import Bound
from magicclass.qthreading import thread_worker
import time
from unittest.mock import MagicMock

def test_worker_basic():
    mock = MagicMock()
    @magicclass
    class A:
        @thread_worker
        def f(self):
            time.sleep(0.01)

        @f.returned.connect
        def on_return(self, _=None):
            mock()

    ui = A()
    ui.f()
    mock.assert_called_once()
    assert str(ui.macro[-1]) == "ui.f()"

def test_wraps():
    mock = MagicMock()
    @magicclass
    class A:
        a = vfield(0)

        @magicmenu
        class Menu:
            def f(self): ...
            def g(self): ...

        @Menu.wraps
        @thread_worker
        def f(self):
            time.sleep(0.01)

        @thread_worker
        @Menu.wraps
        def g(self, x: int):
            time.sleep(0.01)
            return x

        @f.returned.connect
        def _on_return(self, _=None):
            mock()

        @g.returned.connect
        def _update(self, v):
            self.a = v

    ui = A()
    assert not ui["f"].visible
    assert not ui["g"].visible
    ui.f()
    mock.assert_called_once()
    ui.g(1)
    assert ui.a == 1
    assert str(ui.macro[-1]) == "ui.g(x=1)"
