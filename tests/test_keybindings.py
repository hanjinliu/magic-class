# from magicclass import magicclass, bind_key
# from qtpy.QtCore import Qt
# from magicclass._app import get_app

# def test_basic_keybindings():
#     app = get_app()
#     from qtpy.QtTest import QTest

#     @magicclass
#     class A:
#         @bind_key("Ctrl-A")
#         def f(self): pass
#         @bind_key("Ctrl-B")
#         def _g(self): pass

#     ui = A()
#     ui.show(False)
#     QTest.keyClick(app.activeWindow(), Qt.Key_A, Qt.ControlModifier)

#     assert str(ui.macro[-1]) == "ui.f()"
