====================
Container Variations
====================

Use Other Qt Widgets as Container
---------------------------------

In ``magic-class``, many Qt widget variations are available in a same API as ``magicgui``'s ``Container``.
You can use them by importing from ``magicclass.containers``:

.. code-block:: python

    from magicclass.containers import ScrollableContainer
    from magicgui.widgets import LineEdit

    # A container with scroll area
    c = ScrollableContainer()

    for i in range(10):
        c.append(LineEdit())
    c.show()

.. image:: images/fig_5-1.png

Use Container Variations as magic-class
---------------------------------------

✍ please wait ...
