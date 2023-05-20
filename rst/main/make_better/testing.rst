=====================
Testing Magic classes
=====================

.. versionadded:: 0.7.1

:mod:`magicclass.testing` contains several functions to test the magic classes.

.. contents:: Contents
    :local:
    :depth: 1

Testing Function GUI Creation
=============================

All the :class:`FunctionGui` s are built lazily, that is, they are built only
after user clicked the corresponding button. Therefore, the building error
cannot be detected in the "compile" time.

To test if all the :class:`FunctionGui`s can be built successfully, you can
use :meth:`check_function_gui_buildable`.

.. code-block:: python

    from magicclass import magicclass
    from magicclass.testing import check_function_gui_buildable

    @magicclass
    class MyGui:
        def f(self, x):  # x is not annotated, so @magicgui will fail
            ...          # to build a functional GUI.

    ui = MyGui()

    check_function_gui_buildable(ui)  # this will raise an error on "f"

:meth:`check_function_gui_buildable` can also detect inappropriate
:doc:`bind options <use_bind>` and :doc:`choices <use_choices>`.

Testing Docstrings
==================

Magic classes can use the python docstring (``__doc__``) to generate the
tooltips of the corresponding widgets. However, when you renamed some
of the variables, IDE may not rename the docstrings automatically. This
will cause the tooltips not matching the actual variables.

To test if all the docstrings are correct, you can use :meth:`check_tooltip`.

.. code-block:: python

    from magicclass import magicclass
    from magicclass.testing import check_tooltip

    @magicclass
    class MyGui:
        def f(self, x: int):
            """
            ......

            Parameters
            ----------
            y : int         # <---- this should be "x"
                ......
            """

    ui = MyGui()

    check_tooltip(ui)  # wrong "y" will be reported

Testing Preview and Confirmation
================================

:mod:`magic-class` natively supports method :doc:`preview <use_preview>` and
:doc:`confirmation <use_confirm>`. These are again a runtime feature, so they
is hard to be tested.

:class:`FunctionGuiTester` is the class for this purpose.

.. code-block:: python

    from magicclass import magicclass, confirm, impl_preview, vfield
    from magicclass.testing import FunctionGuiTester

    @magicclass
    class MyGui:
        # confirm before run if x is too large
        @confirm(condition="x>100")
        def f(self, x: int):
            for i in range(x):
                print(i)

        # method g has a preview function "_g_preview"
        def g(self, x: int):
            self.result = str(x ** 2)

        @impl_preview(g)
        def _g_preview(self, x: int):
            old = self.result
            self.g(x)  # prerun
            yield
            self.result = old  # cleanup

        result = vfield(str)  # show the result of "g"

    ui = MyGui()
    tester = FunctionGuiTester(ui.f)  # create a tester for function "f"

:meth:`FunctionGuiTester.call` will call the method as if it is called from
GUI, but it will not open the default confirmation dialog (otherwise your test
session will wait for your response). The confirmation callback is temporarily
replaced by a dummy function. You can check if the confirmation is called using
the :attr:`confirm_count` attribute.

.. code-block:: python

    # test if the confirmation works
    tester.call(x=200)
    assert tester.confirm_count == 1

To test preview function, you can use :meth:`FunctionGuiTester.update_parameters`
to update the GUI state and :meth:`FunctionGuiTester.click_preview` to trigger
the preview function.

.. code-block:: python

    tester = FunctionGuiTester(ui.g)  # create a tester for function "g"

    # test if the confirmation works
    tester.update_parameters(x=5)
    assert ui.result == ""  # check preview is not called yet
    tester.click_preview()
    assert ui.result == "25"  # check preview is working
