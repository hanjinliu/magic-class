======================
Options in magic-class
======================

``@magicclass`` decorator has several options.

These options are inherited from ``magicgui``:

* ``layout: str = "vertical"`` ... Layout of container. ``"vertical"`` or ``"horizontal"``.

* ``labels: bool = True`` ... If ``True``, parameter names will appear as labels.

* ``name: str = None`` ... Name of widget. By default the class name is used.

* ``parent = None`` ... Parent widget.

These options are `magicclass` specific:

* ``visible: bool = None`` ... Initial visibility of the widget.

* ``close_on_run: bool = None`` ... If ``True`` (default), ``magicgui`` widgets will be closed
  after function call.

* ``popup: bool = True`` ... Deprecated. Use ``popup_mode`` instead.

* ``popup_mode: str | PopUpMode = None`` ... Specify how ``magicgui`` widgets are popped up.

    + ``popup`` (default): Popped up as a new window, like a dialog.
    + ``first``: Appear on the first position of the container.
    + ``last``: Appear on the last position of the container.
    + ``below``: Appear below the button.
    + ``above``: Appear above the button.
    + ``parentlast``: Appear on the last position of the parent container.
    + ``dock``: Appear as a dock widget. If the parent container is a dock widget of ``napari`` viewer,
      then it is also added as a dock widget.

* ``error_mode: str | ErrorMode = None`` ... Specify how exceptions in function call will be raised.

    + ``msgbox``: Open a message box.
    + ``stderr``: Print output as standard.

* ``widget_type: str | WidgetType = WidgetType.none`` ... Specify widget types. See :doc:`containers`.

To avoid writing the same options many times, you can change the default setting via ``default`` constant:

.. code-block:: python

    from magicclass import default

    default["close_on_run"] = False
    default["popup_mode"] = "dock"
