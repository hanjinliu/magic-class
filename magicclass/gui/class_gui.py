from __future__ import annotations
from inspect import signature
from typing import Any, Callable
from qtpy.QtWidgets import QMenuBar, QWidget
from qtpy.QtCore import Qt
from magicgui.widgets import Container, MainWindow,Label, FunctionGui, Image, Table
from magicgui.widgets._bases import Widget, ButtonWidget, ValueWidget, ContainerWidget
from magicgui.widgets._concrete import _LabeledWidget
from macrokit import Symbol

from .mgui_ext import PushButtonPlus
from .menu_gui import MenuGui, ContextMenuGui
from ._base import BaseGui, PopUpMode, ErrorMode, value_widget_callback, nested_function_gui_callback
from .utils import define_callback, MagicClassConstructionError
from ._containers import (
    ButtonContainer,
    GroupBoxContainer,
    ListContainer,
    SubWindowsContainer,
    ScrollableContainer,
    CollapsibleContainer,
    SplitterContainer,
    StackedContainer,
    TabbedContainer,
    ToolBoxContainer
    )

from ..utils import iter_members, extract_tooltip
from ..widgets import FreeWidget
from ..fields import MagicField
from ..signature import get_additional_option

class ClassGuiBase(BaseGui):
    # This class is always inherited by @magicclass decorator.
    _component_class = PushButtonPlus
    _container_widget: type
    _remove_child_margins: bool
    native: QWidget
    
    def _create_widget_from_field(self, name: str, fld: MagicField):
        cls = self.__class__
        if fld.not_ready():
            try:
                fld.default_factory = cls.__annotations__[name]
                if isinstance(fld.default_factory, str):
                    # Sometimes annotation is not type but str. 
                    from pydoc import locate
                    fld.default_factory = locate(fld.default_factory)
                    
            except (AttributeError, KeyError):
                pass
        
        fld.name = fld.name or name.replace("_", " ")
        widget = fld.get_widget(self)
            
        if isinstance(widget, (ValueWidget, Container)):
            # If the field has callbacks, connect it to the newly generated widget.
            for callback in fld.callbacks:
                # funcname = callback.__name__
                widget.changed.connect(define_callback(self, callback))
                
            if hasattr(widget, "value") and fld.record:
                # By default, set value function will be connected to the widget.
                f = value_widget_callback(self, widget, name, getvalue=type(fld) is MagicField)
                widget.changed.connect(f)
                
        return widget
    
    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and nested
        classes are converted to magicgui widgets.
        """        
        cls = self.__class__
        
        # Add class docstring as tooltip.
        doc = extract_tooltip(cls)
        self.tooltip = doc
        
        # Bind all the methods and annotations
        n_insert = 0
        base_members = set(x[0] for x in iter_members(self._container_widget)) 
        base_members |= set(x[0] for x in iter_members(ClassGuiBase))
        
        _hist: list[tuple[str, str, str]] = [] # for traceback
        
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if name in ClassGuiBase.__annotations__.keys() or isinstance(attr, property):
                continue
            
            try:
                if isinstance(attr, type):
                    # Nested magic-class
                    widget = attr()
                    setattr(self, name, widget)
                    self.__magicclass_children__.append(widget)
                
                elif isinstance(attr, BaseGui):
                    widget = attr
                    setattr(self, name, widget)
                    self.__magicclass_children__.append(widget)
                
                elif isinstance(attr, MagicField):
                    # If MagicField is given by field() function.
                    widget = self._create_widget_from_field(name, attr)
                                
                elif isinstance(attr, FunctionGui):
                    widget = attr
                    p0 = list(signature(attr).parameters)[0]
                    getattr(widget, p0).bind(self) # set self to the first argument
                    
                else:
                    # convert class method into instance method
                    widget = getattr(self, name, None)
                
                if isinstance(widget, BaseGui):
                    widget._my_symbol = Symbol(name)
                            
                if isinstance(widget, MenuGui):
                    # Add menubar to container
                    widget.__magicclass_parent__ = self
                    if self._menubar is None:
                        self._menubar = QMenuBar(parent=self.native)
                        self.native.layout().setMenuBar(self._menubar)
                    
                    widget.native.setParent(self._menubar, widget.native.windowFlags())
                    self._menubar.addMenu(widget.native)
                    _hist.append((name, type(attr), "MenuGui"))
                
                elif isinstance(widget, ContextMenuGui):
                    # Add context menu to container
                    widget.__magicclass_parent__ = self
                    self.native.setContextMenuPolicy(Qt.CustomContextMenu)
                    self.native.customContextMenuRequested.connect(
                        _define_context_menu(widget, self.native)
                        )
                    _hist.append((name, type(attr), "ContextMenuGui"))
                
                elif isinstance(widget, (Widget, Callable)):
                    if (not isinstance(widget, Widget)) and isinstance(widget, Callable):
                        # Methods or any callable objects, but FunctionGui is not included.
                        # NOTE: Here any custom callable objects could be given. Some callable
                        # objects can be incompatible (like "Signal" object in magicgui) but
                        # useful. Those callable objects should be passed from widget construction.
                        try:
                            widget = self._create_widget_from_method(widget)
                        except Exception:
                            continue
                    
                    elif hasattr(widget, "__magicclass_parent__") or \
                        hasattr(widget.__class__, "__magicclass_parent__"):
                        # magic-class has to know its parent.
                        # if __magicclass_parent__ is defined as a property, hasattr must be called
                        # with a type object (not instance).
                        widget.__magicclass_parent__ = self

                    elif isinstance(widget, FunctionGui):
                        # magic-class has to know when the nested FunctionGui is called.
                        f = nested_function_gui_callback(self, widget)
                        widget.called.connect(f)
                        
                    else:
                        if not widget.name:
                            widget.name = name
                        if hasattr(widget, "text") and not widget.text:
                            widget.text = widget.name.replace("_", " ")
                        
                    # Now, "widget" is a Widget object. Add widget in a way similar to "insert" method 
                    # of Container.
                    if name.startswith("_"):
                        continue
                
                    clsname = get_additional_option(attr, "into")
                    if clsname is not None:
                        self._unwrap_method(clsname, name, widget)
                    else:
                        self.insert(n_insert, widget)
                        n_insert += 1
                    
                    _hist.append((name, str(type(attr)), type(widget).__name__))
            
            except Exception as e:
                hist_str = "\n\t".join(map(
                    lambda x: f"{x[0]} {x[1]} -> {x[2]}",
                    _hist
                    )) + f"\n\t\t{name} ({type(attr).__name__}) <--- Error"
                if not hist_str.startswith("\n\t"):
                    hist_str = "\n\t" + hist_str
                if isinstance(e, MagicClassConstructionError):
                    e.args = (f"\n{hist_str}\n{e}",)
                    raise e
                else:
                    raise MagicClassConstructionError(f"\n{hist_str}\n\n{type(e).__name__}: {e}") from e
            
        
        # convert __call__ into a button
        if hasattr(self, "__call__"):
            widget = self._create_widget_from_method(self.__call__)
            self.insert(n_insert, widget)
            n_insert += 1
        
        self._unify_label_widths()
        del _hist
        return None

def make_gui(container: type[ContainerWidget], no_margin: bool = True):
    """
    Make a ClassGui class from a Container widget.
    Because GUI class inherits Container here, functions that need overriden must be defined
    here, not in ClassGuiBase.
    """    
    def wrapper(cls_: type[ClassGuiBase]):
        cls = type(cls_.__name__, (container, ClassGuiBase), {})
        def __init__(self: cls, 
                     layout: str = "vertical", 
                     parent = None, 
                     close_on_run: bool = None,
                     popup_mode: str | PopUpMode = None, 
                     error_mode: str | ErrorMode = None,
                     labels: bool = True, 
                     name: str = None, 
                     ):

            container.__init__(self, layout=layout, labels=labels, name=name)
            BaseGui.__init__(self, close_on_run=close_on_run, popup_mode=popup_mode, 
                             error_mode=error_mode)
            
            if parent is not None:
                self.parent = parent
                
            self._menubar = None
            
            self.native.setObjectName(self.name)
            self.native.setWindowTitle(self.name)
        
        def __setattr__(self: cls, name: str, value: Any):
            if not isinstance(getattr(self.__class__, name, None), MagicField):
                container.__setattr__(self, name, value)
            else:
                object.__setattr__(self, name, value)

        def insert(self: cls, key: int, widget: Widget):
            # _hide_labels should not contain Container because some ValueWidget like widgets
            # are Containers.
            _hide_labels = (_LabeledWidget, ButtonWidget, ClassGuiBase, FreeWidget, Label,
                            Image, Table, FunctionGui)
                
            if isinstance(widget, (ValueWidget, ContainerWidget)):
                widget.changed.connect(lambda: self.changed.emit(self))
            
            if hasattr(widget, "__magicclass_parent__") or \
                hasattr(widget.__class__, "__magicclass_parent__"):
                if isinstance(widget, ClassGuiBase) and self._remove_child_margins:
                    widget.margins = (0, 0, 0, 0)
                widget.__magicclass_parent__ = self
                
            _widget = widget

            if self.labels:
                # no labels for button widgets (push buttons, checkboxes, have their own)
                if not isinstance(widget, _hide_labels):
                    _widget = _LabeledWidget(widget)
                    widget.label_changed.connect(self._unify_label_widths)

            self._list.insert(key, widget)
            if key < 0:
                key += len(self)
            self._widget._mgui_insert_widget(key, _widget)
            self._unify_label_widths()

        
        def show(self: cls, run: bool = False) -> None:
            """
            Show ClassGui. If any of the parent ClassGui is a dock widget in napari, then this
            will also show up as a dock widget (floating if in popup mode).
            """        
            if self.__magicclass_parent__ is not None and self.parent is None:
                # If child magic class is closed before, we have to set parent again.
                self.native.setParent(self.__magicclass_parent__.native, 
                                      self.native.windowFlags())
            
            viewer = self.parent_viewer
            if viewer is not None and self.parent is not None:
                name = self.parent.objectName()
                if name in viewer.window._dock_widgets:
                    viewer.window._dock_widgets[name].show()
                else: 
                    dock = viewer.window.add_dock_widget(self, area="right", 
                                                         allowed_areas=["left", "right"])
                    dock.setFloating(self._popup_mode == PopUpMode.popup)
            else:
                container.show(self, run=run)
                self.native.activateWindow()
            return None
        
        def close(self: cls):
            current_self = self._search_parent_magicclass()
            
            viewer = current_self.parent_viewer
            if viewer is not None:
                try:
                    viewer.window.remove_dock_widget(self.parent)
                except Exception:
                    pass
                
            container.close(self)
                
            return None
        
        cls.__init__ = __init__
        cls.__setattr__ = __setattr__
        cls.insert = insert
        cls.show = show
        cls.close = close
        cls._container_widget = container
        cls._remove_child_margins = no_margin
        return cls
    return wrapper


@make_gui(Container)
class ClassGui: pass

@make_gui(SplitterContainer)
class SplitClassGui: pass

@make_gui(ScrollableContainer)
class ScrollableClassGui: pass

@make_gui(CollapsibleContainer)
class CollapsibleClassGui: pass

@make_gui(ButtonContainer)
class ButtonClassGui: pass

@make_gui(ToolBoxContainer, no_margin=False)
class ToolBoxClassGui: pass

@make_gui(TabbedContainer, no_margin=False)
class TabbedClassGui: pass

@make_gui(StackedContainer, no_margin=False)
class StackedClassGui: pass

@make_gui(ListContainer, no_margin=False)
class ListClassGui: pass

@make_gui(SubWindowsContainer, no_margin=False)
class SubWindowsClassGui: pass

@make_gui(GroupBoxContainer, no_margin=False)
class GroupBoxClassGui: pass

@make_gui(MainWindow)
class MainWindowClassGui: pass

def _define_context_menu(contextmenu, parent):
    def rightClickContextMenu(point):
        contextmenu.native.exec_(parent.mapToGlobal(point))
    return rightClickContextMenu
