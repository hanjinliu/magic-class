from __future__ import annotations
from typing import TYPE_CHECKING
import warnings
from qtpy.QtWidgets import QMenuBar, QToolBar
from magicgui.widgets import Container, Label, LineEdit, FunctionGui
from magicgui.widgets._bases import Widget, ButtonWidget
from magicgui.widgets._concrete import _LabeledWidget

from .macro import Expr, Head
from .utils import iter_members, extract_tooltip, get_parameters
from .widgets import PushButtonPlus, FrozenContainer
from .field import MagicField
from .menu_gui import MenuGui
from .containers import ScrollableContainer, CollapsibleContainer
from ._base import BaseGui

if TYPE_CHECKING:
    try:
        import napari
    except ImportError:
        pass
    
class ClassGuiBase(BaseGui):
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
                 single_call: bool = True
                 ):
        Container.__init__(self, layout=layout, labels=labels, name=name)
        BaseGui.__init__(self, close_on_run=close_on_run, popup=popup, single_call=single_call)
        
        if parent is not None:
            self.parent = parent
            
        self._menubar: QMenuBar | None = None
        self._toolbar: QToolBar | None = None
        
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
        base_members = set(x[0] for x in iter_members(Container)) | set(x[0] for x in iter_members(ClassGuiBase))
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if name in ClassGuiBase.__annotations__.keys() or name.startswith("_"):
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
            
            if isinstance(widget, MenuGui):
                widget.__magicclass_parent__ = self
                if self._menubar is None:
                    self._menubar = QMenuBar(parent=self.native)
                    self.native.layout().setMenuBar(self._menubar)
                
                widget.native.setParent(self._menubar, widget.native.windowFlags())
                self._menubar.addMenu(widget.native)
            
            elif isinstance(widget, Widget) or callable(widget):
                if (not isinstance(widget, Widget)) and callable(widget):
                    widget = self._create_widget_from_method(widget)
                
                elif isinstance(widget, ClassGuiBase):
                    widget.__magicclass_parent__ = self
                    widget.margins = (0, 0, 0, 0)
            
                if isinstance(widget, FunctionGui):
                    # magic-class has to know when the nested FunctionGui is called.
                    # BUG: only one FunctionGui will be added
                    f = _nested_function_gui_callback(self, widget)
                    widget.called.connect(f)
                    
                elif self.labels and not isinstance(widget, (_LabeledWidget, ButtonWidget, ClassGuiBase, 
                                                        FrozenContainer, Label)):
                    widget = _LabeledWidget(widget)
                    widget.label_changed.connect(self._unify_label_widths)
            
                try:
                    self.append(widget)
                except Exception as e:
                    msg = f"Could not convert {attr!r} into a widget due to {type(e)}: {e}"
                    warnings.warn(msg, UserWarning)
                
        # Append result widget in the bottom
        if self._result_widget is not None:
            self._result_widget.enabled = False
            self.append(self._result_widget)
            
        return None

def make_gui(container):
    def wrapper(cls):
        cls = type(cls.__name__, (container, ClassGuiBase), {})
        def __init__(self, 
                    layout: str = "vertical", 
                    parent = None, 
                    close_on_run: bool = True,
                    popup: bool = True, 
                    result_widget: bool = False,
                    labels: bool = True, 
                    name: str = None, 
                    single_call: bool = True
                    ):
            container.__init__(self, layout=layout, labels=labels, name=name)
            BaseGui.__init__(self, close_on_run=close_on_run, popup=popup, single_call=single_call)
            
            if parent is not None:
                self.parent = parent
                
            self._menubar = None
            self._toolbar = None
            
            self._result_widget = None
            if result_widget:
                self._result_widget = LineEdit(gui_only=True, name="result")
        cls.__init__ = __init__
        return cls
    return wrapper


@make_gui(Container)
class ClassGui: pass

@make_gui(ScrollableContainer)
class ScrollableClassGui: pass

@make_gui(CollapsibleContainer)
class CollapsibleClassGui: pass

def _nested_function_gui_callback(cgui: ClassGui, fgui: FunctionGui):
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
