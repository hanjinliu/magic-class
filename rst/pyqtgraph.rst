====================
Use PyQtGraph Canvas
====================

PyQtGraph is a data visualization library based on Qt. It provides variety of plot
canvases and plot items that can be operated in a interactive way. The
``magicclass.ext.pyqtgraph`` submodule tries to integrate many of the ``pyqtgraph``
widgets to provide a consistent, ``magicgui``-like API.

You have to install ``pyqtgraph`` in advance.

.. code-block::

    pip install pyqtgraph


.. code-block:: python

    from magicclass.ext.pyqtgraph import QtPlotCanvas  # 1-D plot, like plt.plot
    from magicclass.ext.pyqtgraph import QtImageCanvas  # 2-D image, like plt.imshow
    from magicclass.ext.pyqtgraph import QtMultiPlotCanvas  # multiple QtPlotCanvas
    from magicclass.ext.pyqtgraph import QtMultiImageCanvas  # multiple QtImageCanvas
