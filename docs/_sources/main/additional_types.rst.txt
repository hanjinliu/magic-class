================
Additional types
================

To make implementation simpler, ``magic-class`` has some additional types that were not
available in ``magicgui``.

.. contents:: Contents
    :local:
    :depth: 2

Optional type
=============

``Optional`` type is almost identical to ``typing.Optional``. Using this type annotation
``@magicgui`` can create an ``OptionalWidget``, which has a checkbox and an widget of any
type. It represents ``None`` if the checkbox is checked.

.. code-block:: python

    from magicgui import magicgui
    from magicclass.types import Optional

    @magicgui
    def func(a: Optional[int]):
        print(a)
    func.show(True)

.. image:: images/fig_8-1.png

The "Use default value" text can be changed by "text" option. Options of the inner widget
(``SpinBox`` in this example) can be set by "options" option.

.. code-block:: python

    from magicgui import magicgui
    from magicclass.types import Optional

    @magicgui(a={"text": "Don't need a value", "options": {"min": 1, "max": 10}})
    def func(a: Optional[int]):
        print(a)
    func.show(True)

Color type
==========

There is no straightforward way to use a color as an input. In ``magic-class`` you can
use ``Color`` type as a type annotation. This type is an alias of
``Union[Iterable[float], str]`` and is converted into ``ColorEdit`` widget. ``ColorEdit``
behaves very similar to the color editor in ``napari``'s layer control.

.. code-block:: python

    from magicgui import magicgui
    from magicclass.types import Color

    @magicgui
    def func(col: Color = "red"):
        print(col)

.. image:: images/fig_8-2.png
