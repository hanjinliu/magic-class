===================================
Complicated Settings of FunctionGui
===================================

GUI built by ``@magicgui`` can be customized later.

.. code-block:: python

    from magicgui import magicgui

    @magicgui
    def func(x: int, y: int):
        return x + y

    # connect signals
    @func.x.changed.connect
    def _(val):
        func.y.value = val

    # add widgets
    func.append(...)

Of course, you can do this customization by calling ``get_function_gui`` inside
:meth:`__post_init__`.

.. code-block:: python

    from magicclass import magicclass, get_function_gui

    @magicclass
    class A:
        def __post_init__(self):
            gui = get_function_gui(self.func)
            gui.x.changed.connect(print)

        def func(self, x: int):
            print(x)

But the better solution is to use ``@setup_function_gui`` decorator.

.. code-block:: python

    from magicclass import magicclass, setup_function_gui

    @magicclass
    class A:
        def func(self, x: int):
            print(x)

        @setup_function_gui(func)
        def _setup_func(self, mgui):
            mgui.x.changed.connect(print)
