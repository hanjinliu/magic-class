================
Set Custom Icons
================

An icon often tells more than a text. If you don't hesitate to prepare icons, using them
in your GUI will be a good idea especially in a tool bar.

Basically you'll set icons with the ``icon`` keyword argument of ``@set_design`` decorator.
There are several ways to do that in ``magic-class``.

.. contents:: Contents
    :local:
    :depth: 1

Image File as an Icon
=====================

If you have your icon file in such as .jpg or .svg format, you can use the path.

.. code-block:: python

    from magicclass import magicclass, magictoolbar, set_design

    icon_path = "path/to/icon.png"

    @magicclass
    class A:
        @magictoolbar
        class toolbar:
            @set_design(icon=icon_path)
            def func(self):
                ...


Standard Icons
==============

Qt supplies several standard icons. You can use them by their name. Since it is tough to
find out the name of a icon, you can use the ``Icon`` namespace.

.. code-block:: python

    from magicclass import magicclass, magictoolbar, set_design, Icon

    @magicclass
    class A:
        @magictoolbar
        class toolbar:
            @set_design(icon=Icon.ArrowUp)
            def func(self):
                ...

Array as an Icon
================

You may want to apply some transformation to an icon image. In this case, an array-like object
can be used.

.. code-block:: python

    from magicclass import magicclass, magictoolbar, set_design
    from skimage import io

    img = io.imread("path/to/image.png")  # read image as a np.ndarray
    icon = -img  # invert image

    @magicclass
    class A:
        @magictoolbar
        class toolbar:
            @set_design(icon=icon)
            def func(self):
                ...
