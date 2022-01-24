from magicclass import magicclass, set_options
from enum import Enum
from pathlib import Path
from datetime import datetime, date, time
from unittest.mock import MagicMock

class X(Enum):
    a = 1
    b = 2

def test_macro_rerun():
    mock = MagicMock()
    
    @magicclass(error_mode="stderr")
    class A:
        def f1(self, x: X):
            try:
                x = X(x)  # this is the formal way to use Enum
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