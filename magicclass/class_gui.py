from __future__ import annotations
from typing import Callable, TYPE_CHECKING
from qtpy.QtWidgets import QMenuBar
from magicgui.widgets import Container, Label, LineEdit, FunctionGui
from magicgui.widgets._bases import Widget, ButtonWidget
from magicgui.widgets._concrete import _LabeledWidget

from .macro import Expr, Head
from .utils import iter_members, extract_tooltip, get_parameters
from .widgets import PushButtonPlus, FrozenContainer
from .field import MagicField
from .menu_gui import MenuGui
from ._base import BaseGui

if TYPE_CHECKING:
    try:
        import napari
    except ImportError:
        pass

class ClassGui(Container, BaseGui):
    # This class is always inherited by @magicclass decorator.
    _component_class = PushButtonPlus
    
    def __init__(self, 
                 layout: str = "vertical", 
                 parent = None, 
                 close_on_run: bool = True,
                 popup: bool = True, 
                 result_widget: bool = False,
                 labels: bool = True, 
                 name: str = None, 
                 single_call: bool = True):
        BaseGui.__init__(self, close_on_run=close_on_run, popup=popup, single_call=single_call)
        Container.__init__(self, layout=layout, labels=labels, name=name)
        
        if parent is not None:
            self.parent = parent
            
        self._menubar = None
        
        self._result_widget: LineEdit | None = None
        if result_widget:
            self._result_widget = LineEdit(gui_only=True, name="result")
            
    
    @property
    def parent_viewer(self) -> "napari.Viewer"|None:
        """
        Return napari.Viewer if self is a dock widget of a viewer.
        """
        current_self = self
        while hasattr(current_self, "__magicclass_parent__") and current_self.__magicclass_parent__:
            current_self = current_self.__magicclass_parent__
        try:
            viewer = current_self.parent.parent().qt_viewer.viewer
        except AttributeError:
            viewer = None
        return viewer
    
    def insert(self, key:int, obj:Widget|Callable) -> None:
        """
        This override enables methods/functions and other magic-class to be appended into Container 
        widgets. Compatible with ``@magicgui`` and ``@magicclass`` decorators inside class. If 
        ``FunctionGui`` object or ``ClassGui`` object was appended, it will appear on the container 
        as is, rather than a push button.
        """        
        
        if (not isinstance(obj, Widget)) and callable(obj):
            obj = self._create_widget_from_method(obj)
        
        elif isinstance(obj, FunctionGui):
            # magic-class has to know when the nested FunctionGui is called.
            f = _nested_function_gui_callback(self, obj)
            obj.called.connect(f)
            
        elif self.labels and not isinstance(obj, (_LabeledWidget, ButtonWidget, ClassGui, 
                                                  FrozenContainer, Label)):
            obj = _LabeledWidget(obj)
            obj.label_changed.connect(self._unify_label_widths)
        
        elif isinstance(obj, ClassGui):
            obj.margins = (0, 0, 0, 0)

        self._list.insert(key, obj)
        if key < 0:
            key += len(self)
            
        self._widget._mgui_insert_widget(key, obj)
        self._unify_label_widths()
        
        return None
    
    def show(self, run: bool = False) -> None:
        """
        Show ClassGui. If any of the parent ClassGui is a dock widget in napari, then this will also show up
        as a dock widget (floating if popup=True).
        """        
        current_self = self
        while hasattr(current_self, "__magicclass_parent__") and current_self.__magicclass_parent__:
            current_self = current_self.__magicclass_parent__
        
        viewer = current_self.parent_viewer
        if viewer is not None:
            dock = viewer.window.add_dock_widget(self, area="right", allowed_areas=["left", "right"])
            dock.setFloating(current_self._popup)
        else:
            super().show(run=run)
            self.native.activateWindow()
        return None
    
    def close(self):
        viewer = self.parent_viewer
        if viewer is not None:
            try:
                viewer.window.remove_dock_widget(self.parent)
            except Exception:
                pass
            
        super().close()
            
        return None
        
    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and nested
        classes are converted to magicgui widgets.
        """        
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            doc = extract_tooltip(cls)
            lbl = Label(value=doc)
            self.append(lbl)
        
        # Bind all the methods and annotations
        base_members = set(x[0] for x in iter_members(ClassGui))        
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if name in ("changed", "_widget"):
                continue

            if isinstance(attr, type):
                # Nested magic-class
                widget = attr()
                setattr(self, name, widget)
            
            elif isinstance(attr, MagicField):
                # If MagicField is given by field() function.
                widget = self._create_widget_from_field(name, attr)
                
            else:
                # convert class method into instance method
                widget = getattr(self, name, None)
            
            if isinstance(widget, ClassGui):
                widget.__magicclass_parent__ = self
                
            elif isinstance(widget, MenuGui):
                widget.__magicclass_parent__ = self
                if self._menubar is None:
                    self._menubar = QMenuBar(parent=self.native)
                    self.native.layout().setMenuBar(self._menubar)
                
                widget.native.setParent(self._menubar, widget.native.windowFlags())
                self._menubar.addMenu(widget.native)
                
            if not name.startswith("_") and (callable(widget) or isinstance(widget, Widget)):
                self.append(widget)
        
        # Append result widget in the bottom
        if self._result_widget is not None:
            self._result_widget.enabled = False
            self.append(self._result_widget)
            
        return None
    
    
def _nested_function_gui_callback(cgui:ClassGui, fgui:FunctionGui):
    def _after_run(e):
        value = e.value
        if isinstance(value, Exception):
            return None
        inputs = get_parameters(fgui)
        args = [Expr(head=Head.assign, args=[k, v]) for k, v in inputs.items()]
        # args[0] is self
        sub = Expr(head=Head.getattr, args=["{x}", fgui.name]) # {x}.func
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
