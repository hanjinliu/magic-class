"""
Jupyter QtConsole widget with callback signals.

You can embed a console widget in a magic class.

.. code-block:: python

    from magicclass import magicclass
    from magicclass.widgets import QtConsole

    class Main:
        console = QtConsole()

    ui = Main()
    ui.show()

There are some additional methods that would be very useful for developing a Python script
executable GUI.

.. code-block:: python

    # programmatically add code to console.
    ui.console.value = "a = 1"

    # callback when code is executed.
    @console.executed.connect
    def _():
        print("executed!")

    # programmatically execute code.
    ui.console.execute()

"""

from .widgets import QtConsole

__all__ = ["QtConsole"]
