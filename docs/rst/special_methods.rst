=================================
Special attributes in magic-class
=================================

There are some special attributes that will be recognized differently by magic classes. 

* ``__post_init__``

    Similar to builtin ``dataclass``, this method will be called after ``__init__`` had finished.
    This method is necessary because widgets are created after instance construction so you cannot
    refer to the widgets in ``__init__`` function. For instance, you can set widget geometry in
    ``__post_init__``.
  
    .. code-block:: python
    
        @magicclass
        class Main:
            def __post_init__(self):
                self["func"].min_height = 100
    
            def func(self): ...

* ``__call__``

    Magic classes do not convert methods into widgets if the name start with "_" but this is an 
    exception.

* ``__magicclass_parent__``

    The parent magic class object is stored in this attribute. This parameter is needed because
    the `parent` property of ``magicgui``'s widgets returns backend widget.
    
    .. code-block:: python
    
        @magicclass
        class Parent:
            @magicclass
            class Child: ...

        ui = Parent()
        print(type(ui.Child.parent))
        print(type(ui.Child.__magicclass_parent__))
    
    .. code-block::
        
        <class 'PyQt5.QtWidgets.QWidget'>
        <class 'abc.Parent'>
    
    Therefore, when you want to call parent methods from its children, you don't have to use ``wraps``
    method in principle.

* ``__magicclass_children__``

    The child widgets are all stored in this list.
    