============
Add Tooltips
============

Adding tooltips is important for usability. If you are going to add all the tooltip
naively, you will have to set ``tooltip`` property for every widget.

.. code-block:: python

    @magicclass
    class A:
        ...

    ui = A()
    ui["widget-1"].tooltip = "tooltip for widget-1"
    ui["widget-2"].tooltip = "tooltip for widget-2"
    # ... and so on

However, this kind of documentation is not optimal. ``magic-class`` is designed to
avoid GUI-specific lines to make code clean. This chapter shows how to provide
tooltips in magic-classes in a tidy way.

Add tooltips to buttons and menus
---------------------------------

As explained in previous chapters, methods are converted into buttons in classes
decorated with ``@magicclass`` and into menus when ``@magicmenu`` or
``@magiccontext`` are used. Following ``magicgui`` tooltip generation procedure,
function docstrings are very useful for adding tooltips to the buttons and the
widgets appear in the pop-up function GUI. In the example below:

.. code-block:: python

    from magicclass import magicclass

    @magicclass
    class A:
        def f(self, x: int):
            """
            Description of the function.

            Parameters
            ----------
            x : int
                The first parameter.
            """

"Description of the function." will be interpreted as a tooltip for button "f"
and "The first parameter." will be added as a tooltip to the ``SpinBox`` widget
that will appear when the button "f" is clicked.

A benefit of adding tooltips in this way is that you don't have to do more than
documenting a Python code. What's more, these tooltips are compatible with
auto-documentation using ``sphinx``.

Add tooltips to classes
-----------------------

When magic-classes are nested, you may want to add tooltips to child widgets.
This time, class docstrings will be used for the purpose.

.. code-block:: python

    from magicclass import magicclass

    @magicclass
    class A:
        """Description of A."""

        @magicclass
        class B:
            """Description of B."""


Add tooltips to fields
----------------------

Another important component of magic-classes are fields. In a naive way, you'll
have to set ``"tooltip"`` options for every field.

.. code-block:: python

    from magicclass import magicclass, vfield

    @magicclass
    class A:
        x = vfield(int, options={"tooltip": "Description of what x is."})
        y = vfield(str, options={"tooltip": "Description of what y is."})

Again, this can also be substituted with docstrings of class itself.

.. code-block:: python

    from magicclass import magicclass, vfield

    @magicclass
    class A:
        """
        Description of this class.

        Attributes
        ----------
        x : int
            Description of what x is.
        y : int
            Description of what y is.
        """
        x = vfield(int)
        y = vfield(str)

Note that "Attributes" section is used here because fields are class
attributes.
