from magicclass import magicclass, bind_key
from qtpy.QtGui import QKeyEvent
from qtpy.QtCore import QCoreApplication, Qt, QEvent

# auto FOCUSOBJ = QGuiApplication::focusObject();
# QString keyStr(QKeySequence(key).toString()); // key is int with keycode
# QKeyEvent pressEvent = QKeyEvent(QEvent::KeyPress, key, Qt::NoModifier, keyStr);
# QKeyEvent releaseEvent = QKeyEvent(QEvent::KeyRelease, key, Qt::NoModifier);
# QCoreApplication::sendEvent(FOCUSOBJ, &pressEvent);
# QCoreApplication::sendEvent(FOCUSOBJ, &releaseEvent);

def Ctrl_A(ui):
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_A, Qt.Ctrl)
    QCoreApplication.postEvent(ui.native, event)
    

def test_basic_keybindings():
    @magicclass
    class A:
        @bind_key("Ctrl-A")
        def f(self): pass
        @bind_key("Ctrl-B")
        def _g(self): pass
    
    ui = A()
    Ctrl_A(ui)
    ui.macro