from magicclass import magicclass, magicmenu

# PushButtonPlus.running should be True only if it is called from GUI.

def test_running():
    @magicclass
    class A:
        def __init__(self):
            self.last_running = None

        def func(self):
            self.last_running = self["func"].running

    ui = A()
    ui.func()
    assert ui.last_running == False
    ui["func"].changed()
    assert ui.last_running == True


def test_wrapped_running():
    @magicclass
    class A:
        @magicmenu
        class B:
            def func(self): ...

        def __init__(self):
            self.last_running = None

        @B.wraps
        def func(self):
            self.last_running = self["func"].running

    ui = A()
    ui.func()
    assert ui.last_running == False
    ui.B["func"].changed()
    assert ui.last_running == True
