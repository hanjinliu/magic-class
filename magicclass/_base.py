from __future__ import annotations
from functools import wraps
from typing import Callable, Any
import inspect
import numpy as np
from copy import deepcopy
from magicgui import magicgui
from magicgui.widgets import FunctionGui, FileEdit, Container
from magicgui.widgets._bases import ValueWidget

from .macro import Macro, Expr, Head
from .utils import (define_callback, n_parameters, extract_tooltip, raise_error_in_msgbox,
                    raise_error_msg, get_parameters, find_unique_name, show_mgui)
from .widgets import Separator, Logger
from .field import MagicField
from .wrappers import upgrade_signature

# Check if napari is available so that layers are detectable from GUIs.
try:
    import napari
except ImportError:
    NAPARI_AVAILABLE = False
else:
    NAPARI_AVAILABLE = True

class BaseGui:
    _component_class: type = None
    
    def __init__(self, close_on_run=True, popup=True, single_call=True):
        self._recorded_macro: Macro[Expr] = Macro()
        self._parameter_history: dict[str, dict[str, Any]] = {}
        self.__magicclass_parent__: None|BaseGui = None
        self._popup = popup
        self._close_on_run = close_on_run
        self._result_widget = None
        self._single_call = single_call
    
    def create_macro(self, show: bool = False, symbol: str = "ui") -> str:
        """
        Create executable Python scripts from the recorded macro object.

        Parameters
        ----------
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
            win = Logger(name="macro")
            win.read_only = False
            win.append(out.split("\n"))
            viewer = self.parent_viewer
            if viewer is not None:
                dock = viewer.window.add_dock_widget(win, area="right", name="Macro",
                                                     allowed_areas=["left", "right"])
                dock.setFloating(self._popup)
            else:
                win.show()
        return out
    
    def _collect_macro(self, myname:str=None) -> list[tuple[int, Expr]]:
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
        
        for name, attr in filter(lambda x: not x[0].startswith("__"), self.__dict__.items()):
            # Collect all the macro from child magic-classes recursively
            if not isinstance(attr, BaseGui):
                continue
            out += attr._collect_macro(myname=name)
        
        return out
    
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
    
    def create_macro(self, show:bool=False, symbol:str="ui") -> str:
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
            win = Logger(name="macro")
            win.read_only = False
            win.append(out.split("\n"))
            viewer = self.parent_viewer
            if viewer is not None:
                dock = viewer.window.add_dock_widget(win, area="right", name="Macro",
                                                     allowed_areas=["left", "right"])
                dock.setFloating(self._popup)
            else:
                win.show()
        return out
    
    @classmethod
    def wraps(cls, method: Callable) -> Callable:
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
        # Base function to get access to the original function
        def _childmethod(self:cls, *args, **kwargs):
            current_self = self.__magicclass_parent__
            while not (hasattr(current_self, funcname) and 
                        current_self.__class__.__name__ == clsname):
                current_self = current_self.__magicclass_parent__
            return getattr(current_self, funcname)(*args, **kwargs)
        
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
            childmethod = magicgui(**options)(wraps(method)(_childmethod))
            method = _copy_function(method)

        else:
            clsname, funcname = method.__qualname__.split(".")
            childmethod = wraps(method)(_childmethod)
        
        # To avoid two buttons with same bound function being showed up
        upgrade_signature(method, caller_options={"visible": False})
        
        if hasattr(cls, funcname):
            # Sometimes we want to pre-define function to arrange the order of widgets.
            # By updating __wrapped__ attribute we can overwrite the line number
            childmethod.__wrapped__ = getattr(cls, funcname)
        
        if hasattr(method, "__doc__"):
            childmethod.__doc__ = method.__doc__
        setattr(cls, funcname, childmethod)
        return method
    
    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and nested
        classes are converted to magicgui widgets.
        """        
        raise NotImplementedError()
    
    
    def _create_widget_from_field(self, name:str, fld:MagicField):
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
        widget.name = widget.name or name
            
        if isinstance(widget, (ValueWidget, Container)):
            # If the field has callbacks, connect it to the newly generated widget.
            for callback in fld.callbacks:
                # funcname = callback.__name__
                widget.changed.connect(define_callback(self, callback))
                
            if hasattr(widget, "value"):        
                # By default, set value function will be connected to the widget.
                @widget.changed.connect
                def _set_value(event):
                    if not event.source.enabled:
                        # If widget is read only, it means that value is set in script (not manually).
                        # Thus this event should not be recorded as a macro.
                        return None
                    value = event.source.value # TODO: fix after psygnal start to be used.
                    self.changed(value=self)
                    if isinstance(value, Exception):
                        return None
                    sub = Expr(head=Head.getattr, args=[name, "value"]) # name.value
                    expr = Expr(head=Head.setattr, args=["{x}", sub, value]) # {x}.name.value = value
                    
                    last_expr = self._recorded_macro[-1]
                    if last_expr.head == expr.head and last_expr.args[1].args[0] == expr.args[1].args[0]:
                        self._recorded_macro[-1] = expr
                    else:
                        self._recorded_macro.append(expr)
                    return None
        
        setattr(self, name, widget)
        return widget
    
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
                    mgui[0].value = result
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
                
                viewer = self.parent_viewer
                                    
                if viewer is None:
                    # If napari.Viewer was not found, then open up a magicgui when button is pushed, and 
                    # close it when function call is finished (if close_on_run==True).
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
                            
                else:
                    # If napari.Viewer was found, then create a magicgui as a dock widget when button is 
                    # pushed, and remove it when function call is finished (if close_on_run==True).
                    viewer: napari.Viewer
                    
                    if self._close_on_run:
                        @mgui.called.connect
                        def _close(value):
                            viewer.window.remove_dock_widget(mgui.parent)
                            mgui.close()
                            
                    dock_name = find_unique_name(text, viewer)
                    dock = viewer.window.add_dock_widget(mgui, name=dock_name)
                    dock.setFloating(self._popup)
                
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
        
        if len(widget.changed.callbacks) > 1:
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
    @wraps(f)
    def out(self, *args, **kwargs):
        return f(self, *args, **kwargs)
    return out