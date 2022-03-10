===================
Inherit Magic Class
===================

Class inheritance is fundamental in object-oriented languages. It makes class
definition much clearer in many cases.

Magic-class is designed to make GUI structures connected with the structure of
class itself, so how to deal with class inheritance is not a well-defined feature
by default. Here are some points that you have to keep in mind before making
abstract classes.

The Order of Widget
===================

First, let's consider following example.

.. code-block:: python

    from magicclass import magicclass

    class Base:
        def common_function(self):
            """Do some common things."""

    @magicclass
    class Main(Base):
        def main_function(self):
            """Main one."""

    ui = Main()
    ui.show()

.. note::

    Do **NOT** decorate ``Base`` class with ``@magicclass``, otherwise constructor will
    raise ``TypeError``. You only have to decorate the final concrete classes.

It is obvious that created GUI will have two buttons named "common function" and "main
function", but it is not clear which is upper and which is lower.

In magic-class, methods defined in base classes will appear **upper** than those in
subclasses. In the case of example, GUI will look like:

.. code-block::

    [ common function ]
    [  main function  ]


Field Objects in the Base Class
===============================

You may want to add widgets using ``MagicField`` (see :doc:`use_field`). ``MagicField``
behaves similarly as methods. In the following example,

.. code-block:: python

    from magicclass import magicclass, field

    class Base:
        x = field(int)

    @magicclass
    class Main(Base):
        y = field(str)

Two widgets, ``x`` and ``y`` will be packed in the ``Main`` GUI, in order ``x``, ``y``.

However, if you want to use ``Bound`` to bind parameter to method or connect callback
function to a field, you must re-define fields in the subclasses.

1. Bind methods
---------------

.. container:: twocol

    .. container:: leftside

        *This will not work*

        .. code-block:: python

            from magicclass import magicclass, field
            from magicclass.types import Bound

            class Base:
                x = field(int)

            @magicclass
            class Main(Base):
                def func(self, value: Bound[x]):
                    """Do something"""

    .. container:: rightside

        *This will work*

        .. code-block:: python

            from magicclass import magicclass, field
            from magicclass.types import Bound

            class Base:
                x = field(int)

            @magicclass
            class Main(Base):
                x = field(int)

                def func(self, value: Bound[x]):
                    """Do something"""

1. Define Callbacks
-------------------

.. container:: twocol

    .. container:: leftside

        *This will not work*

        .. code-block:: python

            from magicclass import magicclass, field

            class Base:
                x = field(int)

            @magicclass
            class Main(Base):
                @x.connect
                def _callback(self):
                    """Do something"""

    .. container:: rightside

        *This will work*

        .. code-block:: python

            from magicclass import magicclass, field

            class Base:
                x = field(int)

            @magicclass
            class Main(Base):
                x = field(int)

                @x.connect
                def _callback(self):
                    """Do something"""

.. note::

    These caveats are quite natural considering the concept of scope in Python.
    When you define a variable in a class, it is not available from other classes
    until class definition finishes.

    .. code-block:: python

        class A:
            x = 1
        class B(A):
            print(x)

    .. code-block::

        NameError: name 'x' is not defined

    This is because class inheritance has not finished yet in the line ``print(x)``.

Nesting Magic Classes
=====================

Nesting magic classes (see :doc:`nest`) is useful for designing layout of widgets.
You don't have to worry about inheriting base class with a nested magic class.

.. code-block:: python

    class Base(MagicTemplate):
        # All of these widgets and their layout will be inherited to subclasses
        result = field(str)

        @magicclass
        class X(MagicTemplate):
            def func(self): ...

        @X.wraps
        def func(self):
            self.result.value = self.__class__.__name__

    @magicclass
    class A(Base):
        pass

Predefinition of Methods and Fields
===================================

Most of the time you want to inherit a class is when you want to prepare a template
of multipule GUIs. As mentioned above, methods and fields that are defined in the
base class will packed **before** those in the subclasses. This is not desirable if
you want the subclasses share same header and footer and make the middle widgets variable.

Just like using ``wraps`` method (see :doc:`use_wraps`), the pre-definition strategy is
also useful here. First arrange all the widgets in the base class, and specifically
define the real widgets in the subclasses.

.. code-block:: python

    class Base(MagicTemplate):
        header = field("this is header", default_factory="Label")
        x = ...  # pre-definition
        footer = field("this is footer", default_factory="Label")

    @magicclass
    class A(Base):
        def x(self):
            """Do something"""

    @magicclass
    class B(Base):
        x = field(int)

.. image:: images/fig_7-1.png
