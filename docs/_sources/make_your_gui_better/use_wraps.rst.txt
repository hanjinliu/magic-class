==================================
Call Parent Methods from its Child
==================================

When you want to define a function under the parent class while put its push button or action in the child
widget for better widget design, code will look very complicated and will be hard to maintain. This problem
usually happens when you want a menu bar, since menu actions always execute something using the parameters
of the parent and often update its parent.

With class method ``warps``, you can easily connect parent methods to its child while keeping code clean.

Basic Syntax
------------

You have to do is:

1. Define child class
2. Define parent method
3. Define a child method with the same name as that of parent's (not necessary but recommended)
4. Wrap the parent method with ``wraps`` function of the child class.

Following example shows how to call ``set_param`` and ``print_param`` functions from its child class
``Child``.

.. code-block:: python

    from magicclass import magicclass, field

    @magicclass
    class Parent:
        param = 0.1

        @magicclass(layout="horizontal")
        class Child:
            # A frame of buttons
            def set_param(self): ...
            def print_param(self): ...

        # a result widget
        result = field(widget_type="LineEdit", options={"enabled": False})

        @Child.wraps
        def set_param(self, value: float):
            self.param = value

        @Child.wraps
        def print_param(self):
            self.result.value = self.param

    ui = Parent()
    ui.show()

.. image:: images/fig_4-1.png

The wrapped parent method will not appear in the parent widget because they already exist in the
child widget.

.. note::

    Method predefinition in Step 3. is not a must. It is recommended, however, in several reasons:

    1. It plays as an "index" of functions. One can know what functions are implemented in the GUI,
       and in what order they will appear in widgets.

    2. If the widget is composed of nested magic classes and other widgets or fields, the order of
       widgets will not be sorted due to different timing of widget creation.

.. warning::

    In the current version (0.5.21), integer indexing is not safe if a magic class has wrapped
    methods. To access chind widgets, use ``str`` (such as ``ui["X"]``) instead of ``int``
    (such as ``ui[1]``).

Use Template Functions
----------------------

Sometimes you may want to define many functions with same parameter names.

A typical example is ``seaborn``. It has meny plot functions with identical arguments such as ``x``,
``y`` and ``hue``. If you annotate all the arguments, your code will look very "noisy".

``magicclass`` provides a method that can copy annotations from a template function to some target
functions, and this function is integrated in ``wraps`` method (You might have noticed that
``functools.wraps`` does a similar thing. Yes, ``wraps`` method is named after ``functools.wraps``).
``magicclass`` also provides a non-method type ``wraps`` function for the most-parent class.

.. code-block:: python

    from magicclass import magicclass, wraps

    def template(i: int, s: str): pass

    @magicclass
    class Main:
        @magicclass
        class Child:
            def f1(self): ...

        @Child.wraps(template=template)
        def f1(self, i, s): ...

        @wraps(template=template)
        def f2(self, i, s): ...

        @wraps(template=template)
        def f3(self, s): ... # method don't have to take all the arguments that template takes.

    ui = Main()
    ui.show()


Make Copies of a Method
-----------------------

You can use ``copy=True`` option to make a copy of a same method. This option is useful when
you want to call same method from different places, like in menu and toolbar.

In following example, ``func`` method appears in menu ``Menu``, toolbar  ``Tools`` and the
main widget ``Main``.

.. code-block:: python

    from magicclass import magicclass, magicmenu, magictoolbar

    @magicclass
    class Main:
        @magicmenu
        class Menu:
            def func(self): ...

        @magictoolbar
        class Tools:
            def func(self): ...

        @Menu.wraps(copy=True)
        @Tools.wraps(copy=True)
        def func(self):
            """write program here."""

.. image:: images/fig_4-2.png

If push button in ``Main`` is not needed, delete ``copy=True`` from the first decorator.

.. code-block:: python

    # in class Main
    @Menu.wraps(copy=True)
    @Tools.wraps
    def func(self):
        """write program here."""

In this case, even the second ``copy=True`` option can be omitted because you'll never have to wrap
same method twice. Magic classes automatically make copies if a method is already wrapped.

.. code-block:: python

    # in class Main
    @Menu.wraps
    @Tools.wraps
    def func(self):
        """write program here."""

Widget designs can be separetely set via pre-defined methods.

.. code-block:: python

    from magicclass import magicclass, magicmenu, magictoolbar, set_design

    @magicclass
    class Main:
        @magicmenu
        class Menu:
            @set_design(text="func in Menu")
            def func(self): ...

        @magictoolbar
        class Tools:
            @set_design(text="func in Tools")
            def func(self): ...

        @Menu.wraps
        @Tools.wraps
        def func(self):
            """write program here."""

Find Ancestor Widgets
---------------------

If your purpose is just to get the ancestor widget, you can call ``find_ancestor`` method instead.
``self.find_ancestor(X)`` will iteratively search for the widget parent until it reaches an instance
of ``X``.

.. code-block:: python

    @magicclass
    class Main:
        @magicclass
        class A:
            def func(self):
                ancestor = self.find_ancestor(Main)
                # do something on the ancestor widget

In terms of calling parent methods, ``find_ancestor`` works very similar to ``@wraps``. However, there
are pros and cons between ``@wraps`` and ``find_ancestor``.

- You can define child widget class outside the parent widget class.

    .. code-block:: python

        @magicmenu
        class A:
            def func(self):
                ancestor = self.find_ancestor(Main)
                # do something on the ancestor widget

        @magicclass
        class Main:
            A = A

- Recorded macro will be different. In the case of calling ``find_ancestor``,
  macro will be recorded as ``"ui.ChildClass.method(...)"`` while it will be
  ``"ui.method(...)"`` if you used ``@wraps``. In terms of readability,
  usually ``@wraps`` will be better.
