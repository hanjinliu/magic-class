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

.. code-block:: shell

    [ common function ]
    [  main function  ]

Predefinition of methods
========================


Field Objects in the Base Class
===============================

