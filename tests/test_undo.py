from magicgui import magicgui
from magicclass import magicclass, field, vfield
from magicclass.undo import to_undo

def test_undo_func():
    @magicclass
    class A:
        def __init__(self):
            self._x = 0

        def f(self, x: int):
            old_value = self._x
            self._x = x
            @to_undo
            def undo():
                self._x = old_value
            return undo

    ui = A()
    ui.f(1)
    ui.f(2)
    assert ui._x == 2
    assert len(ui.macro) == 3 and str(ui.macro[-1]) == "ui.f(x=2)"
    ui.macro.undo()
    assert ui._x == 1
    assert len(ui.macro) == 2 and str(ui.macro[-1]) == "ui.f(x=1)"
    ui.macro.undo()
    assert ui._x == 0
    assert len(ui.macro) == 1 and str(ui.macro[-1])
    ui.macro.redo()
    assert ui._x == 1
    assert len(ui.macro) == 2 and str(ui.macro[-1]) == "ui.f(x=1)"
    ui.macro.redo()
    assert ui._x == 2
    assert len(ui.macro) == 3 and str(ui.macro[-1]) == "ui.f(x=2)"

def test_magicgui_undo():
    @magicclass
    class A:
        def __init__(self) -> None:
            self._x = 0

        @magicgui
        def f(self, x: int):
            old_value = self._x
            self._x = x
            @to_undo
            def undo():
                self._x = old_value
            return undo

    ui = A()
    ui[0].x.value = 1
    ui[0].call_button.changed()
    ui[0].x.value = 2
    ui[0].call_button.changed()
    assert ui._x == 2
    assert len(ui.macro) == 3 and str(ui.macro[-1]) == "ui.f(x=2)"
    ui.macro.undo()
    assert ui._x == 1
    assert len(ui.macro) == 2 and str(ui.macro[-1]) == "ui.f(x=1)"
    ui.macro.undo()
    assert ui._x == 0
    assert len(ui.macro) == 1
    ui.macro.redo()
    assert ui._x == 1
    assert len(ui.macro) == 2 and str(ui.macro[-1]) == "ui.f(x=1)"
    ui.macro.redo()
    assert ui._x == 2
    assert len(ui.macro) == 3 and str(ui.macro[-1]) == "ui.f(x=2)"

def test_clear_undo_stack():
    @magicclass
    class A:
        x = vfield(10)

        def undoable(self):
            return to_undo(lambda: None)

        def not_undoable(self):
            pass

    ui = A()
    ui.x = 20
    ui.not_undoable()
    assert len(ui.macro._stack_undo) == 0
    ui.undoable()
    ui.undoable()
    ui.macro.undo()
    assert len(ui.macro._stack_undo) == len(ui.macro._stack_redo) == 1
    ui.not_undoable()
    assert len(ui.macro._stack_undo) == len(ui.macro._stack_redo) == 0
