============
Vispy Canvas
============

`vispy <https://github.com/vispy/vispy>`_ is a 2D/3D visualization library that has Qt
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

You can programatically adjust parameters

.. code-block:: python

    ui.canvas.layers[0].contrast_limits = (0.2, 0.7)

or create a ``Container`` widget of parameters.

.. code-block:: python

    params = ui.canvas.layers[0].as_container()  # create a Container
    params.show()  # show the widget

Supported Methods
-----------------

- :meth:`add_image` ... Add a 3D array as a volume.
- :meth:`add_isosurface` ... Add a 3D array as a isosurface.
- :meth:`add_surface` ... Add a list of 2D arrays as a surface.
- :meth:`add_points` ... Add a (N, 3) array as a point cloud.
- :meth:`add_arrows` ... Add a (N, P, 3) array as arrows. P is the number of points per arrow.
