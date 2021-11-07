===========
Quick Start
===========

In ``magicgui``, you can convert functions into widgets. For instance,

.. code-block:: python

    from magicgui import magicgui

    @magicgui
    def print_text(text: str):
        print(text)
    
    print_text.show()

will create a widget that is composed of a line edit (for the input argument ``text``) and a call button.

Similarly, with ``magicclass`` decorator, you can convert a Python class into a widget and its methods appear as
push buttons. When a button is clicked, the corresponding magicgui will be popped up.

.. code-block:: python

    from magicclass import magicclass

    @magicclass
    class MyClass:
        def set_value(self, value: str):
            self.value = value
        
        def print_value(self):
            print(self.value)
