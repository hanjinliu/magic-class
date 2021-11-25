from __future__ import annotations
from functools import wraps as functools_wraps
from typing import Any, Callable, TYPE_CHECKING, Iterable, TypeVar, overload
from typing_extensions import _AnnotatedAlias
import inspect
from enum import Enum
import warnings
from collections.abc import MutableSequence

from magicgui.events import Signal
from magicgui.signature import MagicParameter
from magicgui.widgets import FunctionGui, FileEdit, EmptyWidget, Widget
from magicgui.widgets._bases import ValueWidget

from .macro import Macro, Expr, Head, Symbol, symbol
from .utils import (get_signature, iter_members, n_parameters, extract_tooltip, raise_error_in_msgbox, 
                    identity_wrapper, screen_center, get_index)
from .widgets import Separator, MacroEdit
from .mgui_ext import FunctionGuiPlus, PushButtonPlus
from .fields import MagicField
from .signature import MagicMethodSignature
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

class MagicTemplate:    
    _recorded_macro: Macro[Expr] = Macro()
    __magicclass_parent__: None | MagicTemplate
    __magicclass_children__: list[MagicTemplate]
    _close_on_run: bool
    _popup_mode: PopUpMode
    _error_mode: ErrorMode
    name: str
    width: int
    max_width: int
    min_width: int
    height: int
    max_height: int
    min_height: int
    parent_changed: Signal
    label_changed: Signal
    changed: Signal
    tooltip: str
    enabled: bool
    annotation: Any
    gui_only: bool
    param_kind: inspect._ParameterKind
    visible: bool
    options: dict
    parent: Widget
    widget_type: str
    label: str
    margin: tuple[int, int, int, int]
    layout: str
    labels: bool
    
    def show(self) -> None:
        raise NotImplementedError()
    
    def hide(self) -> None:
        raise NotImplementedError()
    
    def close(self) -> None:
        raise NotImplementedError()
    
    @overload
    def __getitem__(self, key: int | str) -> Widget: ...

    @overload
    def __getitem__(self, key: slice) -> MutableSequence[Widget]: ...

    def __getitem__(self, key):
        raise NotImplementedError()
    
    def index(self, value: Any, start: int, stop: int) -> int:
        raise NotImplementedError()
    
    def remove(self, value: Widget | str):
        raise NotImplementedError()
    
    def append(self, widget: Widget) -> None:
        raise NotImplementedError()
        
    def insert(self, key: int, widget: Widget) -> None:
        raise NotImplementedError()
    
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
        
        for name, clsattr in iter_members(self.__class__):
            # Collect all the macro from child magic-classes recursively
            if not isinstance(clsattr, (MagicTemplate, type, MagicField)):
                continue
            
            attr = getattr(self, name)
            
            if not isinstance(attr, MagicTemplate):
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
            win = MacroEdit(name="macro")
            win.value = out
            
            win.native.setParent(self.native, win.native.windowFlags())
            win.native.move(screen_center() - win.native.rect().center())
            win.show()
            
        return out
    
    @classmethod
    def wraps(cls, 
              method: Callable | None = None,
              *, 
              template: Callable | None = None) -> Callable:
        """
        Wrap a parent method in a child magic-class. Wrapped method will appear in the
        child widget but behaves as if it is in the parent widget.
        
        Basically, this function is used as a wrapper like below.
        
        .. code-block:: python
        @magicclass
        class C:
            @magicclass
            class D: 
                def func(self, ...): ... # pre-definition
            @D.wraps
            def func(self, ...): ...

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
            if isinstance(method, FunctionGui):
                func = method._function
            else:
                func = method
            if template is not None:
                func = _wraps(template)(func)
            if hasattr(cls, method.__name__):
                getattr(cls, method.__name__).__signature__ = get_signature(func)
            
            upgrade_signature(func, additional_options={"into": cls.__name__})
            return func
        
        return wrapper if method is None else wrapper(method)
    
    def _unwrap_method(self, child_clsname: str, name: str, widget: FunctionGui | PushButtonPlus):
        """
        This private method converts class methods that are wrapped by its child widget class
        into widget in child widget. Practically same widget is shared between parent and child,
        but only visible in the child side.

        Parameters
        ----------
        child_clsname : str
            Name of child widget class name.
        name : str
            Name of method.
        widget : FunctionGui
            Widget to be added.

        Raises
        ------
        RuntimeError
            If ``child_clsname`` was not found in child widget list. This error will NEVER be raised
            in the user's side.
        """        
        for child_instance in self._iter_child_magicclasses():
            if child_instance.__class__.__name__ == child_clsname:
                # get the position of predefined child widget
                try:
                    index = get_index(child_instance, name)
                    new = False
                except ValueError:
                    index = len(child_instance)
                    new = True
                
                self.append(widget)
                
                if isinstance(widget, FunctionGui):
                    if new:
                        child_instance.append(widget)
                    else:
                        del child_instance[index]
                        child_instance.insert(index, widget)
                else:
                    widget.visible = False
                    if new:
                        widget = child_instance._create_widget_from_method(lambda x: None)
                        child_instance.append(widget)
                    else:
                        child_widget: PushButtonPlus = child_instance[index]
                        child_widget.changed.disconnect()
                        child_widget.changed.connect(widget.changed)
                break
        else:
            raise RuntimeError(f"{child_clsname} not found in class {self.__class__.__name__}")
    
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
            wrapper = identity_wrapper
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
        
        # This block enables instance methods in "bind" method of ValueWidget.
        all_params = []
        for param in func.__signature__.parameters.values():
            if isinstance(param.annotation, _AnnotatedAlias):
                param = MagicParameter.from_parameter(param)
            if isinstance(param, MagicParameter):
                bound_value = param.options.get("bind", None)
                
                # If bound method is a class method, use self.method(widget) as the value.
                # "n_parameters(bound_value) == 2" seems a indirect way to determine that
                # "bound_value" is a class method but "_method_as_getter" raises ValueError
                # if "bound_value" is defined in a wrong namespace.
                if isinstance(bound_value, Callable) and n_parameters(bound_value) == 2:
                    param.options["bind"] = _method_as_getter(self, bound_value)
                
                # If a MagicFiled is bound, bind the value of the connected widget.
                elif isinstance(bound_value, MagicField):
                    param.options["bind"] = _field_as_getter(self, bound_value)
                
                # If a value widget is bound, bind the value.
                elif isinstance(bound_value, ValueWidget):
                    param.options["bind"] = _one_more_arg(bound_value.get_value)
            
            all_params.append(param)
        
        func.__signature__ = func.__signature__.replace(
            parameters=all_params
            )
        
        obj_sig = get_signature(obj)
        if isinstance(func.__signature__, MagicMethodSignature):
            # NOTE: I don't know the reason why "additional_options" is lost. 
            func.__signature__.additional_options = getattr(obj_sig, "additional_options", {})
            
        if nparams == 0:
            # We don't want a dialog with a single widget "Run" to show up.
            def run_function():
                # NOTE: callback must be defined inside function. Magic class must be
                # "compiled" otherwise function wrappings are not ready!
                mgui = _build_mgui(widget, func)
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                if mgui.call_count == 0 and len(mgui.called._slots) == 0 and _need_record(func):
                    callback = _temporal_function_gui_callback(self, mgui, widget)
                    mgui.called.connect(callback)
                
                out = mgui()
                
                return out
            
        elif nparams == 1 and isinstance(fgui[0], FileEdit):
            # We don't want to open a magicgui dialog and again open a file dialog.
            def run_function():
                mgui = _build_mgui(widget, func)
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                if mgui.call_count == 0 and len(mgui.called._slots) == 0 and _need_record(func):
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
                    mgui.native.move(screen_center() - mgui.native.rect().center())
                    
                    # deal with popup mode.
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
                            i = get_index(self, name)
                            self.insert(i, mgui)
                        elif self._popup_mode == PopUpMode.below:
                            name = _get_widget_name(widget)
                            i = get_index(self, name)
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
                    
                    if _need_record(func):
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
    
    def _search_parent_magicclass(self) -> MagicTemplate:
        current_self = self
        while getattr(current_self, "__magicclass_parent__", None) is not None:
            current_self = current_self.__magicclass_parent__
        return current_self
    
    def _iter_child_magicclasses(self) -> Iterable[MagicTemplate]:
        for child in self.__magicclass_children__:
            yield child
            yield from child.__magicclass_children__
    
class BaseGui(MagicTemplate):
    def __init__(self, close_on_run, popup_mode, error_mode):
        self._recorded_macro: Macro[Expr] = Macro()
        self.__magicclass_parent__: None | BaseGui = None
        self.__magicclass_children__: list[MagicTemplate] = []
        self._close_on_run = close_on_run
        self._popup_mode = popup_mode
        self._error_mode = error_mode

def _get_widget_name(widget):
    # To escape reference
    return widget.name
    
def _temporal_function_gui_callback(bgui: MagicTemplate, fgui: FunctionGuiPlus, widget: PushButtonPlus):
    if isinstance(fgui, FunctionGui):
        _function = fgui._function
    else:
        raise TypeError("fgui must be FunctionGui object.")
        
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
            b = Expr(head=Head.getitem, args=[symbol(bgui), widget.name])
            ev = Expr(head=Head.getattr, args=[b, Symbol("changed")])
            line = Expr(head=Head.call, args=[ev])
            if result_required:
                line = Expr(head=Head.assign, args=[result, line])
            bgui._recorded_macro.append(line)
        else:
            line = Expr.parse_method(bgui, _function, bound.args, bound.kwargs)
            if result_required:
                line = Expr(Head.assign, [result, line])
            bgui._recorded_macro.append(line)
        
        # Deal with return annotation
        
        if result_required:
            from magicgui.type_map import _type2callback

            for callback in _type2callback(return_type):
                b = Expr(head=Head.getitem, args=[symbol(bgui), widget.name])
                _gui = Expr(head=Head.getattr, args=[b, Symbol("mgui")])
                line = Expr.parse_call(callback, (_gui, result, return_type), {})
                bgui._recorded_macro.append(line)
        
        return None
    
    return _after_run

def _one_more_arg(f):
    def out(e):
        return f()
    return out

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
    mgui.native.setWindowTitle(widget_.name)
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

def _method_as_getter(self, bound_value: Callable):
    *clsnames, funcname = bound_value.__qualname__.split(".")
    
    def _func(w):
        ins = self
        while clsnames[0] != ins.__class__.__name__:
            ins = getattr(ins, "__magicclass_parent__", None)
            if ins is None:
                raise ValueError(f"Method {bound_value.__qualname__} is invisible"
                                 f"from magicclass {self.__class__.__qualname__}")
        
        for clsname in clsnames[1:]:
            ins = getattr(ins, clsname)
        return getattr(ins, funcname)(w)
    return _func

def _field_as_getter(self, bound_value: MagicField):
    def _func(w):
        namespace = bound_value.parent_class.__qualname__
        clsnames = namespace.split(".")
        ins = self
        while type(ins).__name__ not in clsnames:
            ins = getattr(ins, "__magicclass_parent__", None)
            if ins is None:
                raise ValueError(f"MagicField {namespace}.{bound_value.name} is invisible"
                                 f"from magicclass {self.__class__.__qualname__}")
        i = clsnames.index(type(ins).__name__)
        for clsname in clsnames[i:]:
            ins = getattr(ins, clsname, ins)
            
        _field_widget = bound_value.get_widget(ins)
        if not hasattr(_field_widget, "value"):
            raise TypeError(f"MagicField {bound_value.name} does not return ValueWidget "
                            "thus cannot be used as a bound value.")
        return bound_value.as_getter(ins)(w)
    return _func

def _need_record(func: Callable):
    if isinstance(func.__signature__, MagicMethodSignature):
        record = func.__signature__.additional_options.get("record", True)
    else:
        record = True
    return record