from magicclass import magicclass, magicmenu, magictoolbar, bind_key
from qtpy.QtCore import Qt
from magicclass._app import get_app
from unittest.mock import MagicMock

def test_basic_keybindings(qtbot):
    app = get_app()
    mock = MagicMock()
    from qtpy.QtTest import QTest

    @magicclass
    class A:
        @magicclass
        class B:
            @bind_key("Ctrl-T")
            def f(self): pass
            @bind_key("Ctrl-U")
            def _g(self):
                mock()

        @magicmenu
        class C:
            @bind_key("Ctrl-P")
            def f(self): pass

        @magictoolbar
        class D:
            @bind_key("Ctrl-R")
            def f(self): pass
            @bind_key("Ctrl-S")
            def _g(self):
                mock()

        @bind_key("Ctrl-A")
        def f(self): pass
        @bind_key("Ctrl-B")
        def _g(self):
            mock()

    ui = A()
    with qtbot.waitExposed(ui.native, timeout=500):
        ui.show(False)
    app.processEvents()
    QTest.keyClick(ui.native, Qt.Key_A, Qt.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    assert str(ui.macro[-1]) == "ui.f()"
    mock.assert_not_called()
    QTest.keyClick(ui.native, Qt.Key_B, Qt.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    mock.assert_called_once()
    mock.reset_mock()

    QTest.keyClick(ui.native, Qt.Key_T, Qt.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    assert str(ui.macro[-1]) == "ui.B.f()"
    mock.assert_not_called()
    QTest.keyClick(ui.native, Qt.Key_U, Qt.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    mock.assert_called_once()
    mock.reset_mock()

    QTest.keyClick(ui.native, Qt.Key_P, Qt.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    assert str(ui.macro[-1]) == "ui.C.f()"

    QTest.keyClick(ui.native, Qt.Key_R, Qt.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    assert str(ui.macro[-1]) == "ui.D.f()"
    mock.assert_not_called()
    QTest.keyClick(ui.native, Qt.Key_S, Qt.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    mock.assert_called_once()
    mock.reset_mock()
