===========================
Binding Values to Arguments
===========================

In ``magicgui``, you can bind values to function arguments instead of annotating them.
The ``"bind"`` option is useful when the parameter is determined programatically, such
as time, random value or parameters in other widgets.

.. code-block:: python

    from magicgui import magicgui
    import time

    def get_time(w):
        return time.time()

    @magicgui(t={"bind": get_time})
    def func(t):
        print(t)

Same grammar also works in magic-class. Furthermore, there are more options here.
Since many parameters will be obtained from widgets that are created by ``field`` function,
or retrieved by some get-value instance methods, magic-class is desined in a way that
also works with these options.

Use Methods
-----------

If a method defined in a class is given as a bind option, magic-class calls it as an instance
method every time the value is accessed. A bind option should be set using ``set_options`` wrapper
as usual.

.. code-block:: python

    from magicclass import magicclass, set_options
    import time

    @magicclass
    class Main:
        def __post_init__(self):
            self.t_start = time.time()

        def _get_time(self, w):
            # To avoid being added as a widget, make this method private.
            return time.time() - self.t_start

        @set_options(t={"bind": _get_time})
        def print_time(self, t):
            print(t)

One of the advantages of this method is reproducibility of macro. In the example above, values to
be returned by ``_get_time`` will differ a lot depending on whether you are manually calling
function on GUI or executing as a Python script. When parameters are bound from methods, the returned
values will be recorded as a macro so that results are always the same.

.. code-block:: python

    ui = Main()
    ui.show()
    # click button once
    print(ui.macro)

.. code-block::

    ui = Main()
    ui.print_time(2.3758413791656494)

.. tip::

    The bind option is very useful to make macro-recordable napari plugin widgets. If a function need
    some information from the viewer, you can record the viewer's state.

    .. code-block:: python

        @magicclass
        class Plugin:
            def _get_last_shapes(self, w):
                viewer = self.parent_viewer
                # ndarray will not be recorded as concrete values by default, to avoid recording very
                # large arrays. You have to convert it to a list, or use "register_type" function in
                # "magicclass.macro".
                return viewer.layers["Shapes"].data[-1].tolist()

            @set_options(rectangle={"bind": _get_last_shapes})
            def read_coordinates(self, rectangle):
                ...

Use Fields
----------

Many GUIs let users to set global parameters by widgets, and use these parameters in other functions.
However, if you want to run the function from the script, you don't want to do this like:

.. code-block:: python

    ui.a.value = 1
    ui.b.value = 2
    ui.call()

Most programmers should prefer:

.. code-block:: python

    ui.call(1, 2)

An option to solve this problem is to define getter methods like ``get_a_value`` and ``get_b_value``
and bind them to the ``call`` method. But there is a way that is much simpler: bind field objects
directly (See also :doc:`use_field`).

.. code-block:: python

    from magicclass import magicclass, set_options, field

    @magicclass
    class Add:
        a = field(float)
        b = field(float)

        @set_options(x0={"bind": a}, x1={"bind": b})
        def call(self, x0, x1):
            print(x0 + x1)

In this example, values ``x0`` and ``x1`` is determined by refering to ``a.value`` and ``b.value``.

Use Annotated Type
------------------

``magicgui`` supports ``typing_extensions``'s ``Annotated`` type, which makes GUI configurations much
clearer.

.. code-block:: python

    from typing_extensions import Annotated

    @magicgui
    def func(i: Annotated[int, {"max": 10}]):
        ...

In magic-class, you can also use ``Annotated`` for bind options. But when you bind field to parameters
you can use ``Bound`` type instead because all the options are already defined in the field and options
are useless when bind option is specified.

.. code-block:: python

    from magicclass import magicclass, field
    from magicclass.types import Bound

    @magicclass
    class Add:
        a = field(float)
        b = field(float)

        def call(self, x0: Bound[a], x1: Bound[b]):
            print(x0 + x1)
