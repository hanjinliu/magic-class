================================
Partialize Functions and Widgets
================================

``functools.partial`` is a function that takes a function and some arguments to
partialize it. However, whether ``magicgui`` widget should be partialized is another
problem. In ``magicgui``, ``functools.partial`` object does **not** partialize
the widget. It only affects the default value of the parameters.

.. code-block:: python

    def f(i: int, j: int):
        return i + j

    mgui = partial(f, j=2)  # mgui still has two widgets corresponding to i and j

Yet, partializing ``magicgui`` widgets are very useful in magic classes. For instance,
if you want to call ``ui.func(x=0, y=1, z=2)`` from a partialized method, like
``ui.func_x_is_0(y=1, z=2)``, the macro should be recorded as ``ui.func(x=0, y=1, z=2)``
for simplicity.

Partializing widgets
--------------------

In ``magicclass``, you can use ``partial`` class in ``magicclass.utils`` instead of
``functools.partial``. It basically works in a same way, but also properly partialize
widget options.

.. code-block:: python

    from magicclass import magicclass
    from magicclass.utils import partial

    @magicclass
    class A:
        def func(self, x: int, y: int, z: int):
            print(x, y, z)

    ui = A()
    func_x_is_0 = partial(ui.func, x=0)


Example: "open recent"
----------------------

.. code-block:: python

    from pathlib import Path
    from magicclass import magicclass, magicmenu
    from magicclass.utils import partial

    @magicclass
    class A:
        @magicmenu
        class File:
            def __init__(self):
                self._history = []

            def open_file(self, path: Path):
                path = Path(path)
                print("Opening:", path)

                # To avoid appending the same history twice, check if the path
                # is already in the history.
                if path not in self._history:
                    pfunc = partial(self.open_file, path=path)
                    self.append(pfunc)
                    self._history.append(path)

            @magicmenu
            class open_recent:
                pass  # recently opened files will be appended here
