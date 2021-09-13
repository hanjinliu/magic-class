from __future__ import annotations
from enum import Enum, auto
from functools import wraps
from typing import Callable, Iterable, Any
import inspect
from contextlib import contextmanager
import numpy as np
from pathlib import Path
from magicgui import magicgui
from magicgui.widgets import Container, Label, LineEdit
from magicgui.widgets._bases import Widget, ValueWidget

from .utils import InlineClass, iter_members_and_annotations
from .widgets import PushButtonPlus, Separator, Logger, raise_error_msg

# Check if napari is available so that layers are detectable from GUIs.
try:
    import napari
except ImportError:
    NAPARI_AVAILABLE = False
else:
    NAPARI_AVAILABLE = True
    
_HARD_TO_RECORD = (np.ndarray,) # This is a temporal solution to avoid recording layer as an numpy

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

# BUG: Method name "func" causes application to break.

class ClassGui(Container):
    def __init__(self, layout:str= "vertical", parent=None, close_on_run:bool=True, popup:bool=True, 
                 result_widget:bool=False, name=None):
        super().__init__(layout=layout, labels=False, name=name)
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
    
    def _convert_methods_into_widgets(self) -> ClassGui:
        cls = self.__class__
        cls_annotations = cls.__annotations__
        
        # Add class docstring as label.
        if cls.__doc__:
            doc = cls.__doc__.strip()
            lbl = Label(value=doc)
            self.append(lbl)
        
        def _define_set_value(name):
            def _set_value(event):
                value = event.source.value # TODO: fix after psygnal start to be used.
                args = [name, value]
                expr = Expr(head=Head.setattr, args=args)
                last_expr = self._recorded_macro[-1]
                if last_expr.head == Head.setattr and last_expr.args[0][1:-1] == name:
                    self._recorded_macro[-1] = expr
                else:
                    self._recorded_macro.append(expr)
                return None
            return _set_value
                
        # Bind all the methods and annotations
        base_members = set(iter_members_and_annotations(ClassGui))
        for name in filter(lambda x: x not in base_members, iter_members_and_annotations(cls)):
            if name in cls_annotations.keys():
                widgetclass = cls_annotations[name]
                if not issubclass(widgetclass, Widget):
                    continue
                
                if not issubclass(widgetclass, InlineClass):
                    # Class widgetclass was not defined in an inline way. Widget may
                    # appear in a wrong position because magicclass cannot determine
                    # its line number. 
                    pass
                
                if hasattr(self, name) and isinstance(getattr(self, name), Widget):
                    # If the annotation has a default value, same widget will be created
                    # twice.
                    continue
                
                attr = widgetclass()
                setattr(self, name, attr)
                
            else:
                attr = getattr(self, name, None)
                
            if isinstance(attr, ValueWidget):
                attr.changed.connect(_define_set_value(name))
                        
            if callable(attr) or isinstance(attr, (type, Widget)):
                self.append(attr)
        
        # Append result widget in the bottom
        if self._result_widget is not None:
            self._result_widget.enabled = False
            self.append(self._result_widget)
        return self
    
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
        kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, _HARD_TO_RECORD)}
        self._parameter_history.update({func: kwargs})
        return None
    
    def append(self, obj:Widget|Callable|type) -> None:
        """
        This override enables methods/functions and other magic-class to be appended into Container 
        widgets. Compatible with ``@magicgui`` and ``@magicclass`` decorators inside class. If 
        ``FunctionGui`` object or ``ClassGui`` object was appended, it will appear on the container 
        as is, rather than a push button.
        """        
        if isinstance(obj, type):
            # Inline class definition
            acceptable = Widget
            if issubclass(obj, acceptable):
                obj = obj()
            else:
                raise TypeError(
                    f"Cannot append class except for {acceptable.__name__} (got {obj.__name__})"
                    )
            
        elif (not isinstance(obj, Widget)) and callable(obj):
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
            button.tooltip = func.__doc__.strip() if func.__doc__ else ""
            
            if len(inspect.signature(func).parameters) == 0:
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
                    func_obj_name = f"function-{id(func)}"
                    try:
                        mgui = magicgui(func)
                        mgui.name = func_obj_name
                            
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
                    
                    @mgui.called.connect
                    def _after_run(value):
                        if isinstance(value, Exception):
                            return None
                        inputs = _get_parameters(mgui)
                        self._record_macro(func, (), inputs)
                        self._record_parameter_history(func.__name__, inputs)
                        if self._close_on_run:
                            if not self._popup:
                                try:
                                    self.remove(func_obj_name)
                                except ValueError:
                                    pass
                            mgui.close()
                            
                        if self._result_widget is not None:
                            self._result_widget.value = value
                        
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
                                    self.remove(func_obj_name)
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
                    
                    return None
                
            button.changed.connect(run_function)
            
            # If button design is given, load the options.
            try:
                options = obj.__signature__.caller_options
            except AttributeError:
                pass
            else:
                button.from_options(options)
                
            obj = button
        
        return super().append(obj)
    
    def objectName(self) -> str:
        """
        This function makes the object name discoverable by napari's `viewer.window.add_dock_widget` function.
        """        
        return self.native.objectName()
    
    def show(self, run:bool=False) -> None:
        super().show(run=run)
        self.native.activateWindow()
        return None
    
    def create_macro(self, symbol:str="ui") -> list[str]:
        macro: list[tuple[int, str]]
        macro = _collect_macro(self._recorded_macro, symbol)
        for name, attr in filter(lambda x: not x[0].startswith("_"), self.__dict__.items()):
            if not isinstance(attr, ClassGui):
                continue
            macro += _collect_macro(attr._recorded_macro, f"{symbol}.{name}")

        sorted_macro = map(lambda x: x[1], sorted(macro, key=lambda x: x[0]))
        return "\n".join(sorted_macro)

def _collect_macro(macro:Macro, symbol:str) -> list[tuple[int, str]]:
    return list((expr.number, expr.str_as(symbol)) for expr in macro)

def _raise_error_in_msgbox(func, parent:Widget=None):
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        try:
            out = func(*args, **kwargs)
        except Exception as e:
            raise_error_msg(parent.native, title=e.__class__.__name__, msg=str(e))
            out = e
        return out
    
    return wrapped_func

def _write_log(func, parent=None):
    @wraps(func)
    def wrapped_func(*args, **kwargs):
        try:
            out = func(*args, **kwargs)
        except Exception as e:
            log = [f'{parent.__class__.__name__}.{func.__name__}: '
                   f'<span style="color: red; font-weight: bold;">{e.__class__.__name__}</span>',
                   f'{e}']
            out = e
        else:
            log = f'{parent.__class__.__name__}.{func.__name__}: ' \
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

def _safe_str(obj):
    if isinstance(obj, _HARD_TO_RECORD):
        out = f"var{id(obj)}"
    elif isinstance(obj, Path):
        out = f"r'{obj}'"
    elif hasattr(obj, "__name__"):
        out = obj.__name__
    elif isinstance(obj, str):
        out = repr(obj)
    else:
        out = str(obj)
    return out

class Macro(list):
    def append(self, __object:Expr):
        if not isinstance(__object, Expr):
            raise TypeError("Cannot append objects to Macro except for MacroExpr objecs.")
        return super().append(__object)
    
    def __str__(self) -> str:
        return "\n".join(map(str, self))
        
class Head(Enum):
    construction = auto()
    method = auto()
    getattr = auto()
    setattr = auto()
    getitem = auto()
    setitem = auto()
    call = auto()
    setvalue = auto()
    comment = auto()

class Expr:
    n = 0
    def __init__(self, head:Head, args:Iterable[Any], symbol:str="ui"):
        self.head = head
        self.args = [_safe_str(a) for a in args]
        self.symbol = symbol
        self.number = self.__class__.n
        self.__class__.n += 1
    
    def __repr__(self) -> str:
        out = [f"head: {self.head.name}\nargs:\n"]
        for i, arg in enumerate(self.args):
            out.append(f"    {i}: {arg}\n")
        return "".join(out)
    
    def __str__(self) -> str:
        func, *vals = self.args
        if self.head == Head.construction:
            line = f"{self.symbol} = {func}({', '.join(vals)})"
        elif self.head == Head.method:
            line = f"{self.symbol}.{func}({', '.join(vals)})"
        elif self.head == Head.getattr:
            line = f"{self.symbol}.{self.args[0][1:-1]}"
        elif self.head == Head.setattr:
            line = f"{self.symbol}.{self.args[0][1:-1]} = {self.args[1]}"
        elif self.head == Head.getitem:
            line = f"{self.symbol}[{self.args[0]}]"
        elif self.head == Head.setitem:
            line = f"{self.symbol}[{self.args[0]}] = {self.args[1]}"
        elif self.head == Head.call:
            line = f"{self.symbol}{tuple(self.args)}"
        elif self.head == Head.comment:
            line = f"# {self.args[0]}"
        elif self.head == Head.setvalue:
            line = f"{self.symbol}={self.args[0]}"
        else:
            raise ValueError(self.head)
        return line
    
    @classmethod
    def parse_method(cls, func:Callable, args:tuple[Any], kwargs:dict[str, Any], symbol:str="ui"):
        head = Head.method
        inputs = [func]
        for a in args:
            inputs.append(a)
                
        for k, v in kwargs.items():
            inputs.append(cls(Head.setvalue, [v], symbol=k))
        return cls(head=head, args=inputs, symbol=symbol)

    @classmethod
    def parse_init(cls, other_cls:type, args:tuple[Any], kwargs:dict[str, Any], symbol:str="ui"):
        self = cls.parse_method(other_cls, args, kwargs, symbol=symbol)
        self.head = Head.construction
        return self
    
    def str_as(self, symbol:str):
        old_symbol = self.symbol
        self.symbol = symbol
        out = str(self)
        self.symbol = old_symbol
        return out