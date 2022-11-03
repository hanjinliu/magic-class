===========================
Add Preview Functionalities
===========================

It is a very usual case when you want to preview something before actually running a
function.

1. Suppose in your GUI you implemented a function that can load a csv file and
   summarize its contents, you may want to open the csv file and see if you chose the
   correct file.
2. Suppose you want to process a dataset in-place, you may want to add a "preview"
   checkbox so that you can search for the proper parameters (imagine Gaussian filter
   function in other softwares).

The preview functionality is, however, unexpectedly hard to be implemented in ``magicgui``
or ``magic-class``.

- If they are implemented in separate buttons, say in button "summarize csv" and
  "preview csv", users have to synchronize all the input arguments between these
  two widgets.
- If they are implemented in a same widget, you have to add an additional button in the
  bottom of the ``FunctionGui``. This is not simple and hard to maintain.
- In the case of 2, you'll have to properly connect signals such as "turn on preview",
  "turn off preview" and "restore the original state", which is massive.

In ``magic-class``, ``impl_preview`` decorator is very useful for this purpose. You can
define a preview function and directly integrate it into another function easily.

1. Preview a File
=================

.. code-block:: python

    @impl_preview(f)
    def _f_prev(self, xxx):
        ...

will define a previewer ``_f_prev`` for function ``f``. Arguments of ``_f_prev`` must be
composed of those in ``f``. The ``_f_prev`` can be called from the ``FunctionGui``
created by ``f``, as a preview button above the call button.

.. code-block:: python

    from pathlib import Path
    import pandas as pd
    from magicgui.widgets import Table  # for preview
    from magicclass import magicclass, impl_preview

    @magicclass
    class A:
        def summarize_csv(self, path: Path):
            df = pd.read_csv(path)
            print(df.agg([np.mean, np.std]))  # print summary

        @impl_preview(summarize_csv)
        def _preview_csv(self, path):
            df = pd.read_csv(path)
            Table(value=df).show()  # open table widget as the preview

Previewer don't have to accept all the arguments. Suppose you defined a function
``calc_something`` that calculate something using a data frame and a input parameter
like ``calc_something(df, param)``, the ``param`` in not needed for preview.

.. code-block:: python

    @magicclass
    class A:
        def calc_csv(self, path: Path, param: float):
            df = pd.read_csv(path)
            result = calc_something(df, param)
            print(result)

        @impl_preview(calc_csv)
        def _preview_csv(self, path):  # "param" is not needed here
            df = pd.read_csv(path)
            Table(value=df).show()

You can mark the same function as a previewer for multiple functions. You can also set
the text of preview button using ``text=...`` argument.

.. code-block:: python

    @magicclass
    class A:
        def summarize_csv(self, path: Path):
            df = pd.read_csv(path)
            print(df.agg([np.mean, np.std]))

        def calc_csv(self, path: Path, param: float):
            df = pd.read_csv(path)
            result = calc_something(df, param)
            print(result)

        def plot_csv(self, path: Path):
            df = pd.read_csv(path)
            df.plot()

        @impl_preview(summarize_csv)
        @impl_preview(calc_csv)
        @impl_preview(plot_csv, text="preview CSV")
        def _preview_csv(self, path):  # "param" is not needed here
            df = pd.read_csv(path)
            Table(value=df).show()

2. Prerun a Function
====================

This is essentially same as 1, except that the preview function will update some parts
of the GUI. Following example shows an incomplete implementation of a previewable
Gaussian filtering.

.. code-block:: python

    from magicclass import magicclass, impl_preview, vfield
    from magicgui.widgets import Image
    from scipy import ndimage as ndi

    @magicclass
    class A:
        img = vfield(Image)

        def __post_init__(self):
            # sample image
            self.img = np.random.random((100, 100))
            self["img"].min_width = 100
            self["img"].min_height = 100

        def gaussian_filter(self, sigma: float = 1.0):
            """Run Gaussian filter inplace"""
            self.img = ndi.gaussian_filter(self.img, sigma)

        @impl_preview(gaussian_filter)
        def _prerun(self, sigma):
            self.gaussian_filter(sigma)

    ui = A()
    ui.show()

The problem here is that the preview function :meth:`_prerun` updates the GUI state so
the second preview and the actual run are affected by the previous previews.

Functions wrapped by :meth:`impl_preview` has an additional attribute :meth:`during_preview`,
which defines a context manager for storing/restoring GUI state.

.. code-block:: python

    @magicclass
    class A:
        ...

        @impl_preview(gaussian_filter)
        def _prerun(self, sigma):
            self.gaussian_filter(sigma)

        @_prerun.during_preview
        def _prev_context(self, sigma):
            original = self.img  # store current image
            yield  # prerun called here
            self.img = original  # restore

Auto call
---------

In the example above, it's nicer to auto-call the preview function. :meth:`impl_preview`
has an option ``auto_call=True`` to implement this.

.. code-block:: python

    @magicclass
    class A:
        ...

        @impl_preview(gaussian_filter, auto_call=True)
        def _prerun(self, sigma):
            self.gaussian_filter(sigma)

        @_prerun.during_preview
        def _prev_context(self, sigma):
            original = self.img  # store current image
            yield  # prerun called here
            self.img = original  # restore

In the auto-call mode, a checkbox (instead of an additional button) will be added to the
``FunctionGui`` widget. Preview will be auto-called if the checkbox in checked.

Use function itself as the preview
----------------------------------

As in this example, preview function is usually the same as the target function.
:meth:`impl_preview` can wrap the target function itself if the first argument is not given.

.. code-block:: python

    from magicclass import magicclass, impl_preview, vfield
    from magicgui.widgets import Image
    from scipy import ndimage as ndi

    @magicclass
    class A:
        img = vfield(Image)

        def __post_init__(self):
            # sample image
            self.img = np.random.random((100, 100))
            self["img"].min_width = 100
            self["img"].min_height = 100

        @impl_preview(auto_call=True)  # use gaussian_function as the preview of itself
        def gaussian_filter(self, sigma: float = 1.0):
            """Run Gaussian filter inplace"""
            self.img = ndi.gaussian_filter(self.img, sigma)

        @_prerun.during_preview
        def _prev_context(self, sigma):
            original = self.img
            yield
            self.img = original

    ui = A()
    ui.show()

.. note::

    if :meth:`impl_preview` decorator takes no arguments, it should be

    .. code-block:: python

        @impl_preview()
        def gaussian_filter(self, sigma: float = 1.0):
            ...

    Do not forget the parentheses.
