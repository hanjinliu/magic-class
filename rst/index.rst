.. magic-class documentation master file, created by
   sphinx-quickstart on Sun Nov  7 12:23:43 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to magic-class documentation!
=====================================

``magic-class`` is an extension of `magicgui <https://napari.org/magicgui/>`_.
You can make multi-functional GUI from Python classes.

Source
------

`Jump to GitHub repository <https://github.com/hanjinliu/magic-class>`_.

Installation
------------

``magic-class`` is available on PyPI.

.. code-block:: shell

   pip install magic-class

Contents
--------

.. toctree::
   :maxdepth: 1

   quick_start

Basics
^^^^^^

Here's some basics for widget creation in ``magic-class``.

.. toctree::
   :maxdepth: 1

   options
   nest
   use_field

Make Your GUI Better
^^^^^^^^^^^^^^^^^^^^

It is important to make your GUI user friendly and intuitive. ``magic-class`` provides many
methods that can improve widget appearance and interactivity without disturbing readability
and tidiness of the source code.

.. toctree::
   :maxdepth: 1

   use_wraps
   use_bind
   use_choices
   additional_types
   containers

Data Visualization
^^^^^^^^^^^^^^^^^^

Data visualization is one of the main reasons why we have to rely on GUIs. ``magic-class``
has prepared some custom magic widgets (widgets that follow ``magicgui`` protocols) that
can directly used as components of your GUI.

.. toctree::
   :maxdepth: 1

   matplotlib
   pyqtgraph
   vispy

Advanced Topics
^^^^^^^^^^^^^^^

Learn more about ``magic-class`` here!

.. toctree::
   :maxdepth: 1

   keybinding
   customize_macro
   class_inheritance
   special_methods
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
