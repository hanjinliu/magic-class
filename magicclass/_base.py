from __future__ import annotations
from functools import wraps as functools_wraps
from typing import Callable, TYPE_CHECKING, TypeVar
import inspect
from enum import Enum
import warnings
from magicgui import magicgui
from magicgui.signature import MagicParameter
from magicgui.widgets import FunctionGui, FileEdit, EmptyWidget

from magicclass.signature import MagicMethodSignature

from .macro import Macro, Expr, Head, Symbol, symbol
from .utils import iter_members, n_parameters, extract_tooltip, raise_error_in_msgbox, id_wrapper
from .widgets import Separator, ConsoleTextEdit
from .mgui_ext import FunctionGuiPlus
from .field import MagicField
from .wrappers import upgrade_signature

if TYPE_CHECKING:
    try:
        import napari
    except ImportError:
        pass
    
class PopUpMode(Enum):
    popup = "popup"
    first = "first"
    last = "last"
    above = "above"
    below = "below"
    dock = "dock"
    parentlast = "parentlast"

class ErrorMode(Enum):
    msgbox = "msgbox"
    stderr = "stderr"
    
defaults = {"popup_mode": PopUpMode.popup,
            "error_mode": ErrorMode.msgbox,
            "close_on_run": True,
            }

class BaseGui:
    _component_class: type = None
    
    def __init__(self, close_on_run, popup_mode, error_mode):
        self._recorded_macro: Macro[Expr] = Macro()
        self.__magicclass_parent__: None | BaseGui = None
        self._close_on_run = close_on_run
        self._popup_mode = popup_mode
        self._error_mode = error_mode
    
    def _collect_macro(self, parent_symbol: Symbol = None, self_symbol: Symbol = None) -> Macro:
        if self_symbol is None:
            self_symbol = symbol(self)
        
        if parent_symbol is not None:
            self_symbol = Expr(Head.getattr, [parent_symbol, self_symbol])
        
        sym = symbol(self)
        macro = Macro()
        for expr in self._recorded_macro:
            if parent_symbol is not None and expr.head == Head.init:
                continue
            macro.append(expr.format({sym: self_symbol}))
        
        for name, attr in filter(lambda x: not x[0].startswith("__"), self.__dict__.items()):
            # Collect all the macro from child magic-classes recursively
            if not isinstance(attr, BaseGui):
                continue
            macro += attr._collect_macro(self_symbol, Symbol(name))
                
        return macro
    
    @property
    def parent_viewer(self) -> "napari.Viewer" | None:
        """
        Return napari.Viewer if self is a dock widget of a viewer.
        """
        parent_self = self._search_parent_magicclass()
        try:
            viewer = parent_self.parent.parent().qt_viewer.viewer
        except AttributeError:
            viewer = None
        return viewer
    
    def objectName(self) -> str:
        """
        This function makes the object name discoverable by napari's 
        `viewer.window.add_dock_widget` function.
        """        
        return self.native.objectName()
    
    def create_macro(self, show: bool = False, myname: str = "ui") -> str:
        """
        Create executable Python scripts from the recorded macro object.

        Parameters
        ----------
        show : bool, default is False
            Launch a TextEdit window that shows recorded macro.
        myname : str, default is "ui"
            Symbol of the instance.
        """
        # Recursively build macro from nested magic-classes
        macro = self._collect_macro(self_symbol=Symbol(myname))
        # Sort by the recorded order
        sorted_macro = Macro(sorted(macro, key=lambda x: x.number))
        
        script = str(sorted_macro)
        # type annotation for the hard-to-record types
        annot = []
        idt_list = []
        for expr in self._recorded_macro:
            if expr.head == Head.init:
                idt_list.append(expr.args[0].args[0])
            for sym in expr.iter_args():
                if sym.valid or sym in idt_list:
                    continue
                idt_list.append(sym)
                annot.append(f"# {sym}: {sym.type}")
        
        if annot:
            out = "\n".join(annot) + "\n" + script
        else:
            out = script
                    
        if show:
            win = ConsoleTextEdit(name="macro")
            win.read_only = False
            win.value = out
            vbar = win.native.verticalScrollBar()
            vbar.setValue(vbar.maximum())
            
            win.native.setParent(self.native, win.native.windowFlags())
            win.show()
            
        return out
    
    @classmethod
    def wraps(cls, 
              method: Callable | None = None,
              *, 
              template: Callable | None = None) -> Callable:
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
                _, _parent_method = _search_wrapper(self, funcname, clsname)
                return _parent_method(*args, **kwargs)
            
            if isinstance(method, FunctionGui):
                fgui = method
                parent_method = fgui._function
            else:
                fgui = None
                parent_method = method
                
            # Must be template as long as this wrapper function is called
            if template is None:
                _wrap_func = functools_wraps(parent_method)
            else:
                def _wrap_func(f):
                    f = _wraps(template, reference=parent_method)(f)
                    f.__wrapped__ = parent_method
                    f.__name__ = parent_method.__name__
                    f.__qualname__ = parent_method.__qualname__
                    return f
                    
            # If method is defined as a member of class X, __qualname__ will be X.<method name>.
            # We can know the namespace of the wrapped function with __qualname__.
            if isinstance(method, FunctionGui):
                clsname, funcname = fgui._function.__qualname__.split(".")
                options = dict(
                    call_button=fgui._call_button.text if fgui._call_button else None,
                    layout=fgui.layout,
                    labels=fgui.labels,
                    auto_call=fgui._auto_call,
                    result_widget=bool(fgui._result_widget)
                    )
                
                childmethod = magicgui(**options)(_wrap_func(_childmethod))
                parent_method = _copy_function(parent_method)
            
            else:
                clsname, funcname = parent_method.__qualname__.split(".")
                childmethod = _wrap_func(_childmethod)
            
            # To avoid two buttons with same bound function being showed up
            upgrade_signature(parent_method, caller_options={"visible": False})
            
            if hasattr(cls, funcname):
                # Sometimes we want to pre-define function to arrange the order of widgets.
                predifined = getattr(cls, funcname)
                predifined.__wrapped__ = childmethod
                predifined.__magicclass_wrapped__ = childmethod
                if hasattr(childmethod, "__signature__"):
                    predifined.__signature__ = childmethod.__signature__
                parent_method.__doc__ = parent_method.__doc__ or predifined.__doc__
            else:
                setattr(cls, funcname, childmethod)
            
            childmethod.__doc__ = parent_method.__doc__
            
            return parent_method
        
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
    
    def _create_widget_from_method(self, obj: Callable):
        text = obj.__name__.replace("_", " ")
        widget = self._component_class(name=obj.__name__, text=text, gui_only=True)

        # Wrap function to deal with errors in a right way.
        if self._error_mode == ErrorMode.msgbox:
            wrapper = raise_error_in_msgbox
        elif self._error_mode == ErrorMode.stderr:
            wrapper = id_wrapper
        else:
            raise ValueError(self._error_mode)
            
        func = wrapper(obj, parent=self)
        
        # Signature must be updated like this. Otherwise, already wrapped member function
        # will have signature with "self".
        func.__signature__ = inspect.signature(obj)
        
        # Prepare a button or action
        widget.tooltip = extract_tooltip(func)
        
        # Get the number of parameters except for empty widgets.
        # With these lines, "bind" method of magicgui works inside magicclass.
        fgui = FunctionGuiPlus.from_callable(obj)
        n_empty = len([widget for widget in fgui if isinstance(widget, EmptyWidget)])
        nparams = n_parameters(func) - n_empty
        
        record = True
        
        if hasattr(obj, "__signature__"):
            # This block enables instance methods in "bind" method of ValueWidget.
            for param in obj.__signature__.parameters.values():
                if isinstance(param, MagicParameter):
                    bound_value = param.options.get("bind", None)
                    # TODO: n_parameters(bound_value) == 2 is not elegant
                    if callable(bound_value) and n_parameters(bound_value) == 2:
                        clsname, _ = bound_value.__qualname__.split(".")
                        if clsname != self.__class__.__name__:
                            self.__class__.wraps(bound_value)
                        param.options["bind"] = getattr(self, bound_value.__name__)
                        
            func.__signature__ = func.__signature__.replace(
                parameters=list(obj.__signature__.parameters.values())[1:]
                )

            # Check additional options
            if isinstance(obj.__signature__, MagicMethodSignature):
                record = obj.__signature__.additional_options.get("record", True)
                 
        if nparams == 0:
            # We don't want a dialog with a single widget "Run" to show up.
            def run_function():
                # NOTE: callback must be defined inside function. Magic class must be
                # "compiled" otherwise function wrappings are not ready!
                mgui = _build_mgui(widget, func)
                mgui.parent = self
                if mgui.call_count == 0 and len(mgui.called._slots) == 0 and record:
                    callback = _temporal_function_gui_callback(self, mgui, widget)
                    mgui.called.connect(callback)

                out = mgui()
                
                return out
            
        elif nparams == 1 and isinstance(fgui[0], FileEdit):
            # We don't want to open a magicgui dialog and again open a file dialog.
            def run_function():
                mgui = _build_mgui(widget, func)
                mgui.parent = self
                if mgui.call_count == 0 and len(mgui.called._slots) == 0 and record:
                    callback = _temporal_function_gui_callback(self, mgui, widget)
                    mgui.called.connect(callback)
                
                fdialog: FileEdit = mgui[0]
                result = fdialog._show_file_dialog(
                    fdialog.mode,
                    caption=fdialog._btn_text,
                    start_path=str(fdialog.value),
                    filter=fdialog.filter,
                )
                if result:
                    fdialog.value = result
                    out = mgui(result)
                else:
                    out = None
                return out
            
        else:                
            def run_function():
                mgui = _build_mgui(widget, func)
                if mgui.call_count == 0 and len(mgui.called._slots) == 0:
                    mgui.native.setParent(self.native, mgui.native.windowFlags())
                    if self._popup_mode not in (PopUpMode.popup, PopUpMode.dock):
                        mgui.label = ""
                        mgui.name = f"mgui-{id(mgui._function)}" # to avoid name collision
                        mgui.margins = (0, 0, 0, 0)
                        title = Separator(orientation="horizontal", text=text, button=True)
                        title.btn_text = "-"
                        title.btn_clicked.connect(mgui.hide)
                        mgui.insert(0, title)
                        mgui.append(Separator(orientation="horizontal"))
                        
                        if self._popup_mode == PopUpMode.parentlast:
                            parent_self = self._search_parent_magicclass()
                            parent_self.append(mgui)
                        elif self._popup_mode == PopUpMode.first:
                            self.insert(0, mgui)
                        elif self._popup_mode == PopUpMode.last:
                            self.append(mgui)
                        elif self._popup_mode == PopUpMode.above:
                            name = _get_widget_name(widget)
                            i = _get_index(self, name)
                            self.insert(i, mgui)
                        elif self._popup_mode == PopUpMode.below:
                            name = _get_widget_name(widget)
                            i = _get_index(self, name)
                            self.insert(i+1, mgui)
                            
                    elif self._popup_mode == PopUpMode.dock:
                        parent_self = self._search_parent_magicclass()
                        viewer = parent_self.parent_viewer
                        if viewer is None:
                            if not hasattr(parent_self.native, "addDockWidget"):
                                msg = "Cannot add dock widget to a normal container. Please use\n" \
                                      ">>> @magicclass(widget_type='mainwindow')\n" \
                                      "to create main window widget, or add the container as a dock "\
                                      "widget in napari."
                                warnings.warn(msg, UserWarning)
                            
                            else:    
                                from qtpy.QtWidgets import QDockWidget
                                from qtpy.QtCore import Qt
                                dock = QDockWidget(_get_widget_name(widget), self.native)
                                dock.setWidget(mgui.native)
                                parent_self.native.addDockWidget(
                                    Qt.DockWidgetArea.RightDockWidgetArea, dock
                                    )
                        else:
                            dock = viewer.window.add_dock_widget(
                                mgui, name=_get_widget_name(widget), area="right"
                                )
                    
                    if self._close_on_run:
                        if self._popup_mode != PopUpMode.dock:
                            mgui.called.connect(mgui.hide)
                        else:
                            # If FunctioGui is docked, we should close QDockWidget.
                            mgui.called.connect(lambda: mgui.parent.hide())
                    
                    if record:
                        callback = _temporal_function_gui_callback(self, mgui, widget)
                        mgui.called.connect(callback)
                
                if self._popup_mode != PopUpMode.dock:
                    widget.mgui.show()
                else:
                    mgui.parent.show()
                                
                return None
            
        widget.changed.connect(run_function)
        
        # If design is given, load the options.
        widget.from_options(obj)
            
        return widget
    
    def _search_parent_magicclass(self) -> BaseGui:
        current_self = self
        while getattr(current_self, "__magicclass_parent__", None) is not None:
            current_self = current_self.__magicclass_parent__
        return current_self

def _get_widget_name(widget):
    # To escape reference
    return widget.name
    
def _temporal_function_gui_callback(bgui: BaseGui, fgui: FunctionGuiPlus, widget):
    if isinstance(fgui, FunctionGui):
        _function = fgui._function
    else:
        raise TypeError("fgui must be FunctionGui object.")
    
    cls_method = getattr(bgui.__class__, _function.__name__)
    if hasattr(cls_method, "__magicclass_wrapped__"):
        clsname, funcname = _function.__qualname__.split(".")
        root, _function = _search_wrapper(bgui, funcname, clsname)
    else:
        root = bgui
        
    def _after_run():
        bound = fgui._previous_bound
        return_type = fgui.return_annotation
        result_required = return_type is not inspect._empty
        result = Symbol("result")
        
        # Standard button will be connected with two callbacks.
        # 1. Build FunctionGui
        # 2. Emit value changed signal.
        # But if there are more, they also have to be called.
        if len(widget.changed._slots) > 2:
            b = Expr(head=Head.getitem, args=[symbol(root), widget.name])
            ev = Expr(head=Head.getattr, args=[b, Symbol("changed")])
            line = Expr(head=Head.call, args=[ev])
            if result_required:
                line = Expr(head=Head.assign, args=[result, line])
            root._recorded_macro.append(line)
        else:
            line = Expr.parse_method(root, _function, bound.args, bound.kwargs)
            if result_required:
                line = Expr(Head.assign, [result, line])
            root._recorded_macro.append(line)
        
        # Deal with return annotation
        
        if result_required:
            from magicgui.type_map import _type2callback

            for callback in _type2callback(return_type):
                b = Expr(head=Head.getitem, args=[symbol(bgui), widget.name])
                _gui = Expr(head=Head.getattr, args=[b, Symbol("mgui")])
                line = Expr.parse_call(callback, (_gui, result, return_type), {})
                bgui._recorded_macro.append(line)
        
    return _after_run

def _copy_function(f):
    @functools_wraps(f)
    def out(self, *args, **kwargs):
        return f(self, *args, **kwargs)
    return out

def _get_index(container, widget_or_name):
    if isinstance(widget_or_name, str):
        name = widget_or_name
    else:
        name = widget_or_name.name
    for i, widget in enumerate(container):
        if widget.name == name:
            break
    else:
        raise ValueError
    return i

def _search_wrapper(bgui: BaseGui, funcname: str, clsname: str) -> tuple[BaseGui, Callable]:
    current_self = bgui.__magicclass_parent__
    while not (hasattr(current_self, funcname) and 
                current_self.__class__.__name__ == clsname):
        current_self = current_self.__magicclass_parent__
    return current_self, getattr(current_self, funcname)


def _build_mgui(widget_, func):
    if widget_.mgui is not None:
        return widget_.mgui
    try:
        mgui = FunctionGuiPlus(func)
    except Exception as e:
        msg = f"Exception was raised during building magicgui from method {func.__name__}.\n" \
            f"{e.__class__.__name__}: {e}"
        raise type(e)(msg)
    
    widget_.mgui = mgui
    return mgui
        
_C = TypeVar("_C", Callable, type)

def wraps(template: Callable | inspect.Signature) -> Callable[[_C], _C]:
    """
    Update signature using a template. If class is wrapped, then all the methods
    except for those start with "__" will be wrapped.

    Parameters
    ----------
    template : Callable or inspect.Signature object
        Template function or its signature.

    Returns
    -------
    Callable
        A wrapper which take a function or class as an input and returns same
        function or class with updated signature(s).
    """    
    return _wraps(template)

def _wraps(template: Callable | inspect.Signature, 
           reference: Callable = None) -> Callable:
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
            raise TypeError("template must be a callable object or signature, "
                           f"but got {type(template)}.")
        
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
    