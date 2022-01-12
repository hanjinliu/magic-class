from __future__ import annotations
from functools import wraps as functools_wraps
from typing import Any, Callable, TYPE_CHECKING, Iterable, Iterator, TypeVar, overload, MutableSequence
from typing_extensions import _AnnotatedAlias
import inspect
import warnings
import os
from enum import Enum
import warnings
from docstring_parser import parse, compose
from qtpy.QtWidgets import QWidget, QDockWidget
from qtpy.QtGui import QIcon

from magicgui.events import Signal
from magicgui.signature import MagicParameter
from magicgui.widgets import FunctionGui, FileEdit, EmptyWidget, Widget, Container, Image, Table, Label
from magicgui.application import use_app
from magicgui.widgets._bases.widget import Widget
from magicgui.widgets._bases import ButtonWidget, ValueWidget
from macrokit import Expr, Head, Symbol, symbol

from .keybinding import as_shortcut
from .mgui_ext import AbstractAction, Action, FunctionGuiPlus, PushButtonPlus, _LabeledWidgetAction, mguiLike
from .utils import get_parameters, define_callback
from ._macro import GuiMacro

from ..utils import get_signature, iter_members, extract_tooltip, screen_center
from ..widgets import Separator, FreeWidget
from ..fields import MagicField
from ..signature import MagicMethodSignature, get_additional_option
from ..wrappers import upgrade_signature

if TYPE_CHECKING:
    import numpy as np
    import napari

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

_RESERVED = {"__magicclass_parent__", "__magicclass_children__", "_close_on_run", 
             "_error_mode", "_popup_mode", "_my_symbol", "_macro_instance", "macro",
             "annotation", "enabled", "gui_only", "height", "label_changed", "label",
             "layout", "labels", "margins", "max_height", "max_width", "min_height", 
             "min_width", "name", "options", "param_kind", "parent_changed", 
             "tooltip", "visible", "widget_type", "width", "wraps", "_unwrap_method",
             "_search_parent_magicclass", "_iter_child_magicclasses", 
             }

def check_override(cls: type):
    """
    Some of the methods should not be overriden because they are essential for magic 
    class construction.

    Parameters
    ----------
    cls : type
        Base class to test override.

    Raises
    ------
    AttributeError
        If forbidden override found.
    """    
    subclass_members = set(cls.__dict__.keys())
    collision = subclass_members & _RESERVED
    if collision:
        raise AttributeError(
            f"Cannot override magic class reserved attributes: {collision}"
            )
          

class MagicTemplate: 
    __doc__ = ""
    __magicclass_parent__: None | MagicTemplate
    __magicclass_children__: list[MagicTemplate]
    _close_on_run: bool
    _component_class: type[Action | Widget]
    _error_mode: ErrorMode
    _macro_instance: GuiMacro
    _my_symbol: Symbol
    _popup_mode: PopUpMode
    annotation: Any
    changed: Signal
    enabled: bool
    gui_only: bool
    height: int
    icon_path: str
    label_changed: Signal
    label: str
    layout: str
    labels: bool
    margins: tuple[int, int, int, int]
    max_height: int
    max_width: int
    min_height: int
    min_width: int
    name: str
    native: QWidget
    options: dict
    param_kind: inspect._ParameterKind
    parent: Widget
    parent_changed: Signal
    tooltip: str
    visible: bool
    widget_type: str
    width: int
    
    __init_subclass__ = check_override
    
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
        return self.insert(len(self, widget))
    
    def _fast_insert(self, key: int, widget: Widget) -> None:
        raise NotImplementedError()
    
    def insert(self, key: int, widget: Widget) -> None:
        self._fast_insert(key, widget)
        self._unify_label_widths()
    
    def render(self) -> "np.ndarray":
        raise NotImplementedError()
    
    def _unify_label_widths(self):
        raise NotImplementedError()
    
    @property
    def macro(self) -> GuiMacro:
        if self.__magicclass_parent__ is None:
            return self._macro_instance
        else:
            return self.__magicclass_parent__.macro
    
    @property
    def parent_viewer(self) -> "napari.Viewer" | None:
        """
        Return napari.Viewer if magic class is a dock widget of a viewer.
        """
        try:
            from napari.utils._magicgui import find_viewer_ancestor
        except ImportError:
            return None
        parent_self = self._search_parent_magicclass()
        return find_viewer_ancestor(parent_self.native)
    
    @property
    def parent_dock_widget(self) -> "QDockWidget" | None:
        """
        Return dock widget object if magic class is a dock widget of a main 
        window widget, such as a napari Viewer.
        """
        parent_self = self._search_parent_magicclass()
        try:
            dock = parent_self.native.parent()
            if not isinstance(dock, QDockWidget):
                dock = None
        except AttributeError:
            dock = None
            
        return dock

    
    def objectName(self) -> str:
        """
        This function makes the object name discoverable by napari's 
        `viewer.window.add_dock_widget` function.
        """        
        return self.native.objectName()

    @classmethod
    def wraps(cls, 
              method: Callable | None = None,
              *, 
              template: Callable | None = None) -> Callable:
        """
        Wrap a parent method in a child magic-class. Wrapped method will appear in 
        the child widget but behaves as if it is in the parent widget.
        
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
                wraps(template)(func)
            if hasattr(cls, func.__name__):
                getattr(cls, func.__name__).__signature__ = get_signature(func)
            
            upgrade_signature(func, additional_options={"into": cls.__name__})
            return method
        
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
                    index = _get_index(child_instance, name)
                    new = False
                except ValueError:
                    index = -1
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
                        child_widget = child_instance._create_widget_from_method(lambda x: None)
                        child_widget.text = widget.text
                        child_instance.append(child_widget)
                    else:
                        child_widget: PushButtonPlus | AbstractAction = child_instance[index]
                    
                    child_widget.changed.disconnect()
                    child_widget.changed.connect(widget.changed)
                    child_widget.tooltip = widget.tooltip
                    child_widget._doc = widget._doc
                    
                widget._unwrapped = True
                
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
        """Convert instance methods into GUI objects, such as push buttons or actions."""
        if isinstance(obj, MagicMethod):
            obj.widget.__magicclass_parent__ = self
            self.__magicclass_children__.append(obj.widget)
            obj.widget._my_symbol = Symbol(obj.__name__)
            
        text = obj.__name__.replace("_", " ")
        widget = self._component_class(name=obj.__name__, text=text, gui_only=True)

        # Wrap function to deal with errors in a right way.
        if self._error_mode == ErrorMode.msgbox:
            wrapper = _raise_error_in_msgbox
        elif self._error_mode == ErrorMode.stderr:
            wrapper = _identity_wrapper
        else:
            raise ValueError(self._error_mode)
        
        # Wrap function to block macro recording.
        _inner_func = wrapper(obj, parent=self)
        if _need_record(obj):
            @functools_wraps(obj)
            def func(*args, **kwargs):
                with self.macro.blocked():
                    out = _inner_func(*args, **kwargs)
                return out
        else:
            @functools_wraps(obj)
            def func(*args, **kwargs):
                return _inner_func(*args, **kwargs)
        
        # Signature must be updated like this. Otherwise, already wrapped member function
        # will have signature with "self".
        func.__signature__ = inspect.signature(obj)
        
        # Prepare a button or action
        widget.tooltip = extract_tooltip(func)
        widget._doc = func.__doc__
        
        # Get the number of parameters except for empty widgets.
        # With these lines, "bind" method of magicgui works inside magicclass.
        fgui = FunctionGuiPlus.from_callable(obj)
        n_empty = len([_widget for _widget in fgui if isinstance(_widget, EmptyWidget)])
        nparams = _n_parameters(func) - n_empty
        
        # This block enables instance methods in "bind" method of ValueWidget.
        all_params = []
        for param in func.__signature__.parameters.values():
            if isinstance(param.annotation, _AnnotatedAlias):
                # TODO: pydantic
                param = MagicParameter.from_parameter(param)
            if isinstance(param, MagicParameter):
                bound_value = param.options.get("bind", None)
                
                # If bound method is a class method, use self.method(widget) as the value.
                # "_n_parameters(bound_value) == 2" seems a indirect way to determine that
                # "bound_value" is a class method but "_method_as_getter" raises ValueError
                # if "bound_value" is defined in a wrong namespace.
                if isinstance(bound_value, Callable) and _n_parameters(bound_value) == 2:
                    param.options["bind"] = _method_as_getter(self, bound_value)
                
                # If a MagicFiled is bound, bind the value of the connected widget.
                elif isinstance(bound_value, MagicField):
                    param.options["bind"] = _field_as_getter(self, bound_value)
                
            
            all_params.append(param)
        
        func.__signature__ = func.__signature__.replace(
            parameters=all_params
            )
        
        obj_sig = get_signature(obj)
        if isinstance(func.__signature__, MagicMethodSignature):
            # NOTE: I don't know the reason why "additional_options" is lost. 
            func.__signature__.additional_options = getattr(
                obj_sig, "additional_options", {}
                )
        
        # TODO: "update_widget" argument is useful.
        # see https://github.com/napari/magicgui/pull/309
        if nparams == 0:
            # We don't want a dialog with a single widget "Run" to show up.
            def run_function():
                # NOTE: callback must be defined inside function. Magic class must be
                # "compiled" otherwise function wrappings are not ready!
                mgui = _build_mgui(widget, func)
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                if (mgui.call_count == 0 and 
                    len(mgui.called._slots) == 0 and 
                    _need_record(func)):
                    callback = _temporal_function_gui_callback(self, mgui, widget)
                    mgui.called.connect(callback)
                
                out = mgui()
                
                return out
            
        elif nparams == 1 and isinstance(fgui[0], FileEdit):
            # We don't want to open a magicgui dialog and again open a file dialog.
            def run_function():
                mgui = _build_mgui(widget, func)
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                if (mgui.call_count == 0 and 
                    len(mgui.called._slots) == 0 and 
                    _need_record(func)):
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
                    
                    # deal with popup mode.
                    if self._popup_mode not in (PopUpMode.popup, PopUpMode.dock):
                        mgui.label = ""
                        mgui.name = f"mgui-{id(mgui._function)}" # to avoid name collision
                        mgui.margins = (0, 0, 0, 0)
                        title = Separator(orientation="horizontal", text=text, button=True)
                        title.btn_text = "-"
                        title.btn_clicked.connect(mgui.hide) # TODO: should remove mgui from self?
                        mgui.insert(0, title)
                        mgui.append(Separator(orientation="horizontal"))
                        
                        if self._popup_mode == PopUpMode.parentlast:
                            parent_self = self._search_parent_magicclass()
                            parent_self.append(mgui)
                        elif self._popup_mode == PopUpMode.first:
                            child_self = _child_that_has_widget(self, obj, widget)
                            child_self.insert(0, mgui)
                        elif self._popup_mode == PopUpMode.last:
                            child_self = _child_that_has_widget(self, obj, widget)
                            child_self.append(mgui)
                        elif self._popup_mode == PopUpMode.above:
                            child_self = _child_that_has_widget(self, obj, widget)
                            i = _get_index(child_self, widget)
                            child_self.insert(i, mgui)
                        elif self._popup_mode == PopUpMode.below:
                            child_self = _child_that_has_widget(self, obj, widget)
                            i = _get_index(child_self, widget)
                            child_self.insert(i+1, mgui)
                            
                    elif self._popup_mode == PopUpMode.dock:
                        parent_self = self._search_parent_magicclass()
                        viewer = parent_self.parent_viewer
                        if viewer is None:
                            if not hasattr(parent_self.native, "addDockWidget"):
                                msg = (
                                    "Cannot add dock widget to a normal container. Please use\n"
                                    ">>> @magicclass(widget_type='mainwindow')\n"
                                    "to create main window widget, or add the container as a dock "
                                    "widget in napari.")
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
                    else:
                        # To be popped up correctly, window flags of FunctionGui should be
                        # "windowFlags" and should appear at the center.
                        mgui.native.setParent(self.native, mgui.native.windowFlags())
                        mgui.native.move(screen_center() - mgui.native.rect().center())
                        
                    if self._close_on_run and not mgui._auto_call:
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
                    # show dock widget
                    mgui.parent.show()
                                
                return None
            
        widget.changed.connect(run_function)
        
        # If design is given, load the options.
        widget.from_options(obj)
        
        # keybinding
        keybinding = get_additional_option(func, "keybinding", None)
        if keybinding is not None:
            if obj.__name__.startswith("_"):
                from qtpy.QtWidgets import QShortcut
                shortcut = QShortcut(as_shortcut(keybinding), self.native)
                shortcut.activated.connect(widget.changed)
            else:
                shortcut = as_shortcut(keybinding)
                widget.set_shortcut(shortcut)
            
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
        self._macro_instance = GuiMacro(flags={"Get": False, "Return": False})
        self.__magicclass_parent__: BaseGui | None = None
        self.__magicclass_children__: list[MagicTemplate] = []
        self._close_on_run = close_on_run
        self._popup_mode = popup_mode
        self._error_mode = error_mode
        self._my_symbol = Symbol.var("ui")
        self._icon_path = None


class ContainerLikeGui(BaseGui, mguiLike, MutableSequence):
    _component_class = Action
    changed = Signal(object)
    _list: list[AbstractAction | ContainerLikeGui]
    
    def reset_choices(self, *_: Any):
        """Reset child Categorical widgets"""
        for widget in self:
            if hasattr(widget, "reset_choices"):
                widget.reset_choices()
        for widget in self.__magicclass_children__:
            if hasattr(widget, "reset_choices"):
                widget.reset_choices()
    
    @property
    def icon_path(self):
        return self._icon_path
    
    @icon_path.setter
    def icon_path(self, path: str):
        path = str(path)
        if os.path.exists(path):
            icon = QIcon(path)
            if hasattr(self.native, "setIcon"):
                self.native.setIcon(icon)
            else:
                self.native.setWindowIcon(icon)
            self._icon_path = path
        else:
            warnings.warn(
                f"Path {path} does not exists. Could not set icon.",
                UserWarning
            )
        
    def _create_widget_from_field(self, name: str, fld: MagicField):
        cls = self.__class__
        if fld.not_ready():
            try:
                fld.decode_string_annotation(cls.__annotations__[name])    
            except (AttributeError, KeyError):
                pass
            
        fld.name = fld.name or name.replace("_", " ")
        action = fld.get_action(self)
            
        if action.support_value:
            # If the field has callbacks, connect it to the newly generated widget.
            for callback in fld.callbacks:
                # funcname = callback.__name__
                action.changed.connect(define_callback(self, callback))
                     
            # By default, set value function will be connected to the widget.
            if fld.record:
                getvalue = type(fld) is MagicField
                f = value_widget_callback(self, action, name, getvalue=getvalue)
                action.changed.connect(f)
                
        return action
    
    
    def __getitem__(self, key: int | str) -> ContainerLikeGui | AbstractAction:
        if isinstance(key, int):
            return self._list[key]
        
        out = None
        for obj in self._list:
            if obj.name == key:
                out = obj
                break
        if out is None:
            raise KeyError(key)
        return out
    
    def __setitem__(self, key, value):
        raise NotImplementedError()
    
    def __delitem__(self, key: int | str) -> None:
        self.native.removeAction(self[key].native)
    
    def __iter__(self) -> Iterator[ContainerLikeGui | AbstractAction]:
        return iter(self._list)
    
    def __len__(self) -> int:
        return len(self._list)
    
    def append(self, obj: Callable | ContainerLikeGui | AbstractAction) -> None:
        return self.insert(len(self._list), obj)
    
    def _unify_label_widths(self):
        _hide_labels = (_LabeledWidgetAction, ButtonWidget, FreeWidget, Label, 
                        FunctionGui, BaseGui, Image, Table, Action)
        need_labels = [w for w in self if not isinstance(w, _hide_labels)]
        
        if self.labels and need_labels:
            measure = use_app().get_obj("get_text_width")
            widest_label = max(measure(w.label) for w in need_labels)
            for w in need_labels:
                labeled_widget = w._labeled_widget()
                if labeled_widget:
                    labeled_widget.label_width = widest_label

    def render(self):
        try:
            import numpy as np
        except ImportError:
            raise ModuleNotFoundError(
                "could not find module 'numpy'. "
                "Please `pip install numpy` to render widgets."
            ) from None
        import qtpy
        img = self.native.grab().toImage()
        bits = img.constBits()
        h, w, c = img.height(), img.width(), 4
        if qtpy.API_NAME == "PySide2":
            arr = np.array(bits).reshape(h, w, c)
        else:
            bits.setsize(h * w * c)
            arr = np.frombuffer(bits, np.uint8).reshape(h, w, c)

        return arr[:, :, [2, 1, 0, 3]]

    def _repr_png_(self):
        """Return PNG representation of the widget for QtConsole."""
        from io import BytesIO

        try:
            from imageio import imsave
        except ImportError:
            print(
                "(For a nicer magicmenu widget representation in "
                "Jupyter, please `pip install imageio`)"
            )
            return None

        with BytesIO() as file_obj:
            imsave(file_obj, self.render(), format="png")
            file_obj.seek(0)
            return file_obj.read()

def _get_widget_name(widget: Widget):
    # To escape reference
    return widget.name
    
def _temporal_function_gui_callback(bgui: MagicTemplate, 
                                    fgui: FunctionGuiPlus, 
                                    widget: PushButtonPlus):
    if isinstance(fgui, FunctionGui):
        _function = fgui._function
    else:
        raise TypeError("fgui must be FunctionGui object.")
        
    return_type = fgui.return_annotation
    result_required = return_type is not inspect._empty
    
    def _after_run():
        bound = fgui._previous_bound
        result = Symbol("result")
        # Standard button will be connected with two callbacks.
        # 1. Build FunctionGui
        # 2. Emit value changed signal.
        # But if there are more, they also have to be called.
        if len(widget.changed._slots) > 2:
            b = Expr(head=Head.getitem, args=[symbol(bgui), widget.name])
            ev = Expr(head=Head.getattr, args=[b, Symbol("changed")])
            expr = Expr(head=Head.call, args=[ev])
        else:
            kwargs = {k: v for k, v in bound.arguments.items()}
            expr = Expr.parse_method(bgui, _function, (), kwargs)
        
        if fgui._auto_call:
            # Auto-call will cause many redundant macros. To avoid this, only the last input
            # will be recorded in magic-class.
            last_expr = bgui.macro[-1]
            if (last_expr.head == Head.call and
                last_expr.args[0].head == Head.getattr and
                last_expr.at(0, 1) == expr.at(0, 1) and
                len(bgui.macro) > 0):
                bgui.macro.pop()
                bgui.macro._erase_last()
        
        if result_required:
            expr = Expr(Head.assign, [result, expr])
        bgui.macro.append(expr)
        
        # Deal with return annotation
        
        if result_required:
            from magicgui.type_map import _type2callback

            for callback in _type2callback(return_type):
                b = Expr(head=Head.getitem, args=[symbol(bgui), widget.name])
                _gui = Expr(head=Head.getattr, args=[b, Symbol("mgui")])
                line = Expr.parse_call(callback, (_gui, result, return_type), {})
                bgui.macro.append(line)
        bgui.macro._last_setval = None
        return None
    
    return _after_run

def _build_mgui(widget_, func):
    if widget_.mgui is not None:
        return widget_.mgui
    try:
        call_button = get_additional_option(func, "call_button", None)
        layout = get_additional_option(func, "layout", "vertical")
        auto_call = get_additional_option(func, "auto_call", False)
        mgui = FunctionGuiPlus(func, call_button, layout=layout, auto_call=auto_call)
    except Exception as e:
        msg = (
            "Exception was raised during building magicgui from method "
            f"{func.__name__}.\n{e.__class__.__name__}: {e}"
            )
        raise type(e)(msg)
    
    widget_.mgui = mgui
    name = widget_.name or ""
    mgui.native.setWindowTitle(name.replace("_", " "))
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
    def wrapper(f: _C) -> _C:
        if isinstance(f, type):
            for name, attr in iter_members(f):
                if callable(attr) or isinstance(attr, type):
                    wrapper(attr)
            return f
        
        Param = inspect.Parameter
        old_signature = inspect.signature(f)
            
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
        
        fdoc = parse(f.__doc__)
        tempdoc = parse(template.__doc__)
        fdoc.short_description = fdoc.short_description or tempdoc.short_description
        fdoc.long_description = fdoc.long_description or tempdoc.long_description
        fdoc.meta = fdoc.meta or tempdoc.meta
        f.__doc__ = compose(fdoc)
        
        return f
    return wrapper

def _raise_error_in_msgbox(_func: Callable, parent: Widget = None):
    """
    If exception happened inside function, then open a message box.
    """    
    def wrapped_func(*args, **kwargs):
        from qtpy.QtWidgets import QMessageBox
        try:
            out = _func(*args, **kwargs)
        except Exception as e:
            QMessageBox.critical(
                parent.native, e.__class__.__name__, str(e), QMessageBox.Ok
                )
            out = e
        return out
    
    return wrapped_func

def _identity_wrapper(_func: Callable, parent: Widget = None):
    """
    Do nothing.
    """    
    def wrapped_func(*args, **kwargs):
        return _func(*args, **kwargs)
    return wrapped_func

def _n_parameters(func: Callable):
    """
    Count the number of parameters of a callable object.
    """    
    return len(inspect.signature(func).parameters)

def _get_index(container: Container, widget_or_name: Widget | str) -> int:
    """
    Identical to container[widget_or_name], which sometimes doesn't work
    in magic-class.
    """    
    if isinstance(widget_or_name, str):
        name = widget_or_name
    else:
        name = widget_or_name.name
    for i, widget in enumerate(container):
        if widget.name == name:
            break
    else:
        raise ValueError(f"{widget_or_name} not found in {container}")
    return i

def _child_that_has_widget(self: BaseGui, method: Callable, 
                           widget_or_name: Widget | str) -> BaseGui:
    child_clsname = get_additional_option(method, "into")
    if child_clsname is None:
        return self
    for child_instance in self._iter_child_magicclasses():
        if child_instance.__class__.__name__ == child_clsname:
            break
    else:
        raise ValueError(f"{widget_or_name} not found.")
    return child_instance
            

def _method_as_getter(self, bound_value: Callable):
    qualname = bound_value.__qualname__
    _locals = "<locals>."
    if _locals in qualname:
        qualname = qualname.split(_locals)[-1]
    *clsnames, funcname = qualname.split(".")
    
    def _func(w):
        ins = self
        while clsnames[0] != ins.__class__.__name__:
            ins = getattr(ins, "__magicclass_parent__", None)
            if ins is None:
                raise ValueError(f"Method {qualname} is invisible"
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
                raise ValueError(
                    f"MagicField {namespace}.{bound_value.name} is invisible"
                    f"from magicclass {self.__class__.__qualname__}"
                    )
        i = clsnames.index(type(ins).__name__)
        for clsname in clsnames[i:]:
            ins = getattr(ins, clsname, ins)
            
        _field_widget = bound_value.get_widget(ins)
        if not hasattr(_field_widget, "value"):
            raise TypeError(
                f"MagicField {bound_value.name} does not return ValueWidget "
                "thus cannot be used as a bound value."
                )
        return bound_value.as_getter(ins)(w)
    return _func

def _need_record(func: Callable):
    return get_additional_option(func, "record", True)

def value_widget_callback(gui: MagicTemplate,
                          widget: ValueWidget, 
                          name: str, 
                          getvalue: bool = True):
    """
    Define a ValueWidget callback, including macro recording.
    """    
    sym_name = Symbol(name)
    sym_value = Symbol("value")
    def _set_value():
        if not widget.enabled or not gui.macro.active:
            # If widget is read only, it means that value is set in script (not manually).
            # Thus this event should not be recorded as a macro.
            return None
        
        gui.changed.emit(gui)
        
        if getvalue:
            sub = Expr(head=Head.getattr, args=[sym_name, sym_value]) # name.value
        else:
            sub = sym_name
        
        # Make an expression of
        # >>> x.name.value = value
        # or
        # >>> x.name = value
        target = Expr(Head.getattr, [symbol(gui), sub])
        expr = Expr(Head.assign, [target, widget.value])
        if gui.macro._last_setval == target and len(gui.macro) > 0:
            gui.macro.pop()
            gui.macro._erase_last()
        else:
            gui.macro._last_setval = target
        gui.macro.append(expr)
        return None
    return _set_value

def nested_function_gui_callback(gui: MagicTemplate, fgui: FunctionGui):
    """
    Define a FunctionGui callback, including macro recording.
    """    
    fgui_name = Symbol(fgui.name)
    def _after_run():
        if not fgui.enabled or not gui.macro.active:
            # If widget is read only, it means that value is set in script (not manually).
            # Thus this event should not be recorded as a macro.
            return None
        inputs = get_parameters(fgui)
        args = [Expr(head=Head.kw, args=[Symbol(k), v]) for k, v in inputs.items()]
        # args[0] is self
        sub = Expr(head=Head.getattr, args=[symbol(gui), fgui_name]) # {x}.func
        expr = Expr(head=Head.call, args=[sub] + args[1:]) # {x}.func(args...)

        if fgui._auto_call:
            # Auto-call will cause many redundant macros. To avoid this, only the last input
            # will be recorded in magic-class.
            last_expr = gui.macro[-1]
            if (last_expr.head == Head.call and
                last_expr.args[0].head == Head.getattr and
                last_expr.at(0, 1) == expr.at(0, 1) and
                len(gui.macro) > 0):
                gui.macro.pop()
                gui.macro._erase_last()

        gui.macro.append(expr)
        gui.macro._last_setval = None
    return _after_run


class MagicMethod:
    def __init__(self, parent: MagicTemplate):
        self.__name__ = parent.__class__.__name__
        self.__qualname__ = parent.__class__.__qualname__
        self.widget = parent
        self.__signature__ = MagicMethodSignature(additional_options={"record": False})
    
    def __call__(self):
        self.widget.show()
    