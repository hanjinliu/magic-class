try:
    from .widgets import (
        QtPlotCanvas,
        QtMultiPlotCanvas,
        Qt2YPlotCanvas,
        QtImageCanvas,
        QtMultiImageCanvas,
    )

    PYQTGRAPH_AVAILABLE = True

    __all__ = [
        "QtPlotCanvas",
        "QtMultiPlotCanvas",
        "Qt2YPlotCanvas",
        "QtImageCanvas",
        "QtMultiImageCanvas",
        "PYQTGRAPH_AVAILABLE",
    ]
except ImportError:

    PYQTGRAPH_AVAILABLE = False

    __all__ = ["PYQTGRAPH_AVAILABLE"]


def _join(strs):
    strs = [f"``{s}``" for s in strs]
    return ", ".join(strs[:-1]) + f" and {strs[-1]}"


__doc__ = f"""
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
