from magicclass import magicclass, magicmenu, set_options, defaults, redo
from enum import Enum
from pathlib import Path
from datetime import datetime, date, time
from unittest.mock import MagicMock


class X(Enum):
    a = 1
    b = 2

class Y(Enum):
    t = "\t"
    n = "\n"

def test_macro_rerun():
    mock = MagicMock()

    @magicclass(error_mode="stderr")
    class A:
        def f0(self, x: X):
            try:
                x = X(x)  # this is the formal way to use Enum
            except Exception:
                mock()

        def f1(self, y: Y):
            try:
                y = Y(y)  # this is the formal way to use Enum
            except Exception:
                mock()

        @set_options(x={"choices": [2, 3]},
                     y={"choices": ["a", "b"]})
        def f2(self, x, y):
            if not isinstance(x, int):
                mock()

            if not isinstance(y, str):
                mock()

        def f3(self, dt: datetime, d: date, t: time):
            try:
                dt.strftime("")
                d.strftime("")
                t.strftime("")
            except Exception:
                mock()

        def f4(self, path: Path, a=1):
            str(path)  # this is the formal way to use Path

    ui = A()
    ui["f0"].changed()
    ui["f0"].mgui[-1].changed()
    ui["f1"].changed()
    ui["f1"].mgui[-1].changed()
    ui["f2"].changed()
    ui["f2"].mgui[-1].changed()
    ui["f3"].changed()
    ui["f3"].mgui[-1].changed()
    ui["f4"].changed()
    ui["f4"].mgui[-1].changed()

    mock.assert_not_called()

    ui.macro.widget.execute_lines(0)
    mock.assert_not_called()
    ui.macro.widget.execute_lines(1)
    mock.assert_not_called()
    ui.macro.widget.execute_lines(2)
    mock.assert_not_called()
    ui.macro.widget.execute_lines(3)
    mock.assert_not_called()
    ui.macro.widget.execute_lines(4)
    mock.assert_not_called()


def test_blocked():
    @magicclass
    class A:
        def f(self, a: int = 1):
            self._a = a
        def g(self):
            return self.f(0)

    ui = A()
    ui["f"].changed()
    ui["f"].mgui[-1].changed()
    assert ui._a == 1
    ui["g"].changed()
    assert ui._a == 0
    ui.f(2)
    assert ui._a == 2
    ui.g()
    assert ui._a == 0
    assert str(ui.macro[1]) == "ui.f(a=1)"
    assert str(ui.macro[2]) == "ui.g()"
    assert str(ui.macro[3]) == "ui.f(a=2)"
    assert str(ui.macro[4]) == "ui.g()"

def test_max_history():
    @magicclass
    class A:
        def f(self): pass
    max_hist = defaults["macro-max-history"]
    ui = A()
    for i in range(max_hist + 10):
        ui.f()
    assert len(ui.macro) == max_hist
    ui.f()
    assert len(ui.macro) == max_hist

def test_init():
    """test macro is blocked during __init__ and __post_init__"""
    @magicclass
    class A:
        @magicmenu
        class Menu:
            def __init__(self):
                self.f()
            def __post_init__(self):
                self.f()
            def f(self): pass

        def __init__(self):
            self.f()
        def __post_init__(self):
            self.f()
        def f(self): pass

    ui = A()
    assert len(ui.macro) == 1

def test_redo():
    @magicclass
    class A:
        def f(self):
            pass
        def g(self, a: int):
            pass
    ui = A()
    ui.f()
    redo(ui)
    ui.g(2)
    redo(ui)
    assert str(ui.macro[1]) == "ui.f()"
    assert str(ui.macro[2]) == "ui.f()"
    assert str(ui.macro[3]) == "ui.g(a=2)"
    assert str(ui.macro[4]) == "ui.g(a=2)"
