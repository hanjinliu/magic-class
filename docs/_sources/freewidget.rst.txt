=====================================
Convert QtWidgets into a Magic Widget
=====================================

If your are an experienced GUI developper, you may often want to define your own
Qt widget classes. Still, it is a good idea to convert it into a ``magicgui``'s
widget in terms of API consistency and simplicity. Especially if you intend to
make your GUI accessible via Python interpreter, hiding huge number of methods
defined in ``QWidget`` class is very important for code completion and safety.

The easiest way to do that in ``magicclass`` is to inherit ``FreeWidget``. It
is aimed at constructing a ``magicgui.widgets.Widget`` object with custom
Qt widget. Actually, many widgets in ``magicclass.widgets`` are defined in this
way.

Basic Usage
===========

Suppose you have a Qt widget defined like:

.. code-block:: python

    from qtpy.QtWidgets import QWidget

    class MyQWidget(QWidget):
        ...


To convert it into a ``magicgui``'s widget, you'll have to call ``set_widget`` method
after initializing the super class.

.. code-block:: python

    from magicclass.widgets import FreeWidget

    class MyWidget(FreeWidget):
        def __init__(self):
            super().__init__()  # initialize
            self.wdt = MyQWidget()  # construct Qt widget
            self.set_widget(self.wdt)  # set widget

Now the ``MyQWidget`` object is correctly imported into ``magicgui.widgets.Widget`` and
is ready to used as if it is an ordinary ``magicgui``'s widget.

.. code-block:: python

    x = MyWidget()

    # properties and methods inherited from "Widget"
    x.visible = False
    x.enabled = True
    x.show()
    x.hide()

    # append into a container
    from magicgui.widgets import Container
    container = Container()
    container.append(x)

Make It Behave More Like A ValueWidget
======================================

``magicgui.widgets.ValueWidget`` is widgets that have representative values. You'll have
to define ``value`` property to make a ``FreeWidget`` more like a ``ValueWidget``.
It is better idea to add a value change signal to the class.

Following example shows how to define value getter/setter and value change signal, suppose
the ``MyQWidget`` has methods ``value``, ``setValue`` and the corresponding signal
``valueChanged``.

.. code-block:: python

    from psygnal import Signal

    class MyWidget(FreeWidget):
        # you should restrict the type of signal emission according to the Qt widget,
        # such as Signal(str)
        changed = Signal(object)

        def __init__(self):
            super().__init__()  # initialize
            self.wdt = MyQWidget()  # construct Qt widget
            self.wdt.valueChanged.connect(self.changed.emit)  # relay signal
            self.set_widget(self.wdt)  # set widget

        @property
        def value(self):
            return self.wdt.value()

        @value.setter
        def value(self, v):
            self.wdt.setValue(v)
