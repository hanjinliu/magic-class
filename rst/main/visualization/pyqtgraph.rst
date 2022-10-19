================
PyQtGraph Canvas
================

PyQtGraph is a data visualization library based on Qt. It provides variety of plot
canvases and plot items that can be operated in a interactive way. The
``magicclass.ext.pyqtgraph`` submodule tries to integrate many of the ``pyqtgraph``
widgets to provide a consistent, ``magicgui``-like API.

You have to install ``pyqtgraph`` in advance.

.. code-block::

    pip install pyqtgraph

Then several ``pyqtgraph`` canvases are now available.

.. code-block:: python

    from magicclass.ext.pyqtgraph import QtPlotCanvas  # 1-D plot, like plt.plot
    from magicclass.ext.pyqtgraph import QtMultiPlotCanvas  # multiple QtPlotCanvas
    from magicclass.ext.pyqtgraph import QtImageCanvas  # 2-D image, like plt.imshow
    from magicclass.ext.pyqtgraph import QtMultiImageCanvas  # multiple QtImageCanvas

.. contents:: Contents
    :local:
    :depth: 2

QtPlotCanvas
============

``QtPlotCanvas`` is a canvas for 1-D plotting.

.. code-block:: python

    from magicclass.ext.pyqtgraph import QtPlotCanvas

    canvas = QtPlotCanvas()
    canvas.show()

A ``QtPlotCanvas`` is composed of several "layers" and each layer corresponds to a plot item
that is in the canvas. Basically you'll add new layers to visualize data.

Methods and Attributes
----------------------

* Major methods

  - ``add_curve()`` ... Add a curve possibly with symbols, similar to ``plt.plot``.

  - ``add_scatter()`` ... Add scatter plot item, similar to ``plt.scatter``.

  - ``add_hist()`` ... Build a histogram from input data, similar to ``plt.hist``.

  - ``add_bar()`` ... Add a bar plot, similar to ``plt.bar``.

  - ``add_infline()`` ... Add a infinite line, similar to ``plt.axline``.

  - ``add_text()`` ... Add list of texts, similar to ``plt.text``.

  - ``show()`` ... Show canvas.

* Major attributes and properties

  - ``layers`` ... List of all the layers.

  - ``visible`` ... Visibility of canvas.

  - ``enabled`` ... Interactivity of canvas.

  - ``xlim`` ... Minumum and maximum value of x-axis in viewbox.

  - ``ylim`` ... Minumum and maximum value of y-axis in viewbox.

  - ``xlabel`` ... Label text of x-axis.

  - ``ylabel`` ... Label text of y-axis.

  - ``title`` ... Title text of the plot canvas.

  - ``legend`` ... Legend item of the canvas.

  - ``mouse_click_callbacks`` ... list of callback functions that will get called on mouse click.

Add curves
----------

``add_curve`` method will add a ``Curve`` layer to the canvas, store the layer in the ``layers``
attribute and return the layer.

.. code-block:: python

    xdata = np.linspace(0, np.pi, 200)
    ydata = np.sin(xdata) * np.exp(-xdata)
    layer = canvas.add_curve(xdata, ydata)  # or canvas.add_curve(ydata) if you don't need x scale.

There are other keyword argument that will be useful to visualize differently.

.. code-block:: python

    canvas.add_curve(xdata, ydata, name="Data-1")  # name of the layer
    canvas.add_curve(xdata, ydata, edge_color="yellow")  # change color
    canvas.add_curve(xdata, ydata, lw=4, ls="--")  # change line width and line style
    canvas.add_curve(xdata, ydata, symbol="+")  # show symbol at the data points

Layer is available in ``layers``.

.. code-block:: python

    layer = canvas.layers[0]  # the first layer

Handle layers
-------------

The layer objects are also designed to be easily

1. Show/hide layer

   .. code-block:: python

        layer.visible = True  # show
        layer.visible = False  # hide

2. Change color

    .. code-block:: python

        layer.face_color = "red"  # str
        layer.face_color = [0.4, 0.2, 0.2, 1.0]  # float RGBA
        layer.edge_color = [0.4, 0.2, 0.2, 1.0]  # change edge color
        layer.color = "white"  # change face color and edge color

3. Get data

    .. code-block:: python

        layer.xdata  # the x data
        layer.ydata  # the y data

QtMultiPlotCanvas
=================

``QtMultiPlotCanvas`` is a collection of ``QtPlotCanvas``.

.. code-block:: python

    from magicclass.ext.pyqtgraph import QtMultiPlotCanvas

    canvas = QtMultiPlotCanvas(1, 2)  # 1 x 2 canvases
    canvas.show()

If you want to synchronize axes movements, set ``sharex`` and ``sharey``.

.. code-block:: python

    canvas = QtMultiPlotCanvas(2, 2, sharex=True, sharey=True)

The `i`-th canvas is available by simple indexing. Returned items have the same API as
``QtPlotCanvas``.

.. code-block:: python

    canvas[0].add_curve(np.random.random(100))  # add curve to the 0-th canvas.
    canvas[1].layers  # Layer list of the 1st canvas.
