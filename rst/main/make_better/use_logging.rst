======================
Logging in magic-class
======================

Logger Widget
=============

It is important to keep a log if your GUI is complicated.
In data science, it is also helpful to show the results with rich text, tables, and figures.

In :mod:`magicclass`, you can use the logger widget to show the rich messages.

.. code-block:: python

    from magicclass.widgets import Logger

    log = Logger()
    log.show()  # show the logger widget.

Print texts
-----------

There are several ways to show text messages.

.. code-block:: python

    log.print("message")  # print the message.
    log.print_html("<b>bold</b><i>italic</i> <code>code</code>")  # print the message with HTML.
    log.print_rst("**bold** *italic* ``code``")  # print the message with reStructuredText.

If you want to use the built-in :meth:`print` function but show the message in the logger widget,
you can use the :meth:`set_stdout` context manager.

.. code-block:: python

    with log.set_stdout():
        print("message")  # print the message.

:meth:`set_logger` context manager works similarly.

.. code-block:: python

    import logging

    with log.set_logger():
        logging.info("message")

Print images
------------

You can show 2D arrays as images with :meth:`print_image` method.

.. code-block:: python

    log.print_image(np.random.rand(100, 100))  # show the image.

Print tables
------------

Any :class:`pandas.DataFrame`-like objects can be shown as a table with :meth:`print_table`
method.

.. code-block:: python

    log.print_table({"a": [1, 2, 3], "b": [True, False, False]})
    log.print_table([[0, 1], [2, 3]])

Plotting
--------

The :meth:`set_plt` context manager can be used to show the :mod:`matplotlib` plots in the
logger widget.

.. code-block:: python

    import matplotlib.pyplot as plt

    with log.set_plt():
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.show()

Use ``logging`` Submodule
=========================

:mod:`magicclass` provides a submodule ``logging`` to use the logger widget easily.
Most of the methods are the same as the standard :mod:`logging` module.

.. code-block:: python

    from magicclass import logging

    logger = logging.getLogger("your-app-name")
    logger.widget.show()  # show the logger widget.

    logger.print("message")  # print the message.
    with logger.set_plt():
        plt.plot([1, 2, 3], [4, 5, 6])  # plot
