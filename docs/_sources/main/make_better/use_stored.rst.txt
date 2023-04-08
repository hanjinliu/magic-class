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

Type annotation :class:`Stored[T]` is mapped to :class:`ComboBox` magicgui widget.

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

In principle, you can give **any** types to :class:`Stored`. This feature strongly
enhances the reproducibility of your GUI.

.. code-block:: python

    import pandas as pd

    @magicclass
    class A:
        def read_csv(self, path: Path) -> Stored[pd.DataFrame]:
            return pd.read_csv(path)

        def summarize(self, df: Stored[pd.DataFrame]):
            print(df.describe())

:class:`Stored.Last` type
=========================

If you only want to use the last output, you can use :class:`Stored.Last[T]` type.

.. code-block:: python

    @magicclass
    class A:
        def provide(self, x: int) -> Stored[int]:
            return x + 1  # do some computation

        def receive(self, x: Stored.Last[int]):
            print(x)

Macro will be recorded in the same way.

.. code-block:: python

    var0 = ui.provide(1)
    ui.receive(var0)

Split storages for the same type
================================

Methods with same :class:`Stored` types don't always share the same storage. You can
give a hashable specifier to the second argument of :class:`Stored`.

.. code-block:: python

    @magicclass
    class A:
        def provide_0(self, x: int) -> Stored[int, "a"]:
            return x + 1  # do some computation

        def provide_1(self, x: int) -> Stored[int, "b"]:
            return x + 4  # do some computation

        def receive_0(self, x: Stored[int, "a"]):
            print(x)

        def receive_1(self, x: Stored[int, "b"]):
            print(x)

.. note::

    :class:`Stored.Last` follows the same rule. ``Stored.Last[int, "a"]`` provides the
    last output of ``Stored[int, "a"]``.
