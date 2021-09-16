from __future__ import annotations
from functools import wraps
from typing import Callable, Any
import inspect
import numpy as np
from contextlib import contextmanager
from docstring_parser import parse
from magicgui import magicgui
from magicgui.widgets import Container, Label, LineEdit, FunctionGui
from magicgui.widgets._bases import Widget, ValueWidget, ButtonWidget
from magicgui.widgets._concrete import _LabeledWidget

from .macro import Macro, Expr, Head
from .utils import iter_members, n_parameters
from .widgets import PushButtonPlus, Separator, Logger, FrozenContainer, raise_error_msg
from .field import MagicField
from .wrappers import upgrade_signature

# Check if napari is available so that layers are detectable from GUIs.
try:
    import napari
except ImportError:
    NAPARI_AVAILABLE = False
else:
    NAPARI_AVAILABLE = True
    

# Running mode determines how to construct magic-class GUI.
# - "default": Error will be raised in message box
# - "debug": Whether function call ended with error will be recorded in a logger widget.
# - "raw": Raise errors in console (non-wrapped mode)
RUNNING_MODE = "default"

LOGGER = Logger(name="logger")

@contextmanager
def debug():
    """
    Magic-classes that are constructed within this context will enter debug mode.
    """    
    global RUNNING_MODE
    current_mode = RUNNING_MODE
    RUNNING_MODE = "debug"
    LOGGER.show()
    yield
    RUNNING_MODE = current_mode

class ClassGui(Container):
    __magicclass_parent__ = None
    def __init__(self, layout:str= "vertical", parent=None, close_on_run:bool=True, popup:bool=True, 
                 result_widget:bool=False, labels:bool=True, name=None):
        super().__init__(layout=layout, labels=labels, name=name)
        if parent is not None:
            self.parent = parent
        self._current_dock_widget = None
        self._close_on_run = close_on_run
        self._popup = popup
        
        self._result_widget: LineEdit | None = None
        if result_widget:
            self._result_widget = LineEdit(gui_only=True, name="result")
            
        self._parameter_history:dict[str, dict[str, Any]] = {}
        self._recorded_macro:Macro[Expr] = Macro()
        self.native.setObjectName(self.__class__.__name__)
            
        if RUNNING_MODE == "debug":
            LOGGER.append(f"{self.__class__.__name__} object at {id(self)}")
    
    @property
    def parent_viewer(self) -> "napari.Viewer"|None:
        """
        Return napari.Viewer if self is a dock widget of a viewer.
        """        
        try:
            viewer = self.parent.parent().qt_viewer.viewer
        except AttributeError:
            viewer = None
        return viewer
    
    def _convert_attributes_into_widgets(self) -> ClassGui:
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            doc = _extract_tooltip(cls)
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
                if issubclass(attr, ClassGui):
                    attr.__magicclass_parent__ = self
                    widget.margins = (0, 0, 0, 0)
                setattr(self, name, widget)
            
            elif isinstance(attr, MagicField):
                # If MagicField is given by field() function.
                widget = self._create_widget_from_field(name, attr)
            else:
                # convert class method into instance method
                widget = getattr(self, name, None)
                
            if callable(widget) or isinstance(widget, Widget):
                self.append(widget)
        
        # Append result widget in the bottom
        if self._result_widget is not None:
            self._result_widget.enabled = False
            self.append(self._result_widget)
            
        return self
    
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
        
        elif self.labels and not isinstance(obj, (_LabeledWidget, ButtonWidget, ClassGui, FrozenContainer, Label)):
            obj = _LabeledWidget(obj)
            obj.label_changed.connect(self._unify_label_widths)

        self._list.insert(key, obj)
        if key < 0:
            key += len(self)
            
        self._widget._mgui_insert_widget(key, obj)
        self._unify_label_widths()
        
        return None
    
    def objectName(self) -> str:
        """
        This function makes the object name discoverable by napari's `viewer.window.add_dock_widget` function.
        """        
        return self.native.objectName()
    
    def show(self, run:bool=False) -> None:
        super().show(run=run)
        self.native.activateWindow()
        return None
    
    def create_macro(self, symbol:str="ui") -> str:
        """
        Create executable Python scripts from the recorded macro object.

        Parameters
        ----------
        symbol : str, default is "ui"
            Symbol of the instance.
        """
        selfvar = f"var{hex(id(self))}"
        macro = _collect_macro(self._recorded_macro, selfvar)
        for name, attr in filter(lambda x: not x[0].startswith("_"), self.__dict__.items()):
            if not isinstance(attr, ClassGui):
                continue
            macro += _collect_macro(attr._recorded_macro, f"{selfvar}.{name}", self.__class__.__name__)

        sorted_macro = map(lambda x: x[1], sorted(macro, key=lambda x: x[0]))
        script =  "\n".join(sorted_macro)
        
        # type annotation
        annot = []
        for expr in self._recorded_macro:
            for idt in expr.iter_args():
                if not idt.valid:
                    annot.append(idt.as_annotation())
        
        out = "\n".join(annot) + "\n" + script
        out = out.replace(selfvar, symbol)
        
        return out
    
    @classmethod
    def wraps(cls, method:Callable) -> Callable:
        """
        Wrap a parent method in a child magic-class.
        
        Basically, this function is used as a wrapper like below.
        
        >>> @magicclass
        >>> class C:
        >>>     @magicclass
        >>>     class D: ...
        >>>     @D.wraps
        >>>     def func(self, ...): ...

        Parameters
        ----------
        method : Callable
            Parent method

        Returns
        -------
        Callable
            Same method as input, but has updated signature to hide the button.
        """        
        # TODO: may need support for FunctionGui?
        funcname = method.__name__
            
        @wraps(method)
        def childmethod(cls_:cls, *args, **kwargs):
            return getattr(cls_.__magicclass_parent__, funcname)(*args, **kwargs)
        
        if hasattr(cls, funcname):
            raise AttributeError(f"Class {cls.__name__} already has attribute {funcname}")
        
        setattr(cls, funcname, childmethod)
        upgrade_signature(method, caller_options={"visible": False})
        return method
    
    def _create_widget_from_field(self, name:str, fld:MagicField):
        cls = self.__class__
        if fld.not_ready():
            try:
                fld.default_factory = cls.__annotations__[name]
            except (AttributeError, KeyError):
                pass
            
        widget = fld.to_widget()
        if widget.name == "" or widget.name == name:
            widget.name = "_" + name
            
        if isinstance(widget, ValueWidget):
            @widget.changed.connect
            def _set_value(event):
                value = event.source.value # TODO: fix after psygnal start to be used.
                setattr(self, name, value)
                self.changed(value=self)
                expr = Expr(head=Head.setattr, args=[name, value])
                last_expr = self._recorded_macro[-1]
                if last_expr.head == expr.head and last_expr.args[0] == expr.args[0]:
                    self._recorded_macro[-1] = expr
                else:
                    self._recorded_macro.append(expr)
                return None
            setattr(self, name, widget.value)
        else:
            setattr(self, name, widget)
        return widget
    
    def _create_widget_from_method(self, obj):
        # Convert methods into push buttons
        name = obj.__name__.replace("_", " ")
        button = PushButtonPlus(name=obj.__name__, text=name, gui_only=True)

        # Wrap function to deal with errors in a right way.
        if RUNNING_MODE == "default":
            wrapper = _raise_error_in_msgbox
        elif RUNNING_MODE == "debug":
            wrapper = _write_log
        elif RUNNING_MODE == "raw":
            wrapper = lambda x, parent: x
        else:
            raise ValueError(f"RUNNING_MODE={RUNNING_MODE}")
        
        func = wrapper(obj, parent=self)
        
        # Strangely, signature must be updated like this. Otherwise, already wrapped member function
        # will have signature with "self".
        func.__signature__ = inspect.signature(obj)

        # Prepare a button
        button.tooltip = _extract_tooltip(func)
        
        if n_parameters(func) == 0:
            # We don't want a dialog with a single widget "Run" to show up.
            def run_function(*args):
                out = func()
                if not isinstance(out, Exception):
                    self._record_macro(func, (), {})
                if self._result_widget is not None:
                    self._result_widget.value = out
                return out
        else:
            def run_function(*args):
                try:
                    mgui = magicgui(func)
                    mgui.name = f"function-{id(func)}"
                        
                except Exception as e:
                    msg = f"Exception was raised during building magicgui.\n{e.__class__.__name__}: {e}"
                    raise_error_msg(self.native, msg=msg)
                    return None
                
                # Recover last inputs if exists.
                params = self._parameter_history.get(func.__name__, {})
                for key, value in params.items():
                    try:
                        getattr(mgui, key).value = value
                    except ValueError:
                        pass
                
                viewer = self.parent_viewer
                    
                if viewer is None:
                    # If napari.Viewer was not found, then open up a magicgui when button is pushed, and 
                    # close it when function call is finished (if close_on_run==True).
                    if self._popup:
                        mgui.show()
                    else:
                        sep = Separator(orientation="horizontal", text=name)
                        mgui.insert(0, sep)
                        self.append(mgui)
                    
                    if self._close_on_run:
                        @mgui.called.connect
                        def _close(value):
                            if not self._popup:
                                self.remove(mgui.name)
                            mgui.close()
                            
                else:
                    # If napari.Viewer was found, then create a magicgui as a dock widget when button is 
                    # pushed, and remove it when function call is finished (if close_on_run==True).
                    viewer: napari.Viewer
                    
                    if self._close_on_run:
                        @mgui.called.connect
                        def _close(value):
                            viewer.window.remove_dock_widget(mgui.parent)
                            mgui.close()
                            
                    dock_name = _find_unique_name(name, viewer)
                    dock = viewer.window.add_dock_widget(mgui, name=dock_name)
                    mgui.native.setParent(dock)
                    dock.setFloating(self._popup)
                
                f = _temporal_function_gui_callback(self, mgui)
                mgui.called.connect(f)
                
                return None
            
        button.changed.connect(run_function)
        
        # If button design is given, load the options.
        button.from_options(obj)
            
        return button
    
    def _record_macro(self, func:Callable, args:tuple, kwargs:dict[str, Any]) -> None:
        """
        Record a function call as a line of macro.

        Parameters
        ----------
        func : str
            Name of function.
        args : tuple
            Arguments.
        kwargs : dict[str, Any]
            Keyword arguments.
        """        
        macro = Expr.parse_method(func, args, kwargs)
        self._recorded_macro.append(macro)
        return None
    
    def _record_parameter_history(self, func:str, kwargs:dict[str, Any]) -> None:
        """
        Record parameter inputs to history for next call.

        Parameters
        ----------
        func : str
            Name of function.
        kwargs : dict[str, Any]
            Parameter inputs.
        """        
        kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, np.ndarray)}
        self._parameter_history.update({func: kwargs})
        return None
    

def _collect_macro(macro:Macro, symbol:str, parent=None) -> list[tuple[int, str]]:
    out = []
    for expr in macro:
        if parent and expr.head == Head.init and expr.args[0].args[0] != parent:
            # nested magic-class construction is always invisible from the parent.
            # We should not record something like 'ui.A = A()'.
            continue
        out.append((expr.number, expr.str_as(symbol)))
    return list((expr.number, expr.str_as(symbol)) for expr in macro)

def _extract_tooltip(obj: Any) -> str:
    if not hasattr(obj, "__doc__"):
        return ""
    
    doc = parse(obj.__doc__)
    if doc.short_description is None:
        return ""
    elif doc.long_description is None:
        return doc.short_description
    else:
        return doc.short_description + "\n" + doc.long_description

def _raise_error_in_msgbox(_func, parent:Widget=None):
    @wraps(_func)
    def wrapped_func(*args, **kwargs):
        try:
            out = _func(*args, **kwargs)
        except Exception as e:
            raise_error_msg(parent.native, title=e.__class__.__name__, msg=str(e))
            out = e
        return out
    
    return wrapped_func

def _write_log(_func, parent=None):
    @wraps(_func)
    def wrapped_func(*args, **kwargs):
        try:
            out = _func(*args, **kwargs)
        except Exception as e:
            log = [f'{parent.__class__.__name__}.{_func.__name__}: '
                   f'<span style="color: red; font-weight: bold;">{e.__class__.__name__}</span>',
                   f'{e}']
            out = e
        else:
            log = f'{parent.__class__.__name__}.{_func.__name__}: ' \
                   '<span style="color: blue; font-weight: bold;">Pass</span>'
        finally:
            LOGGER.append(log)
        return out
    
    return wrapped_func

def _find_unique_name(name:str, viewer:"napari.Viewer"):
    orig_name = name
    i = 0
    while name in viewer.window._dock_widgets:
        name = orig_name + f"-{i}"
        i += 1
    return name

def _get_parameters(mgui):
    inputs = {param: getattr(mgui, param).value
              for param in mgui.__signature__.parameters.keys()
              }
    
    return inputs

def _nested_function_gui_callback(cgui:ClassGui, fgui:FunctionGui):
    def _after_run(e):
        value = e.value
        if isinstance(value, Exception):
            return None
        inputs = _get_parameters(fgui)
        args = [Expr(head=Head.assign, args=[v], symbol=k) for k, v in inputs.items()]
        expr = Expr(head=Head.getattr, 
                    args=[Expr(head=Head.call, 
                                args=args[1:], 
                                symbol=fgui.name)]
                    )
        if fgui._auto_call:
            # Auto-call will cause many redundant macros. To avoid this, only the last input
            # will be recorded in magic-class.
            last_expr = cgui._recorded_macro[-1]
            if last_expr.head == expr.head and \
                last_expr.args[0].symbol == expr.args[0].symbol:
                cgui._recorded_macro.pop()

        cgui._recorded_macro.append(expr)
    return _after_run

def _temporal_function_gui_callback(cgui:ClassGui, fgui:FunctionGui):
    def _after_run(value):
        if isinstance(value, Exception):
            return None
        inputs = _get_parameters(fgui)
        cgui._record_macro(fgui._function, (), inputs)
        cgui._record_parameter_history(fgui._function.__name__, inputs)
            
        if cgui._result_widget is not None:
            cgui._result_widget.value = value
    return _after_run