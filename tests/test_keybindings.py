from magicclass import magicclass, magicmenu, magictoolbar, bind_key
from qtpy.QtCore import Qt
from magicclass._app import get_app
from unittest.mock import MagicMock
from pytestqt.qtbot import QtBot

def test_basic_keybindings(qtbot: QtBot):
    mock = MagicMock()
    app = get_app()
    @magicclass
    class A:
        @magicclass
        class B:
            @bind_key("Ctrl-T")
            def f(self): pass
            @bind_key("Ctrl+U")
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
        @bind_key("Ctrl+B")
        def _g(self):
            mock()

    ui = A()
    with qtbot.waitExposed(ui.native, timeout=500):
        ui.show(False)
    qtbot.addWidget(ui.native)
    app.processEvents()
    qtbot.keyClick(ui.native, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    assert str(ui.macro[-1]) == "ui.f()"
    mock.assert_not_called()
    qtbot.keyClick(ui.native, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    mock.assert_called_once()
    mock.reset_mock()

    qtbot.keyClick(ui.native, Qt.Key.Key_T, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    assert str(ui.macro[-1]) == "ui.B.f()"
    mock.assert_not_called()
    qtbot.keyClick(ui.native, Qt.Key.Key_U, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    mock.assert_called_once()
    mock.reset_mock()

    qtbot.keyClick(ui.native, Qt.Key.Key_P, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    assert str(ui.macro[-1]) == "ui.C.f()"

    qtbot.keyClick(ui.native, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    assert str(ui.macro[-1]) == "ui.D.f()"
    mock.assert_not_called()
    qtbot.keyClick(ui.native, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    mock.assert_called_once()
    mock.reset_mock()
    ui.close()

def test_key_combo(qtbot: QtBot):
    mock = MagicMock()
    app = get_app()
    @magicclass
    class A:
        @bind_key("Ctrl+K, Ctrl+A")
        def f(self):
            mock()

    ui = A()
    with qtbot.waitExposed(ui.native, timeout=500):
        ui.show(False)
    qtbot.addWidget(ui.native)
    app.processEvents()
    qtbot.keyClick(ui.native, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    mock.assert_not_called()
    qtbot.keyClick(ui.native, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    qtbot.wait(400)
    mock.assert_called_once()
