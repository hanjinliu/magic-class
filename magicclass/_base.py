from __future__ import annotations
from functools import wraps as fwraps
from typing import Callable, Any, TYPE_CHECKING, TypeVar
import inspect
import numpy as np
from copy import deepcopy
from qtpy.QtGui import QFont
from magicgui import magicgui
from magicgui.widgets import FunctionGui, FileEdit, TextEdit

from .macro import Macro, Expr, Head
from .utils import (iter_members, n_parameters, extract_tooltip, raise_error_in_msgbox,
                    raise_error_msg, get_parameters, show_mgui)
from .widgets import Separator
from .field import MagicField
from .wrappers import upgrade_signature

# Check if napari is available so that layers are detectable from GUIs.
if TYPE_CHECKING:
    try:
        import napari
    except ImportError:
        pass

class BaseGui:
    _component_class: type = None
    
    def __init__(self, close_on_run = True, popup = True, single_call = True):
        self._recorded_macro: Macro[Expr] = Macro()
        self._parameter_history: dict[str, dict[str, Any]] = {}
        self.__magicclass_parent__: None|BaseGui = None
        self._popup = popup
        self._close_on_run = close_on_run
        self._result_widget = None
        self._single_call = single_call
    
    
    def _collect_macro(self, myname: str = None) -> list[tuple[int, Expr]]:
        out = []
        macro = deepcopy(self._recorded_macro)
        
        for expr in macro:
            if expr.head == Head.init:
                # nested magic-class construction is always invisible from the parent.
                # We should not record something like 'ui.A = A()'.
                continue
            
            if myname is not None:
                for _expr in expr.iter_expr():
                    # if _expr.head in (Head.value, Head.getattr, Head.getitem):
                    if _expr.args[0] == "{x}":
                        _expr.args[0] = Expr(Head.getattr, args=["{x}", myname])
                
            out.append((expr.number, expr))
        
        if myname is not None:
            prefix = myname + "."
        else:
            prefix = ""
        
        for name, attr in filter(lambda x: not x[0].startswith("__"), self.__dict__.items()):
            # Collect all the macro from child magic-classes recursively
            if not isinstance(attr, BaseGui):
                continue
            out += attr._collect_macro(myname=prefix+name)
        
        return out
    
    def _record_macro(self, func: Callable, args: tuple, kwargs: dict[str, Any]) -> None:
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
    
    def objectName(self) -> str:
        """
        This function makes the object name discoverable by napari's `viewer.window.add_dock_widget` function.
        """        
        return self.native.objectName()
    
    def create_macro(self, show: bool = False, symbol: str = "ui") -> str:
        """
        Create executable Python scripts from the recorded macro object.

        Parameters
        ----------
        show : bool, default is False
            Launch a TextEdit window that shows recorded macro.
        symbol : str, default is "ui"
            Symbol of the instance.
        """
        # Recursively build macro from nested magic-classes
        macro = [(0, self._recorded_macro[0])] + self._collect_macro()

        # Sort by the recorded order
        sorted_macro = map(lambda x: str(x[1]), sorted(macro, key=lambda x: x[0]))
        script = "\n".join(sorted_macro)
        
        # type annotation for the hard-to-record types
        annot = []
        idt_list = []
        for expr in self._recorded_macro:
            for idt in expr.iter_args():
                if idt.valid or idt in idt_list:
                    continue
                idt_list.append(idt)
                annot.append(idt.as_annotation())
        
        out = "\n".join(annot) + "\n" + script
        out = out.format(x=symbol)
        
        if show:
            win = TextEdit(name="macro")
            win.native.setFont(QFont("Consolas"))
            win.read_only = False
            for text in out.split("\n"):
                win.native.append(text)
            vbar = win.native.verticalScrollBar()
            vbar.setValue(vbar.maximum())
            
            win.native.setParent(self.native, win.native.windowFlags())
            
        return out
    
    @classmethod
    def wraps(cls, method: Callable | None = None, *, template: Callable | None = None) -> Callable:
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
        method : Callable, optional
            Method of parent class.
        template : Callable, optional
            Function template for signature.
            
        Returns
        -------
        Callable
            Same method as input, but has updated signature to hide the button.
        """      
        def wrapper(method: Callable):
            # Base function to get access to the original function
            def _childmethod(self: cls, *args, **kwargs):
                current_self = self.__magicclass_parent__
                while not (hasattr(current_self, funcname) and 
                            current_self.__class__.__name__ == clsname):
                    current_self = current_self.__magicclass_parent__
                return getattr(current_self, funcname)(*args, **kwargs)
            
            # Must be template as long as this wrapper function is called
            if template is None:
                _wrap_func = fwraps(method)
            else:
                def _wrap_func(f):
                    f = _wraps(template, reference=method)(f)
                    f.__wrapped__ = method
                    f.__name__ = method.__name__
                    f.__qualname__ = method.__qualname__
                    return f
                    
            # If method is defined as a member of class X, __qualname__ will be X.<method name>.
            # We can know the namespace of the wrapped function with __qualname__.
            if isinstance(method, FunctionGui):
                clsname, funcname = method._function.__qualname__.split(".")
                options = dict(call_button=method._call_button.text if method._call_button else None,
                            layout=method.layout,
                            labels=method.labels,
                            auto_call=method._auto_call,
                            result_widget=bool(method._result_widget)
                            )
                method = method._function
                childmethod = magicgui(**options)(_wrap_func(_childmethod))
                method = _copy_function(method)
            
            else:
                clsname, funcname = method.__qualname__.split(".")
                childmethod = _wrap_func(_childmethod)
            
            # To avoid two buttons with same bound function being showed up
            upgrade_signature(method, caller_options={"visible": False})
            
            if hasattr(method, "__doc__"):
                childmethod.__doc__ = method.__doc__
            
            if hasattr(cls, funcname):
                # Sometimes we want to pre-define function to arrange the order of widgets.
                getattr(cls, funcname).__wrapped__ = childmethod
                getattr(cls, funcname).__magicclass_wrapped__ = childmethod
            else:
                setattr(cls, funcname, childmethod)
            return method
        
        return wrapper if method is None else wrapper(method)
    
    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and nested
        classes are converted to magicgui widgets.
        """        
        raise NotImplementedError()
    
    
    def _create_widget_from_field(self, name: str, fld: MagicField):
        """
        This function is called when magic-class encountered a MagicField in its definition.

        Parameters
        ----------
        name : str
            Name of variable
        fld : MagicField
            A field object that describes what type of widget it should be.
        """        
        raise NotImplementedError()
    
    def _create_widget_from_method(self, obj):
        text = obj.__name__.replace("_", " ")
        widget = self._component_class(name=obj.__name__, text=text, gui_only=True)

        # Wrap function to deal with errors in a right way.
        wrapper = raise_error_in_msgbox
        
        func = wrapper(obj, parent=self)
        
        # Signature must be updated like this. Otherwise, already wrapped member function
        # will have signature with "self".
        func.__signature__ = inspect.signature(obj)
        
        # Prepare a button or action
        widget.tooltip = extract_tooltip(func)
        
        if n_parameters(func) == 0:
            # We don't want a dialog with a single widget "Run" to show up.
            callback = _temporal_function_gui_callback(self, func, widget)
            def run_function(*args):
                out = func()
                callback(out)
                return out
            
        elif n_parameters(func) == 1 and type(FunctionGui.from_callable(func)[0]) is FileEdit:
            # We don't want to open a magicgui dialog and again open a file dialog.
            def run_function(*args):
                mgui = magicgui(func)
                mgui.name = f"function-{id(func)}"
                widget.mgui = mgui
                
                callback = _temporal_function_gui_callback(self, mgui, widget)
                params = self._parameter_history.get(func.__name__, {})
                path = "."
                for key, value in params.items():
                    getattr(widget.mgui, key).value = value
                    path = str(value)
                
                fdialog: FileEdit = widget.mgui[0]
                result = fdialog._show_file_dialog(
                    fdialog.mode,
                    caption=fdialog._btn_text,
                    start_path=path,
                    filter=fdialog.filter,
                )
                if result:
                    fdialog.value = result
                    out = func(result)
                    callback(out)
                else:
                    out = None
                return out
            
        else:
            def run_function(*args):
                if widget.mgui is not None and self._single_call:
                    show_mgui(widget.mgui)
                    return None
                try:
                    mgui = magicgui(func)
                    mgui.name = f"function-{id(func)}"
                        
                except Exception as e:
                    msg = f"Exception was raised during building magicgui.\n{e.__class__.__name__}: {e}"
                    raise_error_msg(self.native, msg=msg)
                    raise e
                
                # Recover last inputs if exists.
                params = self._parameter_history.get(func.__name__, {})
                for key, value in params.items():
                    try:
                        getattr(mgui, key).value = value
                    except ValueError:
                        pass
                    
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                    
                if self._popup:
                    mgui.show()
                else:
                    current_self = self
                    while (hasattr(current_self, "__magicclass_parent__") 
                            and current_self.__magicclass_parent__):
                        current_self = current_self.__magicclass_parent__
                    
                    sep = Separator(orientation="horizontal", text=text)
                    mgui.insert(0, sep)
                    current_self.append(mgui)
                
                if self._close_on_run:
                    @mgui.called.connect
                    def _close(value):
                        if not self._popup:
                            current_self = self
                            while (hasattr(current_self, "__magicclass_parent__") 
                                and current_self.__magicclass_parent__):
                                current_self = current_self.__magicclass_parent__
                            current_self.remove(mgui)
                        mgui.close()
                
                callback = _temporal_function_gui_callback(self, mgui, widget)
                mgui.called.connect(callback)
                widget.mgui = mgui
                return None
            
        widget.changed.connect(run_function)
        
        # If design is given, load the options.
        widget.from_options(obj)
            
        return widget
    
def _temporal_function_gui_callback(bgui: BaseGui, fgui: FunctionGui|Callable, widget):
    def _after_run(value):
        if isinstance(value, Exception):
            return None
        
        if isinstance(fgui, FunctionGui):
            inputs = get_parameters(fgui)
            bgui._record_parameter_history(fgui._function.__name__, inputs)
            _function = fgui._function
        else:
            inputs = {}
            _function = fgui
        
        # Standard button will be connected with two callbacks.
        # 1. Build FunctionGui
        # 2. Emit value changed signal.
        # But if there are more, they also have to be called.
        if len(widget.changed.callbacks) > 2:
            b = Expr(head=Head.getitem, args=["{x}", widget.name])
            ev = Expr(head=Head.getattr, args=[b, "changed"])
            macro = Expr(head=Head.call, args=[ev])
            bgui._recorded_macro.append(macro)
        else:
            bgui._record_macro(_function, (), inputs)
        
        if bgui._result_widget is not None:
            bgui._result_widget.value = value
            
        widget.mgui = None
    return _after_run

def _copy_function(f):
    @fwraps(f)
    def out(self, *args, **kwargs):
        return f(self, *args, **kwargs)
    return out


_C = TypeVar("_C", Callable, type)

def wraps(template: Callable | inspect.Signature) -> Callable:
    """
    Update signature using a template.

    Parameters
    ----------
    template : Callable or inspect.Signature object
        Template function or its signature.

    Returns
    -------
    Callable
        Same function with updated signature.
    """    
    return _wraps(template)

def _wraps(template: Callable | inspect.Signature, reference: Callable = None) -> Callable:
    def wrapper(f: _C) -> _C:
        if isinstance(f, type):
            for name, attr in iter_members(f):
                if callable(attr) or isinstance(attr, type):
                    wrapper(attr)
            return f
        
        Param = inspect.Parameter
        if reference is None:
            old_signature = inspect.signature(f)
        else:
            old_signature = inspect.signature(reference)
            
        old_params = old_signature.parameters
        
        if callable(template):
            template_signature = inspect.signature(template)
        elif isinstance(template, inspect.Signature):
            template_signature = template
        else:
            raise TypeError(f"template must be a callable object or signature, but got {type(template)}.")
        
        # update empty signatures
        template_params = template_signature.parameters
        new_params: list[Param] = []
        
        for k, v in old_params.items():
            if v.annotation is inspect._empty and v.default is inspect._empty:
                new_params.append(
                    template_params.get(k, 
                                        Param(k, Param.POSITIONAL_OR_KEYWORD)
                                        )
                    )
            else:
                new_params.append(v)
        
        # update empty return annotation
        if old_signature.return_annotation is inspect._empty:
            return_annotation = template_signature.return_annotation
        else:
            return_annotation = old_signature.return_annotation
        
        f.__signature__ = inspect.Signature(
            parameters=new_params,
            return_annotation=return_annotation
            )
        return f
    return wrapper
    