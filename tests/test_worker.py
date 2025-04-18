import pytest
from magicclass import magicclass, magicmenu, set_options, do_not_record, vfield, get_function_gui
from magicclass.types import Bound
from magicclass.utils import thread_worker
import time
from unittest.mock import MagicMock
from pytestqt.qtbot import QtBot

def test_worker_basic():
    mock = MagicMock()
    @magicclass
    class A:
        @thread_worker
        def f(self):
            """doc"""
            time.sleep(0.01)

        @f.returned.connect
        def on_return(self, _=None):
            mock()

    ui = A()
    assert ui["f"].tooltip == "doc"
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
    assert get_function_gui(ui.f).a.widget_type == "LogSlider"
    assert get_function_gui(ui.g).a.widget_type == "LogSlider"

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
    assert not get_function_gui(ui.f).a.visible
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
    assert get_function_gui(ui.f).a.choices == (0, 1)
    assert get_function_gui(ui.g).a.choices == (0, 1)
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

def test_with_progress():
    @magicclass
    class A:
        # a progress bar widget is newly created
        @thread_worker.with_progress(desc="test")
        def f(self):
            time.sleep(0.2)

    @magicclass
    class B:
        @thread_worker.with_progress(desc="test")
        def f(self):
            time.sleep(0.2)

    a = A()
    a.f()
    b = B()
    b.f()

def test_callable_desc():
    @magicclass
    class A:
        @thread_worker.with_progress(desc=lambda i, s: f"test {i}, {s}")
        def f(self, i: int, s: str):
            pass

        @thread_worker.with_progress(desc=lambda i: f"test {i}")
        def g(self, i: int, s: str):
            pass

    a = A()
    a.f(1, "a")
    a.g(1, "a")

def test_progress_desc_in_callback():
    @magicclass
    class A:
        @thread_worker.with_progress()
        def f(self, i: int):
            for i in range(3):
                time.sleep(0.01)
                yield thread_worker.description(f"test {i}")
                time.sleep(0.01)
            return thread_worker.callback(lambda: 0).with_desc("test finished")

    a = A()
    a.f(1)

def test_error(qtbot: QtBot):
    @magicclass(error_mode="stderr")
    class A:
        x = vfield(int)
        @thread_worker
        def f(self, n: int = 3):
            if n > 10:
                raise ValueError

        def g(self):
            self.f(20)
            # to check self.f(20) actually raises an error
            self.x = 100

    ui = A()
    ui.f(3)
    assert str(ui.macro[-1]) == "ui.f(n=3)"
    with pytest.raises(ValueError):
        ui.g()
    assert str(ui.macro[-1]) == "ui.f(n=3)"
    assert ui.x < 100

def test_callback():
    @magicclass
    class A:
        def __init__(self):
            self._func_returned = []
            self._gen_yielded = []

        @thread_worker
        def func(self):
            local = 0

            @thread_worker.callback
            def _returned():
                self._func_returned.append(local)
                self.dummy()
            return _returned

        @thread_worker
        def gen(self):
            @thread_worker.callback
            def _yielded():
                self._gen_yielded.append(t)
                self.dummy()
            t = 0
            for _ in range(10):
                yield _yielded
                t += 1

        def dummy(self):
            pass

    ui = A()
    ui.func()
    assert ui._func_returned == [0]
    assert "dummy" not in str(ui.macro)
    ui.gen()
    assert ui._gen_yielded == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert "dummy" not in str(ui.macro)

def test_callback_partial():
    @magicclass
    class A:
        def __init__(self):
            self._gen_yielded = []

        @thread_worker
        def gen(self):
            t = 0
            for _ in range(10):
                yield self._callback.with_args(t)
                t += 1

        @thread_worker.callback
        def _callback(self, x):
            self._gen_yielded.append(x)

    ui = A()
    ui.gen()
    assert ui._gen_yielded == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

def test_nested_worker_macro():
    mock1 = MagicMock()
    mock2 = MagicMock()

    @magicclass
    class A:
        @thread_worker.with_progress(desc="f1")
        def f1(self):
            mock1("f1")

        @thread_worker.with_progress(desc="f1")
        def f2(self):
            mock2("f2")

        @thread_worker.with_progress(desc="f1")
        def f12(self):
            self.f1()
            self.f2()

        def g12(self):
            self.f1()
            self.f2()

    ui = A()
    with thread_worker.no_progress_mode():
        ui.f12()
    mock1.assert_called_with("f1")
    mock2.assert_called_with("f2")
    assert len(ui.macro) == 2
    assert str(ui.macro[-1]) == "ui.f12()"
    mock1.reset_mock()
    mock2.reset_mock()
    ui.g12()
    mock1.assert_called_with("f1")
    mock2.assert_called_with("f2")
    assert len(ui.macro) == 3
    assert str(ui.macro[-1]) == "ui.g12()"
