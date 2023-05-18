from magicclass import magicclass, abstractapi, vfield
from magicclass.testing import assert_function_gui_buildable

def test_fgui():
    @magicclass
    class A:
        x = vfield(1)

        @magicclass
        class B:
            def f(self, i: int):
                ...
            bf = abstractapi()

        def g(self):
            ...
        @B.wraps
        def bf(self):
            ...

    ui = A()

    assert_function_gui_buildable(ui)
    assert ui["g"].mgui is not None
    assert ui["bf"].mgui is not None
    assert ui.B["f"].mgui is not None
