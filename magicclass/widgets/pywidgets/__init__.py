"""
This widget submodule contains "visible PyObject" widgets, which has similar API as PyObject to
operate items. They are also equipped with custom delegate, contextmenu and double-click
callbacks.

ListWidget
----------

``ListWidget`` is a ``QListWidget`` wrapper class. This widget can contain any Python objects as
list items.

.. code-block:: python

    from magicclass.widgets import ListWidget

    listwidget = ListWidget()

    # You can add any objects
    listwidget.append("abc")
    listwidget.append(np.arange(5))

You can dispatch double click callbacks depending on the type of contents.

.. code-block:: python

    @listwidget.register_callback(str)
    def _(item, i):
        # This function will be called when the item "abc" is double-clicked.
        print(item)

    @listwidget.register_callback(np.ndarray)
    def _(item, i):
        # This function will be called when the item np.arange(5) is double-clicked.
        print(item.tolist())

In a similar way, you can dispatch display method and context menu.

.. code-block:: python

    @listwidget.register_delegate(np.ndarray)
    def _(item):
        # This function should return how ndarray will be displayed.
        return f"Array with shape {item.shape}"

    @listwidget.register_contextmenu(np.ndarray)
    def Plot(item, i):
        '''Function documentation will be the tooltip.'''
        plt.plot(item)
        plt.show()

DictWidget
----------

DictWidget is a single column QTableWidget. This widget can contain any Python objects
as table items and keys as row names..

.. code-block:: python

    from magicclass.widgets import DictWidget

    dictwidget = DictWidget()

    # You can add any objects
    dictwidget["name-1"] = 10
    dictwidget["data"] = np.arange(5)

The dispatching feature is shared with ListWidget.

"""

from .dict import DictWidget
from .list import ListWidget

__all__ = ["DictWidget", "ListWidget"]
