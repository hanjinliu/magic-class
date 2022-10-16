======================
Use functools-like API
======================

.. contents:: Contents
    :local:
    :depth: 2

Partialize Functions and Widgets
================================

``functools.partial`` is a function that takes a function and some arguments to
partialize it. However, whether ``magicgui`` widget should be partialized is another
problem. In ``magicgui``, ``functools.partial`` object does **not** partialize
the widget. It only affects the default value of the parameters.

.. code-block:: python

    def f(i: int, j: int):
        return i + j

    mgui = magicgui(partial(f, j=2))  # mgui still has two widgets corresponding to i and j

Partializing widgets
--------------------

In ``magicclass``, you can use ``partial`` class in ``magicclass.utils`` instead of
``functools.partial``. It basically works in a same way, but also properly partialize
widget options.

.. code-block:: python

    from magicgui import magicgui
    from magicclass.utils import partial

    def func(self, x: int, y: int, z: int):
        print(x, y, z)

    pfunc = partial(func, x=0)
    mgui = magicgui(pfunc)
    mgui.show(True)  # mgui has only two widgets corresponding to y and z

.. note::

    To partialize method, you have to use ``partialmethod`` in ``magicclass.utils``,
    just like when you have to use ``functools.partialmethod``.

    .. code-block:: python

        from magicclass import magicclass
        from magicclass.utils import partialmethod

        @magicclass
        class A:
            def func(self, x: int, y: int, z: int):
                print(x, y, z)

            func_0 = partialmethod(func, x=0)  # use partialmethod!

Example: "open recent"
----------------------

``partial`` is very useful when you want to dynamically create buttons or menu actions that
call a function with some defined arguments. Following example shows how to make a "open
recent" menu.

.. code-block:: python

    from pathlib import Path
    from magicclass import magicclass, magicmenu
    from magicclass.utils import partial

    @magicclass
    class A:
        @magicmenu
        class File:
            def open_file(self, path: Path):
                text = str(path)
                print("Opening:", text)  # do something

                # create a partial function
                pfunc = partial(self.open_file, path=path).set_options(text=text)

                # to avoid adding duplicated menu actions, check if the same action
                # already exists.
                if text not in self.open_recent._text_list():
                    self.open_recent.append(pfunc)

            @magicmenu
            class open_recent:
                # recently opened files will be appended here
                def _text_list(self) -> "list[str]":
                    return [a.text for a in self]

    ui = A()
    ui.show()


Single Dispatching
==================

TODO
