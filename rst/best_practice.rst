=============
Best Practice
=============

Here's some tips that will be useful for better GUI design.

.. contents:: Contents
    :local:
    :depth: 2

Shared Input Parameters
=======================

If you want to control input parameters outside each ``magicgui`` widget, the example
below is the mose naive implementation.

.. code-block:: python

    from magicclass import magicclass, magicmenu, field

    @magicclass
    class Main:
        @magicmenu
        class Menu:
            def add(self): ...
            def sub(self): ...

        a = field(float)
        b = field(float)
        result = field(float, record=False)

        @Menu.wraps
        def add(self):
            """Add two values"""
            self.result.value = self.a.value + self.b.value

        @Menu.wraps
        def sub(self):
            """Subtract two values"""
            self.result.value = self.a.value - self.b.value

However, after you calculated "4.0 + 2.0" and "6.0 - 3.0", macro will be recorded like

.. code-block:: python

    ui.a.value = 4.0
    ui.b.value = 2.0
    ui.add()
    ui.a.value = 6.0
    ui.b.value = 3.0
    ui.sub()

This is perfectly reproducible but is not user friendly. If users want to run functions
programmatically, they'll prefer styles like ``add(1, 2)``. Unfriendliness is more obvious
when you changed the values of ``a`` and ``b`` alternately many times before adding them
and saw its macro recorded like

.. code-block:: python

    ui.a.value = 3.0
    ui.b.value = 1.0
    ui.a.value = 6.0
    ui.b.value = 2.0
    ui.a.value = 9.0
    ui.b.value = 3.0
    ui.add()

To avoid this, you can use the "bind" option (see :doc:`use_bind`).

.. code-block:: python

    from magicclass import magicclass, magicmenu, field
    from magicclass.types import Bound

    @magicclass
    class Main:
        @magicmenu
        class Menu:
            def add(self): ...
            def sub(self): ...

        a = field(float, record=False)  # <- don't record
        b = field(float, record=False)  # <- don't record
        result = field(float, record=False)

        @Menu.wraps
        def add(self, a: Bound[a], b: Bound[b]):  # <- use Bound
            """Add two values"""
            self.result.value = a + b

        @Menu.wraps
        def sub(self, a: Bound[a], b: Bound[b]):  # <- use Bound
            """Subtract two values"""
            self.result.value = a - b

Widget created by this code works completely identical to the previous one. Also, macro
will be recorded in a better way.

.. code-block:: python

    ui.add(a=4.0, b=2.0)
    ui.sub(a=6.0, b=3.0)
