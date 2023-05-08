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

You can define undoable methods using functions from submodule :mod:`magicclass.undo`.

:func:`undo_callback` is a decorator that converts a function into a
callback that can be recognized by magic-classes. Returned callback
will be properly processed so that the GUI operations can be recorded
in the undo stack.

Standard methods
----------------

For standard methods, just return the undo callback.

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

Thread workers
--------------

When you use :doc:`./use_worker`, you'll usually return returned-callbacks, which seems to
collide with the undo callback. In this case, you can return an undo callback from the
returned-callback.

.. code-block:: python

    from magicclass.utils import thread_worker

    @magicclass
    class A:
        @thread_worker
        def long_running_function(self, ...):
            ########################
            #   forward function   #
            ########################

            @undo_callback
            def undo():
                ########################
                #   reverse function   #
                ########################

            @thread_worker.to_callback
            def out():
                ########################
                #   returned-callback  #
                ########################
                return undo
            return out

The Undo Stack
==============

Executed undoable operations are all stored in the "undo stack".
Suppose you've defined two undoable methods :meth:`f`, :meth:`g` and
a non-undoable method :meth:`not_undoable` in magic class ``A``, the
undo stack will change as follow.

.. code-block:: python

                        # Undo list / redo list
    ui = A()            # [], []
    ui.f(x=0)           # [<ui.f(x=0)>], []
    ui.g(y=1)           # [<ui.f(x=0)>, <ui.g(y=1)>], []
    ui.macro.undo()     # [<ui.f(x=0)>], [<ui.g(y=1)>]
    ui.macro.undo()     # [], [<ui.f(x=0)>, <ui.g(y=1)>]
    ui.macro.undo()     # [], [<ui.f(x=0)>, <ui.g(y=1)>] (excessive undo does nothing)
    ui.macro.redo()     # [<ui.f(x=0)>], [<ui.g(y=1)>]
    ui.macro.redo()     # [<ui.f(x=0)>, <ui.g(y=1)>], []
    ui.macro.redo()     # [<ui.f(x=0)>, <ui.g(y=1)>], [] (excessive redo does nothing)
    ui.not_undoable()   # [], [] (non-undoable function call clears the undo stack)

Since undo operation is tightly connected to the macro, non-recordable
methods will not added to undo stack, nor will they clears the undo
stack when get called.

.. code-block:: python

    @magicclass
    class A:
        @do_not_record
        def non_recordable(self): ...

        def undoable(self):
            @undo_callback
            def out():
                ...
            return out
                         # Undo list / redo list
    ui = A()             # [], []
    ui.undoable()        # [<ui.undoable()>], []
    ui.undoable()        # [<ui.undoable()>] * 2, []
    ui.non_recordable()  # [<ui.undoable()>] * 2, []
    ui.undoable()        # [<ui.undoable()>] * 3, []

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
    string is not executable, the redo operation will fail. In following
    example, redo does not work.

    .. code-block:: python

        import numpy as np
        from magicclass import magicclass, set_options, vfield
        from magicclass.undo import undo_callback

        def get_array(*_):
            return np.arange(10)

        @magicclass
        class A:
            array = vfield(str, record=False)

            @set_options(x={"bind": get_array})
            def show_array(self, x):
                old_str = self.array
                self.array = str(x)
                @undo_callback
                def out():
                    self.array = old_str
                return out

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
            def show_array(self, x):
                old_str = self.array
                self.array = str(np.asarray(x))
                @undo_callback
                def out():
                    self.array = old_str
                return out
