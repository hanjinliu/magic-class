============================================
Validation/Normalization for Macro Recording
============================================

In Python, argument validation and normalization are very easy.

.. code-block:: python

    def func(arg1, arg2, arg3):
        arg1, arg2, arg3 = _normalize_input(arg1, arg2, arg3)
        # do something

However, normalization is always done in the function body, so that the
arguments are not normalized yet when macro expression is created. This
behavior sometimes affects the reproducibility. For example, if you pass
``None`` as the default argument and changed the default behavior later,
recorded macro will change its behavior in the newer version.

.. code-block:: python

    from magicclass import magicclass
    from magicclass.types import Optional

    @magicclass
    class Main:
        # in version 0.1
        def _normalize_i(self, i):
            if i is not None:
                return i
            return 1

        # in version 0.2
        def _normalize_i(self, i):
            if i is not None:
                return i
            return 2

        def f(self, i: Optional[int] = None):
            i = self._normalize_i(i)
            print(i)

    ui = Main()
    ui.f()  # macro is "f(i=None)"

``magic-class`` extends the typing system of ``magicgui`` to support the
"validator" key in ``Annotated`` types. The validator will be called on the
passed argument *before* macro creation.

.. code-block:: python

    @magicclass
    class Main:

        ...

        def f(self, i: Annotated[Optional[int], {"validator": _normalize_i}] = None):
            print(i)

    ui = Main()
    ui.f()  # macro is "f(i=1)" for v0.1 and "f(i=2)" for v0.2

Validators can accept the third argument, where a dictionary of all the arguments
will be passed. This is useful when you want to normalize the arguments based on
other arguments.

.. code-block:: python

    @magicclass
    class Main:
        def _normalize_i(self, i, values):
            if i is not None:
                return i
            return values["j"]

        def f(
            self,
            i: Annotated[Optional[int], {"validator": _normalize_i}] = None,
            j: int = 1,
        ):
            # if i is not given, use j instead
            print(i, j)
