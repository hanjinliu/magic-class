from __future__ import annotations
from functools import wraps as functools_wraps
from typing import (
    Any,
    Callable,
    TYPE_CHECKING,
    Iterable,
    Iterator,
    TypeVar,
    overload,
    MutableSequence,
)
from types import MethodType
from abc import ABCMeta
from typing_extensions import _AnnotatedAlias, Literal
import inspect
import warnings
import os
from enum import Enum
import warnings
from docstring_parser import parse, compose
from qtpy.QtWidgets import QWidget, QDockWidget
from qtpy.QtGui import QIcon

from psygnal import Signal
from magicgui.signature import MagicParameter, split_annotated_type
from magicgui.widgets import (
    FunctionGui,
    FileEdit,
    EmptyWidget,
    Widget,
    Container,
    Image,
    Table,
    Label,
    MainWindow,
)
from magicgui.application import use_app
from magicgui.widgets._bases.widget import Widget
from magicgui.widgets._bases import ButtonWidget, ValueWidget
from macrokit import Expr, Head, Symbol, symbol


from .keybinding import as_shortcut
from .mgui_ext import (
    AbstractAction,
    Action,
    FunctionGuiPlus,
    PushButtonPlus,
    _LabeledWidgetAction,
    mguiLike,
)
from .utils import get_parameters, callable_to_classes
from ._macro import GuiMacro

from ..utils import (
    get_signature,
    iter_members,
    Tooltips,
    move_to_screen_center,
    argcount,
    is_instance_method,
    method_as_getter,
    thread_worker,
)
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


def _msgbox_raising(e, parent):
    from ._message_box import QtErrorMessageBox

    return QtErrorMessageBox.raise_(e, parent=parent.native)


def _stderr_raising(e, parent):
    pass


def _stdout_raising(e, parent):
    print(f"{e.__class__.__name__}: {e}")


def _napari_notification_raising(e, parent):
    from napari.utils.notifications import show_error

    show_error(str(e))


class ErrorMode(Enum):
    msgbox = "msgbox"
    stderr = "stderr"
    stdout = "stdout"
    napari = "napari"

    def get_handler(self):
        """Get error handler."""
        return ErrorModeHandlers[self]

    def wrap_handler(self, func: Callable, parent):
        """Wrap function with the error handler."""
        handler = self.get_handler()

        def wrapped_func(*args, **kwargs):
            try:
                out = func(*args, **kwargs)
            except Exception as e:
                handler(e, parent=parent)
                out = e
            return out

        wrapped_func.__annotations__ = func.__annotations__
        # wrapped_func.__name__ = func.__name__  # this is not allowed!
        wrapped_func.__qualname__ = func.__qualname__
        wrapped_func.__doc__ = func.__doc__
        wrapped_func.__module__ = func.__module__

        return wrapped_func


ErrorModeHandlers = {
    ErrorMode.msgbox: _msgbox_raising,
    ErrorMode.stderr: _stderr_raising,
    ErrorMode.stdout: _stdout_raising,
    ErrorMode.napari: _napari_notification_raising,
}


defaults = {
    "popup_mode": PopUpMode.popup,
    "error_mode": ErrorMode.msgbox,
    "close_on_run": True,
    "macro-max-history": 1000,
}

_RESERVED = {
    "__magicclass_parent__",
    "__magicclass_children__",
    "_close_on_run",
    "_error_mode",
    "_popup_mode",
    "_my_symbol",
    "_macro_instance",
    "macro",
    "annotation",
    "enabled",
    "find_ancestor",
    "gui_only",
    "height",
    "label_changed",
    "label",
    "layout",
    "labels",
    "margins",
    "max_height",
    "max_width",
    "min_height",
    "min_width",
    "name",
    "options",
    "param_kind",
    "parent_changed",
    "tooltip",
    "visible",
    "widget_type",
    "width",
    "wraps",
    "_unwrap_method",
    "_search_parent_magicclass",
    "_iter_child_magicclasses",
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


_T = TypeVar("_T", bound="MagicTemplate")
_F = TypeVar("_F", bound=Callable)


class _MagicTemplateMeta(ABCMeta):
    """This metaclass enables type checking of nested magicclasses."""

    @overload
    def __get__(self: type[_T], obj: Any, objtype=None) -> _T:
        ...

    @overload
    def __get__(self: type[_T], obj: Literal[None], objtype=None) -> type[_T]:
        ...

    def __get__(self, obj, objtype=None):
        return self


class MagicTemplate(metaclass=_MagicTemplateMeta):
    __doc__ = ""
    __magicclass_parent__: None | MagicTemplate
    __magicclass_children__: list[MagicTemplate]
    _close_on_run: bool
    _component_class: type[Action | Widget]
    _error_mode: ErrorMode
    _list: list[Action | Widget]
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

    def show(self, run: bool) -> None:
        raise NotImplementedError()

    def hide(self) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()

    @overload
    def __getitem__(self, key: int | str) -> Widget:
        ...

    @overload
    def __getitem__(self, key: slice) -> MutableSequence[Widget]:
        ...

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

    def render(self) -> np.ndarray:
        raise NotImplementedError()

    def _unify_label_widths(self):
        raise NotImplementedError()

    def reset_choices(self, *args):
        raise NotImplementedError()

    @property
    def macro(self) -> GuiMacro:
        """The macro object bound to the ancestor widget."""
        if self.__magicclass_parent__ is None:
            return self._macro_instance
        else:
            return self.__magicclass_parent__.macro

    @property
    def parent_viewer(self) -> napari.Viewer | None:
        """Return napari.Viewer if magic class is a dock widget of a viewer."""
        parent_self = self._search_parent_magicclass()
        if parent_self.native.parent() is None:
            return None
        try:
            from napari.utils._magicgui import find_viewer_ancestor
        except ImportError:
            return None
        viewer = find_viewer_ancestor(parent_self.native)
        return viewer

    @property
    def parent_dock_widget(self) -> QDockWidget | None:
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

    def find_ancestor(self, ancestor: type[_T]) -> _T:
        """
        Find magic class ancestor whose type matches the input.
        This method is useful when a child widget class is defined outside a magic
        class while it needs access to its parent.

        Parameters
        ----------
        ancestor : type of MagicTemplate
            Type of ancestor to search for.

        Returns
        -------
        MagicTemplate
            Magic class object if found.
        """
        if not isinstance(ancestor, type):
            raise TypeError(
                "The first argument of 'find_ancestor' must be a type but got "
                f"{type(ancestor)}"
            )

        current_self = self
        while type(current_self) is not ancestor:
            current_self = current_self.__magicclass_parent__
            if current_self is None:
                raise RuntimeError(
                    f"Magic class {ancestor.__name__} not found. {ancestor.__name__} it "
                    f"is not an ancestor of {self.__class__.__name__}"
                )
        return current_self

    def objectName(self) -> str:
        """
        Return object name of the QWidget.

        This function makes the object name discoverable by napari's
        `viewer.window.add_dock_widget` function. At the same time, since this function
        will always be called when the widget is added as a dock widget of napari, we
        can import macro recorders for napari types in the appropriate timing.
        """
        try:
            from . import _napari_type  # load default macro recorder.
        except Exception:
            pass
        return self.native.objectName()

    @classmethod
    def wraps(
        cls,
        method: _F | None = None,
        *,
        template: Callable | None = None,
        copy: bool = False,
    ) -> _F:
        """
        Wrap a parent method in a child magic-class.

        Wrapped method will appear in the child widget but behaves as if it is in
        the parent widget. Basically, this function is used as a wrapper like below.

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
        copy: bool, default is False
            If true, wrapped method is still enabled.

        Returns
        -------
        Callable
            Same method as input, but has updated signature.
        """
        if (not copy) and get_additional_option(method, "into", None) is not None:
            # If method is already wrapped, wraps should create a copy.
            copy = True

        def wrapper(method: _F):
            # Base function to get access to the original function
            if isinstance(method, FunctionGui):
                func = method._function
            else:
                func = method

            if template is not None:
                wraps(template)(func)

            predefined = getattr(cls, func.__name__, None)
            if predefined is not None:
                # Update signature to the parent one. This step is necessary when widget design
                # is defined on the parent side. Parameters should be replaced with a simplest
                # one to avoid creating useless widgets.
                parent_sig = get_signature(func)
                _simple_param = inspect.Parameter(
                    "self", inspect.Parameter.POSITIONAL_OR_KEYWORD
                )
                if not hasattr(predefined, "__signature__"):
                    predefined.__signature__ = parent_sig.replace(
                        parameters=(_simple_param,),
                    )
                else:
                    sig: inspect.Signature = predefined.__signature__
                    predefined.__signature__ = sig.replace(
                        parameters=parent_sig.parameters.values(),
                        return_annotation=parent_sig.return_annotation,
                    )
                upgrade_signature(predefined, additional_options={"copyto": []})

            if copy:
                copyto_list = get_additional_option(func, "copyto", [])
                copyto_list.append(cls.__name__)
                upgrade_signature(func, additional_options={"copyto": copyto_list})
            else:
                upgrade_signature(func, additional_options={"into": cls.__name__})
            return method

        return wrapper if method is None else wrapper(method)

    def _unwrap_method(
        self,
        method_name: str,
        widget: FunctionGui | PushButtonPlus | Action,
        moveto: str,
        copyto: list[str],
    ):
        """
        This private method converts class methods that are wrapped by its child widget class
        into widget in child widget. Practically same widget is shared between parent and child,
        but only visible in the child side.

        Parameters
        ----------
        moveto : str
            Name of child widget class name.
        method_name : str
            Name of method.
        widget : FunctionGui
            Widget to be added.

        Raises
        ------
        RuntimeError
            If ``child_clsname`` was not found in child widget list. This error will NEVER be raised
            in the user's side.
        """
        if moveto is not None:
            matcher = copyto + [moveto]
        else:
            matcher = copyto

        _found = 0
        _n_match = len(matcher)

        for child_instance in self._iter_child_magicclasses():
            _name = child_instance.__class__.__name__
            if _name in matcher:
                # get the position of predefined child widget
                try:
                    index = _get_index(child_instance, method_name)
                    new = False
                except ValueError:
                    index = -1
                    new = True

                self._fast_insert(-1, widget)
                copy = _name in copyto

                if isinstance(widget, FunctionGui):
                    if copy:
                        widget = widget.copy()
                    if new:
                        child_instance._fast_insert(-1, widget)
                    else:
                        del child_instance[index]
                        child_instance._fast_insert(index, widget)

                else:
                    widget.visible = copy
                    if new:
                        child_widget = child_instance._create_widget_from_method(
                            lambda x: None
                        )
                        child_widget.text = widget.text
                        child_instance._fast_insert(-1, child_widget)
                    else:
                        child_widget: PushButtonPlus | AbstractAction = child_instance[
                            index
                        ]

                    child_widget.changed.disconnect()
                    child_widget.changed.connect(widget.changed)
                    child_widget.tooltip = widget.tooltip
                    child_widget._doc = widget._doc

                widget._unwrapped = True

                _found += 1
                if _found == _n_match:
                    break

        else:
            raise RuntimeError(
                f"{method_name} not found in class {self.__class__.__name__}"
            )

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

    def _create_widget_from_method(self, obj: MethodType):
        """Convert instance methods into GUI objects, such as push buttons or actions."""
        text = obj.__name__.replace("_", " ")
        widget = self._component_class(name=obj.__name__, text=text, gui_only=True)

        # Wrap function to deal with errors in a right way.
        func = self._error_mode.wrap_handler(obj, parent=self)

        # Signature must be updated like this. Otherwise, already wrapped member function
        # will have signature with "self".
        obj_sig = inspect.signature(obj)
        func.__signature__ = obj_sig

        # Prepare a button or action
        widget.tooltip = Tooltips(func).desc
        widget._doc = func.__doc__

        # This block enables instance methods in "bind" or "choices" of ValueWidget.
        all_params: list[inspect.Parameter] = []
        for param in func.__signature__.parameters.values():
            if isinstance(param.annotation, _AnnotatedAlias):
                # TODO: after magicgui supports pydantic, something needs update here.
                param = MagicParameter.from_parameter(param)

            if isinstance(param, MagicParameter):
                _param = MagicParameter(
                    name=param.name,
                    default=param.default,
                    annotation=split_annotated_type(param.annotation)[0],
                    gui_options=param.options.copy(),
                )
                _arg_bind = _param.options.get("bind", None)
                _arg_choices = _param.options.get("choices", None)

                # If bound method is a class method, use self.method(widget).
                if is_instance_method(_arg_bind):
                    _param.options["bind"] = method_as_getter(self, _arg_bind)

                # If a MagicFiled is bound, bind the value of the connected widget.
                elif isinstance(_arg_bind, MagicField):
                    _param.options["bind"] = _arg_bind.as_remote_getter(self)

                # If choices are provided by a class method, use self.method(widget).
                if is_instance_method(_arg_choices):
                    _param.options["choices"] = method_as_getter(self, _arg_choices)

            else:
                _param = param

            all_params.append(_param)

        func.__signature__ = func.__signature__.replace(parameters=all_params)
        # Get the number of parameters except for empty widgets.
        # With these lines, "bind" method of magicgui works inside magicclass.
        fgui_classes = callable_to_classes(func)
        n_empty = len(
            [_wdg_cls for _wdg_cls in fgui_classes if _wdg_cls is EmptyWidget]
        )
        nparams = argcount(func) - n_empty

        if isinstance(func.__signature__, MagicMethodSignature):
            func.__signature__.additional_options = getattr(
                obj_sig, "additional_options", {}
            )

        has_preview = get_additional_option(func, "preview", None) is not None

        if nparams == 0 and not has_preview:
            # We don't want a dialog with a single widget "Run" to show up.
            def run_function():
                # NOTE: callback must be defined inside function. Magic class must be
                # "compiled" otherwise function wrappings are not ready!
                mgui = _build_mgui(widget, func, self)
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                out = mgui()

                return out

        elif nparams == 1 and issubclass(fgui_classes[0], FileEdit) and not has_preview:
            # We don't want to open a magicgui dialog and again open a file dialog.
            def run_function():
                mgui = _build_mgui(widget, func, self)
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                fdialog: FileEdit = mgui[0]
                if result := fdialog._show_file_dialog(
                    fdialog.mode,
                    caption=fdialog._btn_text,
                    start_path=str(fdialog.value),
                    filter=fdialog.filter,
                ):
                    fdialog.value = result
                    out = mgui(result)
                else:
                    out = None
                return out

        else:
            _prep_func = _define_popup(self, obj, widget)

            def run_function():
                mgui = _build_mgui(widget, func, self)
                if mgui.call_count == 0 and len(mgui.called._slots) == 0:
                    _prep_func(mgui)
                    if self._popup_mode not in (PopUpMode.popup, PopUpMode.dock):
                        mgui.label = ""
                        # to avoid name collision
                        mgui.name = f"mgui-{id(mgui._function)}"
                        mgui.margins = (0, 0, 0, 0)
                        title = Separator(
                            orientation="horizontal", title=text, button=True
                        )
                        title.btn_text = "-"
                        # TODO: should remove mgui from self?
                        title.btn_clicked.connect(mgui.hide)
                        mgui.insert(0, title)

                    if self._close_on_run and not mgui._auto_call:
                        if self._popup_mode != PopUpMode.dock:
                            mgui.called.connect(mgui.hide)
                        else:
                            # If FunctioGui is docked, we should close QDockWidget.
                            mgui.called.connect(lambda: mgui.parent.hide())

                if nparams == 1 and issubclass(fgui_classes[0], FileEdit):
                    fdialog: FileEdit = mgui[0]
                    if result := fdialog._show_file_dialog(
                        fdialog.mode,
                        caption=fdialog._btn_text,
                        start_path=str(fdialog.value),
                        filter=fdialog.filter,
                    ):
                        fdialog.value = result
                    else:
                        return None

                if self._popup_mode != PopUpMode.dock:
                    widget.mgui.show()
                else:
                    mgui.parent.show()  # show dock widget

                return None

        widget.changed.connect(run_function)

        # If design is given, load the options.
        widget.from_options(obj)

        # keybinding
        keybinding = get_additional_option(func, "keybinding", None)
        if keybinding is not None:
            shortcut = as_shortcut(keybinding)
            widget.set_shortcut(shortcut)

        return widget

    def _search_parent_magicclass(self) -> MagicTemplate:
        """Find the ancestor."""
        current_self = self
        while (
            parent := getattr(current_self, "__magicclass_parent__", None)
        ) is not None:
            current_self = parent
        return current_self

    def _iter_child_magicclasses(self) -> Iterable[MagicTemplate]:
        """Iterate over all the child magic classes"""
        for child in self.__magicclass_children__:
            yield child
            yield from child._iter_child_magicclasses()


class BaseGui(MagicTemplate):
    def __init__(self, close_on_run, popup_mode, error_mode):
        self._macro_instance = GuiMacro(
            max_lines=defaults["macro-max-history"],
            flags={"Get": False, "Return": False},
        )
        self.__magicclass_parent__: BaseGui | None = None
        self.__magicclass_children__: list[MagicTemplate] = []
        self._close_on_run = close_on_run
        self._popup_mode = popup_mode
        self._error_mode = error_mode
        self._my_symbol = Symbol.var("ui")
        self._icon_path = None


class ContainerLikeGui(BaseGui, mguiLike, MutableSequence):
    # This class enables similar API between magicgui widgets and additional widgets
    # in magicclass such as menu and toolbar.
    _component_class = Action
    changed = Signal(object)
    _list: list[AbstractAction | ContainerLikeGui]

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
                f"Path {path} does not exists. Could not set icon.", UserWarning
            )

    def reset_choices(self, *_: Any):
        """Reset child Categorical widgets"""
        all_widgets: set[Widget] = set()

        for item in self._list:
            widget = getattr(item, "_inner_widget", item)
            all_widgets.add(widget)
        for widget in self.__magicclass_children__:
            all_widgets.add(widget)

        for w in all_widgets:
            if hasattr(w, "reset_choices"):
                w.reset_choices()

    def _create_widget_from_field(self, name: str, fld: MagicField):
        if fld.not_ready():
            raise TypeError(
                f"MagicField {name} does not contain enough information for widget creation"
            )

        fld.name = fld.name or name
        action = fld.get_action(self)

        if action.support_value and fld.record:
            # By default, set value function will be connected to the widget.
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
        _hide_labels = (
            _LabeledWidgetAction,
            ButtonWidget,
            FreeWidget,
            Label,
            FunctionGui,
            BaseGui,
            Image,
            Table,
            Action,
        )
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


def _build_mgui(widget_: Action | PushButtonPlus, func: Callable, parent: BaseGui):
    if widget_.mgui is not None:
        return widget_.mgui
    try:
        sig = getattr(func, "__signature__", None)
        if isinstance(sig, MagicMethodSignature):
            opt = sig.additional_options
        else:
            opt = {}
        call_button = opt.get("call_button", None)
        layout = opt.get("layout", "vertical")
        labels = opt.get("labels", True)
        auto_call = opt.get("auto_call", False)
        mgui = FunctionGuiPlus(
            func, call_button, layout=layout, labels=labels, auto_call=auto_call
        )
        preview = opt.get("preview", None)
        if preview is not None:
            btn_text, previewer = preview
            mgui.append_preview(previewer.__get__(parent), btn_text)

    except Exception as e:
        msg = (
            "Exception was raised during building magicgui from method "
            f"{func.__name__}.\n{e.__class__.__name__}: {e}"
        )
        raise type(e)(msg)

    widget_.mgui = mgui
    name = widget_.name or ""
    mgui.native.setWindowTitle(name.replace("_", " ").strip())
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
            raise TypeError(
                "template must be a callable object or signature, "
                f"but got {type(template)}."
            )

        # update empty signatures
        template_params = template_signature.parameters
        new_params: list[Param] = []

        for k, v in old_params.items():
            if v.annotation is Param.empty and v.default is Param.empty:
                new_params.append(
                    template_params.get(k, Param(k, Param.POSITIONAL_OR_KEYWORD))
                )
            else:
                new_params.append(v)

        # update empty return annotation
        if old_signature.return_annotation is inspect._empty:
            return_annotation = template_signature.return_annotation
        else:
            return_annotation = old_signature.return_annotation

        f.__signature__ = inspect.Signature(
            parameters=new_params, return_annotation=return_annotation
        )

        fdoc = parse(f.__doc__)
        tempdoc = parse(template.__doc__)
        fdoc.short_description = fdoc.short_description or tempdoc.short_description
        fdoc.long_description = fdoc.long_description or tempdoc.long_description
        fdoc.meta = fdoc.meta or tempdoc.meta
        f.__doc__ = compose(fdoc)

        return f

    return wrapper


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


def _child_that_has_widget(
    self: BaseGui, method: Callable, widget_or_name: Widget | str
) -> BaseGui:
    child_clsname = get_additional_option(method, "into")
    if child_clsname is None:
        return self
    for child_instance in self._iter_child_magicclasses():
        if child_instance.__class__.__name__ == child_clsname:
            break
    else:
        raise ValueError(f"{widget_or_name} not found.")
    return child_instance


def value_widget_callback(
    gui: MagicTemplate,
    widget: ValueWidget,
    name: str | list[str],
    getvalue: bool = True,
):
    """Define a ValueWidget callback, including macro recording."""
    if isinstance(name, str):
        sym_name = Symbol(name)
    else:
        sym_name = Symbol(name[0])
        for n in name[1:]:
            sym_name = Expr(head=Head.getattr, args=[sym_name, n])

    if getvalue:
        sub = Expr(head=Head.getattr, args=[sym_name, Symbol("value")])  # name.value
    else:
        sub = sym_name

    def _set_value():
        if not widget.enabled or not gui.macro.active:
            # If widget is read only, it means that value is set in script (not manually).
            # Thus this event should not be recorded as a macro.
            return None

        gui.changed.emit(gui)

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
    """Define a FunctionGui callback, including macro recording."""
    fgui_name = Symbol(fgui.name)

    def _after_run():
        if not fgui.enabled or not gui.macro.active:
            # If widget is read only, it means that value is set in script (not manually).
            # Thus this event should not be recorded as a macro.
            return None
        inputs = get_parameters(fgui)
        args = [Expr(head=Head.kw, args=[Symbol(k), v]) for k, v in inputs.items()]
        # args[0] is self
        sub = Expr(head=Head.getattr, args=[symbol(gui), fgui_name])  # {x}.func
        expr = Expr(head=Head.call, args=[sub] + args[1:])  # {x}.func(args...)

        if fgui._auto_call:
            # Auto-call will cause many redundant macros. To avoid this, only the last input
            # will be recorded in magic-class.
            last_expr = gui.macro[-1]
            if (
                last_expr.head == Head.call
                and last_expr.args[0].head == Head.getattr
                and last_expr.at(0, 1) == expr.at(0, 1)
                and len(gui.macro) > 0
            ):
                gui.macro.pop()
                gui.macro._erase_last()

        gui.macro.append(expr)
        gui.macro._last_setval = None

    return _after_run


_SELF = inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)


def _inject_recorder(func: Callable, is_method: bool = True) -> Callable:
    """Inject macro recording functionality into a function."""
    sig = get_signature(func)
    if is_method:
        sig = sig.replace(
            parameters=list(sig.parameters.values())[1:],
            return_annotation=sig.return_annotation,
        )
        _func = func
    else:

        @functools_wraps(func)
        def _func(self, *args, **kwargs):
            return func(*args, **kwargs)

        _func.__signature__ = sig.replace(
            parameters=[_SELF] + list(sig.parameters.values()),
            return_annotation=sig.return_annotation,
        )

    _record_macro = _define_macro_recorder(sig, _func)

    if not isinstance(_func, thread_worker):

        @functools_wraps(_func)
        def _recordable(bgui: MagicTemplate, *args, **kwargs):
            with bgui.macro.blocked():
                out = _func.__get__(bgui)(*args, **kwargs)
            if bgui.macro.active:
                _record_macro(bgui, *args, **kwargs)
            return out

        if hasattr(_func, "__signature__"):
            _recordable.__signature__ = _func.__signature__
        return _recordable

    else:
        _func._set_recorder(_record_macro)
        return _func


def _define_macro_recorder(sig, func):
    if isinstance(sig, MagicMethodSignature):
        opt = sig.additional_options
        _auto_call = opt.get("auto_call", False)
    else:
        _auto_call = False

    # TODO: if function has a return_annotation, macro should be recorded like ui["f"](...)
    def _record_macro(bgui: MagicTemplate, *args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        kwargs = dict(bound.arguments.items())
        expr = Expr.parse_method(bgui, func, (), kwargs)
        if _auto_call:
            # Auto-call will cause many redundant macros. To avoid this, only the last
            # input will be recorded in magic-class.
            last_expr = bgui.macro[-1]
            if (
                last_expr.head == Head.call
                and last_expr.args[0].head == Head.getattr
                and last_expr.at(0, 1) == expr.at(0, 1)
                and len(bgui.macro) > 0
            ):
                bgui.macro.pop()
                bgui.macro._erase_last()

        bgui.macro.append(expr)
        bgui.macro._last_setval = None
        return None

    return _record_macro


def convert_attributes(cls: type[_T], hide: tuple[type, ...]) -> dict[str, Any]:
    """
    Convert class attributes into macro recordable ones.

    Returned dictionary can be directly used for the third argument of
    ``type`` constructor. To avoid converting all the callables in
    subclasses, subclasses that will be iterated over can be restricted
    using ``hide`` argument.

    Parameters
    ----------
    cls : BaseGui type
        Class that will be converted.
    hide : tuple of types
        MROs that will be ignored during iteration.

    Returns
    -------
    dict
        New namespace.
    """
    _dict: dict[str, Callable] = {}
    _pass_type = (property, classmethod, staticmethod, type, Widget)
    mro = [c for c in cls.__mro__ if c not in hide]
    for subcls in reversed(mro):
        for name, obj in subcls.__dict__.items():
            if name.startswith("_") or isinstance(obj, _pass_type) or not callable(obj):
                # private method, non-action-like object, not-callable object are passed.
                new_attr = obj
            elif callable(obj) and get_additional_option(obj, "record", True):
                new_attr = _inject_recorder(obj)
            else:
                new_attr = obj

            _dict[name] = new_attr
    return _dict


def _define_popup(self: BaseGui, obj, widget: PushButtonPlus | Action):
    # deal with popup mode.
    if self._popup_mode == PopUpMode.popup:
        # To be popped up correctly, window flags of FunctionGui should be
        # "windowFlags" and should appear at the center.
        def _prep(mgui: FunctionGui):
            mgui.native.setParent(self.native, mgui.native.windowFlags())
            move_to_screen_center(mgui.native)

    elif self._popup_mode == PopUpMode.parentlast:

        def _prep(mgui: FunctionGui):
            parent_self = self._search_parent_magicclass()
            parent_self.append(mgui)

    elif self._popup_mode == PopUpMode.first:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            child_self.insert(0, mgui)

    elif self._popup_mode == PopUpMode.last:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            child_self.append(mgui)

    elif self._popup_mode == PopUpMode.above:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            i = _get_index(child_self, widget)
            child_self.insert(i, mgui)

    elif self._popup_mode == PopUpMode.below:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            i = _get_index(child_self, widget)
            child_self.insert(i + 1, mgui)

    elif self._popup_mode == PopUpMode.dock:
        from .class_gui import MainWindowClassGui

        def _prep(mgui: FunctionGui):

            parent_self = self._search_parent_magicclass()
            viewer = parent_self.parent_viewer
            if viewer is None:
                if isinstance(parent_self, MainWindowClassGui):
                    parent_self.add_dock_widget(mgui)
                else:
                    msg = (
                        "Cannot add dock widget to a normal container. Please use\n"
                        ">>> @magicclass(widget_type='mainwindow')\n"
                        "to create main window widget, or add the container as a dock "
                        "widget in napari."
                    )
                    warnings.warn(msg, UserWarning)

            else:
                viewer.window.add_dock_widget(
                    mgui, name=_get_widget_name(widget), area="right"
                )

    else:
        raise RuntimeError
    return _prep
