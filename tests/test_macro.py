from typing_extensions import Annotated
from magicclass import magicclass, magicmenu, set_options, defaults, do_not_record
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
    defaults["macro-max-history"] = 100

    @magicclass
    class A:
        def f(self): pass
    max_hist = defaults["macro-max-history"]

    ui = A()
    for i in range(max_hist + 10):
        ui.f()
    try:
        assert len(ui.macro) == max_hist
        ui.f()
        assert len(ui.macro) == max_hist
    finally:
        defaults["macro-max-history"] = 100

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

def test_repeat():
    @magicclass
    class A:
        def f(self):
            pass
        def g(self, a: int):
            pass
    ui = A()
    ui.f()
    ui.macro.repeat_method(same_args=True)
    ui.g(2)
    ui.macro.repeat_method(same_args=True)
    assert str(ui.macro[1]) == "ui.f()"
    assert str(ui.macro[2]) == "ui.f()"
    assert str(ui.macro[3]) == "ui.g(a=2)"
    assert str(ui.macro[4]) == "ui.g(a=2)"

def test_mcls_record_arg():
    from magicclass import field
    @magicclass
    class A:
        @magicclass(record=False)
        class B:
            x = field(int)

            def f(self):
                ...
            @magicmenu
            class M:
                x = field(int)
                def f(self):
                    ...
        def g(self):
            ...

    ui = A()
    @ui.B.append
    def new():
        ...
    @ui.B.M.append
    def new():
        ...
    ui.g()
    ui.B.x.value = 5
    ui.B.f()
    ui.B.new()
    ui.B.M.x.value = 5
    ui.B.M.f()
    ui.B.M.new()

    assert len(ui.macro) == 2
    assert str(ui.macro[1]) == "ui.g()"

def test_validator():
    @magicclass
    class A:
        def __init__(self) -> None:
            self._default = 1

        def _set_default(self, value):
            if value is None:
                value = self._default
            return value

        def _copy_value(self, value, args):
            if value is None:
                value = args["x"]
                if value is None:
                    value = -1
            return value

        def f(
            self,
            x: Annotated[int, {"validator": _set_default}] = None,
            y: Annotated[int, {"validator": _copy_value}] = None,
        ):
            self._default  # check instance is bound to self
            return x, y

    ui = A()
    assert (5, 5) == ui.f(5, 5)
    assert (3, 3) == ui.f(3)
    assert (1, -1) == ui.f()
    assert str(ui.macro[1]) == "ui.f(x=5, y=5)"
    assert str(ui.macro[2]) == "ui.f(x=3, y=3)"
    assert str(ui.macro[3]) == "ui.f(x=1, y=-1)"


def test_validator_with_worker():
    from magicclass.utils import thread_worker

    @magicclass
    class A:
        def __init__(self) -> None:
            self._default = 1

        def _set_default(self, value):
            if value is None:
                value = self._default
            return value

        def _copy_value(self, value, args):
            if value is None:
                value = args["x"]
                if value is None:
                    value = -1
            return value

        @thread_worker
        def f(
            self,
            x: Annotated[int, {"validator": _set_default}] = None,
            y: Annotated[int, {"validator": _copy_value}] = None,
        ):
            self._default  # check instance is bound to self
            return x, y

    ui = A()
    assert (5, 5) == ui.f(5, 5)
    assert (3, 3) == ui.f(3)
    assert (1, -1) == ui.f()
    assert str(ui.macro[1]) == "ui.f(x=5, y=5)"
    assert str(ui.macro[2]) == "ui.f(x=3, y=3)"
    assert str(ui.macro[3]) == "ui.f(x=1, y=-1)"

def test_validator_without_record():
    @magicclass
    class A:
        def __init__(self) -> None:
            self._default = 1

        def _set_default(self, value):
            if value is None:
                value = self._default
            return value

        def _copy_value(self, value, args):
            if value is None:
                value = args["x"]
                if value is None:
                    value = -1
            return value

        @do_not_record
        def f(
            self,
            x: Annotated[int, {"validator": _set_default}] = None,
            y: Annotated[int, {"validator": _copy_value}] = None,
        ):
            self._default  # check instance is bound to self
            return x, y

    ui = A()
    assert (5, 5) == ui.f(5, 5)
    assert (3, 3) == ui.f(3)
    assert (1, -1) == ui.f()

def test_validator_with_silencer():
    @magicclass
    class A:
        def __init__(self) -> None:
            self._default = 1

        def _set_default(self, value):
            if value is None:
                value = self._default
            return value

        def _copy_value(self, value, args):
            if value is None:
                value = args["x"]
                if value is None:
                    value = -1
            return value

        @do_not_record(recursive=True)
        def f(
            self,
            x: Annotated[int, {"validator": _set_default}] = None,
            y: Annotated[int, {"validator": _copy_value}] = None,
        ):
            self._default  # check instance is bound to self
            return x, y

    ui = A()
    assert (5, 5) == ui.f(5, 5)
    assert (3, 3) == ui.f(3)
    assert (1, -1) == ui.f()
