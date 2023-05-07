===================
Implement Undo/Redo
===================

.. versionadded:: 0.7.0

Undo is important for the user to be able to correct mistakes, but it is
extremely difficult to implement. There are several undo/redo architectures.
In :mod:`magic-class`, an undoable method is defined by a forward function
and a reverse function. When a forward function converts GUI state from A to
B, then the reverse function should do the opposite (B to A).

The undo/redo operations can be executed from the macro instance using
:meth:`ui.macro.undo` and :meth:`ui.macro.redo()`.

.. contents:: Contents
    :local:
    :depth: 1

Basic Syntax
============

There are two ways to define undoable methods using functions from submodule
:mod:`magicclass.undo`.

1. Use the :func:`undo_callback` decorator.

    :func:`undo_callback` is a decorator that converts a function into a
    callback that can be recognized by magic-classes. Returned callback
    will be properly processed so that the GUI operations can be recorded
    in the undo stack.

    .. code-block:: python

        from magicclass import magicclass
        from magicclass.undo import undo_callback

        @magicclass
        class A:
            ...

            def func(self, ...):
                ########################
                #   forward function   #
                ########################
                @undo_callback
                def undo():
                    ########################
                    #   reverse function   #
                    ########################
                return undo

    .. note::

        The reason why we need to define the reverse function inside the
        forward function is that the reverse function usually needs the
        local variables of the forward function to return the GUI state
        to the original.

2. Use the :func:`undoable` decorator.

    :func:`undoable` decorator can do the same thing as :func:`undo_callback`,
    but it uses generator instead of callback function.

    .. code-block:: python

        from magicclass import magicclass
        from magicclass.undo import undoable

        @magicclass
        class A:
            ...

            @undoable
            def func(self, ...):
                ########################
                #   forward function   #
                ########################
                yield
                ########################
                #   reverse function   #
                ########################
                return

An example of undoable setter method is like this:

.. code-block:: python

    from magicclass import magicclass
    from magicclass.undo import undo_callback

    @magicclass
    class A:
        def __init__(self):
            self._x = 0

        def set_x(self, x: int):
            old_state = x
            self._x = x
            @undo_callback
            def undo():
                self._x = old_state
            return undo

How Undo Commands are Managed
=============================

.. code-block:: python

    ui = A()

    ui.func(x=0)  # "ui.func(x=0)" is recorded to the macro instance
                  # and the corresponding undo command is added to
                  # the undo stack

    ui.macro.undo()  # undo command is popped from the undo stack,
                     # executed and added to the redo stack.

    ui.macro.redo()  # redo command (the macro string "ui.func(x=0)")
                     # is popped from the redo stack, evaluated and
                     # added to the undo stack.

    ui.not_undoable()  # undo stack is cleared.

Call Undo/Redo in GUI
=====================

Undo/Redo should be called in GUI in most cases. Many applications map the
key sequence ``Ctrl+Z`` to undo and ``Ctrl+Y`` to redo, or add tool buttons
to do the same things.

In :mod:`magicclass`, you can simply call :meth:`ui.macro.undo` and
:meth:`ui.macro.redo` in the desired place. However, there are some points
that you have to be careful about.

1. Do not macro-record undo/redo methods themselves.

    Recording undo/redo methods will block the undo stack from undo/redo
    execution.

    .. code-block:: python

        from magicclass import do_not_record

        @magicclass
        class A:
            def func(self):
                # do some undoable stuff

            @do_not_record  # use this decorator to avoid recording
            def undo(self):
                self.macro.undo()

            @do_not_record
            def redo(self):
                self.macro.redo()

2. Make sure the recorded macro is executable.

    The redo operation fully relies on the macro string. If the macro
    string is not executable, redoing will fail. In following example,
    redo does not work.

    .. code-block:: python

        import numpy as np
        from magicclass import magicclass, set_options, vfield
        from magicclass.undo import undoable

        def get_array(*_):
            return np.arange(10)

        @magicclass
        class A:
            array = vfield(str, record=False)

            @set_options(x={"bind": get_array})
            @undoable
            def show_array(self, x):
                old_str = self.array
                self.array = str(x)
                yield
                self.array = old_str

    :mod:`macro-kit` does not implement the object-to-string conversion
    for :class:`numpy.ndarray` by default because the array data can
    potentially be very large. To avoid this, you can pass a list to the
    method.

    .. code-block:: python

        ...

        def get_array(*_):
            return list(range(10))

        @magicclass
        class A:
            array = vfield(str, record=False)

            @set_options(x={"bind": get_array})
            @undoable
            def show_array(self, x):
                old_str = self.array
                self.array = str(np.asarray(x))
                yield
                self.array = old_str
