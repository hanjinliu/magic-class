from __future__ import annotations
from inspect import signature
from qtpy.QtWidgets import QMenuBar
from magicgui.widgets import Container, MainWindow,Label, FunctionGui, Image, Table
from magicgui.widgets._bases import Widget, ButtonWidget, ValueWidget, ContainerWidget
from magicgui.widgets._concrete import _LabeledWidget

from .macro import Expr, Head, Symbol
from .utils import iter_members, extract_tooltip, get_parameters, define_callback
from .widgets import PushButtonPlus, FrozenContainer
from .field import MagicField
from .menu_gui import MenuGui
from .containers import (
    ButtonContainer,
    ScrollableContainer,
    CollapsibleContainer,
    SplitterContainer,
    StackedContainer,
    TabbedContainer,
    ToolBox
    )
from ._base import BaseGui

class ClassGuiBase(BaseGui):
    # This class is always inherited by @magicclass decorator.
    _component_class = PushButtonPlus
    _container_widget: type
    _remove_child_margins: bool
    
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
            
        widget = fld.to_widget()
        widget.name = widget.name or name.replace("_", " ")
            
        if isinstance(widget, (ValueWidget, Container)):
            # If the field has callbacks, connect it to the newly generated widget.
            for callback in fld.callbacks:
                # funcname = callback.__name__
                widget.changed.connect(define_callback(self, callback))
                
            if hasattr(widget, "value"):        
                # By default, set value function will be connected to the widget.
                f = _value_widget_callback(self, widget, name)
                widget.changed.connect(f)
                
        setattr(self, name, widget)
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
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if name in ClassGuiBase.__annotations__.keys() or isinstance(attr, property):
                continue
            
            # First make sure none of them is type object nor MagicField object.
            if isinstance(attr, type):
                # Nested magic-class
                widget = attr()
                setattr(self, name, widget)
            
            elif isinstance(attr, BaseGui):
                widget = attr
                setattr(self, name, widget)
            
            elif isinstance(attr, MagicField):
                # If MagicField is given by field() function.
                widget = self._create_widget_from_field(name, attr)
            
            elif isinstance(attr, FunctionGui):
                widget = attr
                p0 = list(signature(attr).parameters)[0]
                getattr(widget, p0).bind(self) # set self to the first argument
                
            else:
                # convert class method into instance method
                if not hasattr(attr, "__magicclass_wrapped__"):
                    # Standard method definition
                    widget = getattr(self, name, None)

                else:
                    # If the method is redefined, the newer one should be used instead, while the
                    # order of widgets should be follow the place of the older method.
                    widget = attr.__magicclass_wrapped__.__get__(self)
            
            if isinstance(widget, MenuGui):
                # Add menubar to container
                widget.__magicclass_parent__ = self
                if self._menubar is None:
                    self._menubar = QMenuBar(parent=self.native)
                    self.native.layout().setMenuBar(self._menubar)
                
                widget.native.setParent(self._menubar, widget.native.windowFlags())
                self._menubar.addMenu(widget.native)
            
            elif isinstance(widget, Widget) or callable(widget):
                if (not isinstance(widget, Widget)) and callable(widget):
                    # Methods (FunctionGui not included)
                    widget = self._create_widget_from_method(widget)
                
                elif hasattr(widget, "__magicclass_parent__") or \
                    hasattr(widget.__class__, "__magicclass_parent__"):
                    # magic-class has to know its parent.
                    # if __magicclass_parent__ is defined as a property, hasattr must be called
                    # with a type object (not instance).
                    widget.__magicclass_parent__ = self

                elif isinstance(widget, FunctionGui):
                    # magic-class has to know when the nested FunctionGui is called.
                    f = _nested_function_gui_callback(self, widget)
                    widget.called.connect(f)
                    
                else:
                    if not widget.name:
                        widget.name = name.replace("_", " ")
                    if hasattr(widget, "text") and not widget.text:
                        widget.text = widget.name
                
                # Now, "widget" is a Widget object. Add widget in a way similar to "insert" method 
                # of Container.
                
                if not name.startswith("_"):
                    self.insert(n_insert, widget)
                    n_insert += 1
        
        # convert __call__ into a button
        if hasattr(self, "__call__"):
            widget = self._create_widget_from_method(self.__call__)
            self.insert(n_insert, widget)
            n_insert += 1
        
        self._unify_label_widths()

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
                     close_on_run: bool = True,
                     popup: bool = True, 
                     labels: bool = True, 
                     name: str = None, 
                     ):

            container.__init__(self, layout=layout, labels=labels, name=name)
            BaseGui.__init__(self, close_on_run=close_on_run, popup=popup)
            
            if parent is not None:
                self.parent = parent
                
            self._menubar = None
            
            self.native.setObjectName(self.name)
        
        def insert(self: cls, key: int, widget: Widget):
            _hide_labels = (_LabeledWidget, ButtonWidget, ClassGuiBase, FrozenContainer, Label,
                            Image, Table)
                
            if isinstance(widget, ValueWidget):
                widget.changed.connect(lambda: self.changed.emit(self))
            if isinstance(widget, ClassGuiBase) and self._remove_child_margins:
                widget.margins = (0, 0, 0, 0)
                
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
            if isinstance(_widget, BaseGui):
                _widget.native.setParent(self.native, _widget.native.windowFlags())
            self._unify_label_widths()

        
        def show(self: cls, run: bool = False) -> None:
            """
            Show ClassGui. If any of the parent ClassGui is a dock widget in napari, then this
            will also show up as a dock widget (floating if popup=True).
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
                    dock.setFloating(self._popup)
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

@make_gui(ToolBox, no_margin=False)
class ToolBoxClassGui: pass

@make_gui(TabbedContainer, no_margin=False)
class TabbedClassGui: pass

@make_gui(StackedContainer, no_margin=False)
class StackedClassGui: pass

@make_gui(MainWindow)
class MainWindowClassGui: pass

def _nested_function_gui_callback(cgui: ClassGuiBase, fgui: FunctionGui):
    def _after_run():
        inputs = get_parameters(fgui)
        args = [Expr(head=Head.assign, args=[k, v]) for k, v in inputs.items()]
        # args[0] is self
        sub = Expr(head=Head.getattr, args=[cgui._recorded_macro[0].args[0], fgui.name]) # {x}.func
        expr = Expr(head=Head.call, args=[sub] + args[1:]) # {x}.func(args...)

        if fgui._auto_call:
            # Auto-call will cause many redundant macros. To avoid this, only the last input
            # will be recorded in magic-class.
            last_expr = cgui._recorded_macro[-1]
            if last_expr.head == Head.call and last_expr.args[0].head == Head.getattr and \
                last_expr.args[0].args[1] == expr.args[0].args[1]:
                cgui._recorded_macro.pop()

        cgui._recorded_macro.append(expr)
    return _after_run

def _value_widget_callback(cgui: ClassGuiBase, widget: ValueWidget, name: str):
    def _set_value():
        if not widget.enabled:
            # If widget is read only, it means that value is set in script (not manually).
            # Thus this event should not be recorded as a macro.
            return None
        cgui.changed.emit(cgui)
        sub = Expr(head=Head.getattr, args=[name, Symbol("value")]) # name.value
        expr = Expr(head=Head.setattr, args=[Symbol.from_id(cgui), sub, widget.value]) # {x}.name.value = value
        
        last_expr = cgui._recorded_macro[-1]
        if last_expr.head == expr.head and last_expr.args[1].args[0] == expr.args[1].args[0]:
            cgui._recorded_macro[-1] = expr
        else:
            cgui._recorded_macro.append(expr)
        return None
    return _set_value