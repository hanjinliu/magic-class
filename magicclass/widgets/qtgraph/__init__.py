"""
PyQtGraph wrapper classes.

``QtPlotCanvas`` can treat line plots and scatter plots as "layers" and has similar API as 
``napari.Viewer`` and ``matplotlib``:

.. code-block:: python

    from magicclass.widgets import QtPlotCanvas
    
    canvas = QtPlotCanvas()
    canvas.add_curve(np.random.random(100), color="r")
    canvas.add_scatter(np.random.random(100), ls=":")
    canvas.layers[1].visible = False
    canvas.interactive = False
    canvas.show()

``QtImageCanvas`` is also designed in a similar way as ``QtPlotCanvas`` but aims at 2D image
visualization.

.. code-block:: python

    from magicclass.widgets import QtImageCanvas
    
    image = np.random.random((128, 128))
    canvas = QtImageCanvas(image)
    canvas.show()

"""

from .qt_graph import QtPlotCanvas, QtImageCanvas