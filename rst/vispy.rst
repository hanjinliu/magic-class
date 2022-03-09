============
Vispy Canvas
============

Mostly work in progress but the basic image layer works.

.. code-block:: python

    from magicclass.ext.vispy import Vispy3DCanvas
    from magicclass import magicclass, field

    @magicclass
    class A:
        canvas = field(Vispy3DCanvas)

    ui = A()
    ui.canvas.add_image(np.random.random((60, 60, 60)))
    ui.show()

This widget is useful in providing a mini-viewer as a ``napari`` dock widget.
