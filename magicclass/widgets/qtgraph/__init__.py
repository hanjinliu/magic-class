try:
    import pyqtgraph
except ImportError:
    from ..utils import NotInstalled
    msg = "Module 'pyqtgraph' is not installed. To use {}, " \
          "you have to install it by:\n" \
          "   $ pip install pyqtgraph\n" \
          "or\n" \
          "   $ conda install pyqtgraph -c conda forge"
    QtPlotCanvas = NotInstalled(msg.format("QtPlotCanvas"))
    QtMultiPlotCanvas = NotInstalled(msg.format("QtMultiPlotCanvas"))
    Qt2YPlotCanvas = NotInstalled(msg.format("Qt2YPlotCanvas"))
    QtImageCanvas = NotInstalled(msg.format("QtImageCanvas"))
    QtMultiImageCanvas = NotInstalled(msg.format("QtMultiImageCanvas"))

else:
    from .widgets import (
        QtPlotCanvas,
        QtMultiPlotCanvas,
        Qt2YPlotCanvas,
        QtImageCanvas,
        QtMultiImageCanvas
        )
    
__all__ = ["QtPlotCanvas",
           "QtMultiPlotCanvas", 
           "Qt2YPlotCanvas",
           "QtImageCanvas",
           "QtMultiImageCanvas"
           ]

del pyqtgraph

def _join(strs):
    strs = [f"``{s}``" for s in strs]
    return ", ".join(strs[:-1]) + f" and {strs[-1]}"
    
__doc__ = \
f"""
PyQtGraph wrapper classes. Currently supports {_join(__all__)}.

These classes offer unified API between graphical items and components, similar to those
in ``magicgui`` and ``napari``.

``QtPlotCanvas`` can treat line plot, scatter plot, bar plot and histogram as "layers".

.. code-block:: python

    from magicclass.widgets import QtPlotCanvas
    
    canvas = QtPlotCanvas()
    canvas.add_curve(np.random.random(100), color="r") # like plt.plot
    canvas.add_scatter(np.random.random(100), ls=":")  # like plt.scatter
    canvas.layers[1].visible = False  # toggle visibility
    canvas.enabled = False            # toggle interactivity
    canvas.show()
    
Other components such as axis labels, title and linear region have intuitive interface.

.. code-block:: python

    canvas.region.visible = True  # show linear region
    canvas.region.value           # get range
    canvas.xlabel = "time"        # change label text
    canvas.xlim = [0, 1]          # change limits.

``QtImageCanvas`` is also designed in a similar way as ``QtPlotCanvas`` but aims at 2D image
visualization.

.. code-block:: python

    from magicclass.widgets import QtImageCanvas
    
    canvas = QtImageCanvas()
    canvas.image = np.random.random((128, 128))
    canvas.show()

Text overlay and scale bar are available now.

.. code-block:: python

    canvas.text_overlay.text = "some info"
    canvas.text_overlay.color = "lime"
    canvas.scale_bar.unit = "px"
    canvas.scale_bar.visible = True

"""