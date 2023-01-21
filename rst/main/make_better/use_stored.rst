===================================
Store Outputs for the Future Inputs
===================================

When you want to define a set of functions, in which the output of one function
will be used for the input of another function, naively, you'll have to store
the outputs as an attribute.

.. code-block:: python

    @magicclass
    class A:
        def __init__(self):
            self._output = None

        def provide(self, x: int):
            self._output = x + 1  # do some computation
            return self._output

        def receive(self):
            print(self._output)

If you provided ``1``, macro will be recorded as following.

.. code-block:: python

    ui.provide(1)
    ui.receive()

However, changing the internal state is not a good idea and following script should
be more intuitive.

.. code-block:: python

    value = ui.provide(1)
    ui.receive(value)

:class:`Stored` type
====================

:class:`Stored` type is a type annotation for this purpose. :class:`Stored[T]` is
identical to :class:`T` for the type checker, but it stores the past output
annotated with :class:`Stored[T]` for the future inputs annotated with
:class:`Stored[T]`.

.. code-block:: python

    @magicclass
    class A:
        def provide(self, x: int) -> Stored[int]:
            return x + 1  # do some computation

        def receive(self, x: Stored[int]):
            print(x)

And the macro will look like following.

.. code-block:: python

    var0 = ui.provide(1)
    ui.receive(var0)

.. note::

    ``var0`` may vary depending on the order of the functions. The variable names
    are automatically generated based on their IDs.
