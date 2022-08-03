===========================
Add Preview Functionalities
===========================

It is a very usual case when you want to preview something before actually running a
function. Suppose in your GUI you implemented a function that can load a csv file and
summarize its contents, you may want to open the csv file and see if you chose the
correct file.

The preview functionality is, however, unexpectedly hard to be implemented in ``magicgui``
or ``magic-class``.

- If they are implemented in separate buttons, say in button "summarize csv" and
  "preview csv", users have to synchronize all the input arguments between these
  two widgets.
- If they are implemented in a same button, you have to add an additional button in the
  bottom of the ``FunctionGui``. This is not simple and hard to maintain.

In ``magic-class``, ``mark_preview`` decorator is very useful for this purpose. You can
define a preview function and directly integrate it into another function easily.

Basic Usage
-----------

.. code-block:: python

    @mark_preview(f)
    def _f_prev(self, xxx):
        ...

will define a previewer ``_f_prev`` for function ``f``. Arguments of ``_f_prev`` must be
composed of those in ``f``. The ``_f_prev`` can be called from the ``FunctionGui``
created by ``f``, as a preview button above the call button.

.. code-block:: python

    from pathlib import Path
    import pandas as pd
    from magicgui.widgets import Table  # for preview
    from magicclass import magicclass, mark_preview

    @magicclass
    class A:
        def summarize_csv(self, path: Path):
            df = pd.read_csv(path)
            print(df.agg([np.mean, np.std]))  # print summary

        @mark_preview(summarize_csv)
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

        @mark_preview(calc_csv)
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

        @mark_preview(summarize_csv)
        @mark_preview(calc_csv)
        @mark_preview(plot_csv, text="preview CSV")
        def _preview_csv(self, path):  # "param" is not needed here
            df = pd.read_csv(path)
            Table(value=df).show()
