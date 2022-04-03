============
Vispy Canvas
============

`vispy <https://github.com/vispy/vispy>`_. is a 2D/3D visualization library that has Qt
backend.

.. warning::

    This submodule is largely work in progress!

2D Canvas
=========

For 2D plot, use ``VispyPlotCanvas``.

.. code-block:: python

    from magicclass.ext.vispy import VispyPlotCanvas
    from magicclass import magicclass, field

    @magicclass
    class A:
        canvas = field(Vispy3DCanvas)

    ui = A()
    ui.canvas.add_curve(np.random.random(100), color="red", symbol="+")
    ui.show()


3D Canvas
=========

For 3D visualization, use ``Vispy3DCanvas``.

.. code-block:: python

    from magicclass.ext.vispy import Vispy3DCanvas
    from magicclass import magicclass, field

    @magicclass
    class A:
        canvas = field(Vispy3DCanvas)

    ui = A()
    ui.canvas.add_image(np.random.random((60, 60, 60)))
    ui.show()

You have to programatically adjust parameters.

.. code-block:: python

    ui.canvas.layers[0].contrast_limits = (0.2, 0.7)

This widget is useful in providing a mini-viewer as a ``napari`` dock widget.

Supported Methods
-----------------

- ``add_image``
- ``add_isosurface``
- ``add_surface``
