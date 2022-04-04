from magicclass import magicclass, magicmenu, set_options, do_not_record, vfield, get_function_gui
from magicclass.types import Bound
from magicclass.utils.qthreading import thread_worker
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
    assert ui.a == 0
    ui.g(1)
    assert ui.a == 1
    assert str(ui.macro[-1]) == "ui.g(x=1)"

def test_options():
    @magicclass
    class A:
        @set_options(a={"widget_type": "LogSlider"})
        @thread_worker
        def f(self, a):
            pass

        @thread_worker
        @set_options(a={"widget_type": "LogSlider"})
        def g(self, a):
            pass

    ui = A()
    assert get_function_gui(ui, "f").a.widget_type == "LogSlider"
    assert get_function_gui(ui, "g").a.widget_type == "LogSlider"

def test_bind():
    @magicclass(error_mode="stderr")
    class A:
        a = vfield(int)
        def _get(self, _=None):
            return 10

        @thread_worker
        def f(self, a: Bound[_get]):
            self.a = a

        @f.finished.connect
        def _check(self):
            assert self.a == 10

    ui = A()
    assert ui.a == 0
    assert not get_function_gui(ui, "f").a.visible
    ui["f"].changed()

def test_choice():
    mock = MagicMock()
    @magicclass
    class A:
        def _get_choice(self, _=None):
            return [0, 1]

        @thread_worker
        @set_options(a={"choices": _get_choice})
        def f(self, a):
            pass

        @set_options(a={"choices": _get_choice})
        @thread_worker
        def g(self, a):
            pass

        @f.returned.connect
        @g.returned.connect
        def _on_returned(self, _=None):
            mock()

    ui = A()
    assert get_function_gui(ui, "f").a.choices == (0, 1)
    assert get_function_gui(ui, "g").a.choices == (0, 1)
    mock.assert_not_called()
    ui.f(0)
    mock.assert_called_once()
    mock.reset_mock()
    mock.assert_not_called()
    ui.g(0)
    mock.assert_called_once()

def test_do_not_record():
    @magicclass
    class A:
        def xx(self):
            ...

        @thread_worker
        @do_not_record
        def f(self):
            pass

        @do_not_record
        @thread_worker
        def g(self):
            pass

    ui = A()
    ui.xx()
    ui.f()
    ui.g()
    assert str(ui.macro[-1]) == "ui.xx()"

def test_progressbar():
    from magicgui.widgets import ProgressBar

    @magicclass
    class A:
        # a progress bar widget is newly created
        @thread_worker(progress=True)
        def f(self):
            time.sleep(0.2)

    @magicclass
    class B:
        # use pbar
        pbar = vfield(ProgressBar)
        @thread_worker(progress=True)
        def f(self):
            time.sleep(0.2)

    a = A()
    a.f()
    b = B()
    b.f()

def test_error(qtbot):
    @magicclass(error_mode="stderr")
    class A:
        @thread_worker
        def f(self, n: int = 3):
            if n > 10:
                raise ValueError

    ui = A()
    ui.f(3)
    assert str(ui.macro[-1]) == "ui.f(n=3)"
    with qtbot.capture_exceptions():
        ui.f(20)
    assert str(ui.macro[-1]) == "ui.f(n=3)"
