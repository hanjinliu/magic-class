====================
Container Variations
====================

Use Other Qt Widgets as Container
---------------------------------

In ``magic-class``, many Qt widget variations are available in a same API as ``magicgui``'s ``Container``.
You can use them by importing from ``magicclass.widgets``:

.. code-block:: python

    from magicgui.widgets import LineEdit, ScrollableContainer

    # A container with scroll area
    c = ScrollableContainer()

    for i in range(10):
        c.append(LineEdit())
    c.show()

.. image:: images/fig_5-1.png

Available Containers
--------------------

* ``ButtonContainer``
    + *base Qt class* 
        QPushButton
    + *additional properties*
        ``btn_text`` ... Text of button.
    + *appearance*
        A button widget. The inner container appears when the button is clicked.

* ``CollapsibleContainer``
    + *base Qt class* 
        QToolButton
    + *additional properties*
        ``btn_text`` ... Text of button.
    + *appearance*
        Collapsible/expandable widget.

* ``DraggableContainer``
    + *base Qt class* 
        QScrollArea
    + *additional properties*
        None
    + *appearance*
        Container in a scroll area. Scroll by mouse drag.

* ``GroupBoxContainer``
    + *base Qt class* 
        QGroupBox
    + *additional properties*
        None
    + *appearance*
        Container is enclosed by a line.

* ``ListContainer``
    + *base Qt class* 
        QListWidget
    + *additional properties*
        ``current_index`` ... Current index of selected component in the list.
    + *appearance*
        Drag-and-droppable list widget.

* ``SubWindowsContainer``
    + *base Qt class* 
        QMdiArea
    + *additional properties*
        None
    + *appearance*
        All the child widgets are displayed as subwindows in this container.

* ``ScrollableContainer``
    + *base Qt class* 
        QScrollArea
    + *additional properties*
        None
    + *appearance*
        Container in a scroll area. Scrll by scroll bars.

* ``SplitterContainer``
    + *base Qt class* 
        QSplitter
    + *additional properties*
        None.
    + *appearance*
        The borders between adjacent widgets are adjustable (every child widget is resizable).

* ``StackedContainer``
    + *base Qt class* 
        QStackedWidget
    + *additional properties*
        ``current_index`` ... Current index of selected component in the list.
    + *appearance*
        One child is visible at a time. Current index must be set programmatically or from other widgets.

* ``TabbedContainer``
    + *base Qt class* 
        QTabWidget
    + *additional properties*
        ``current_index`` ... Current index of selected component in the list.
    + *appearance*
        Composed of tabs and each widget is assigned to a tab.

* ``ToolBoxContainer``
    + *base Qt class* 
        QToolBox
    + *additional properties*
        ``current_index`` ... Current index of selected component in the list.
    + *appearance*
        Composed of collapsible tool boxes and one box is expanded at a time.


Use Container Variations in magic-class
---------------------------------------

You can choose a abovementioned container widget types (or ``MainWindow`` widget of ``magicgui``) using
 ``widget_type`` option in ``magicclass``:

.. code-block:: python

    @magicclass(widget_type="scrollable")
    class Main:
        ...

or import ``WidgetType`` for code completion:

.. code-block:: python

    from magicclass import WidgetType

    @magicclass(widget_type=WidgetType.scrollable)
    class Main:
        ...

The type map is following:

=========== ====================
WidgetType  Container
=========== ====================
none        Container
scrollable  ScrollableContainer
draggable   DraggableContainer
split       SplitterContainer
collapsible CollapsibleContainer
button      ButtonContainer
toolbox     ToolBoxContainer
tabbed      TabbedContainer
stacked     StackedContainer
list        ListContainer
subwindows  SubWindowsContainer
groupbox    GroupBoxContainer
mainwindow  MainWindow
=========== ====================