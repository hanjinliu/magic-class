from __future__ import annotations

from contextlib import contextmanager
import functools
from typing import (
    Any,
    ContextManager,
    Literal,
    Callable,
    TYPE_CHECKING,
    Iterable,
    Iterator,
    TypeVar,
    overload,
    MutableSequence,
)
from types import MethodType
from typing_extensions import Self
from abc import ABCMeta
import inspect
import warnings
from weakref import WeakValueDictionary, WeakSet
from qtpy import QtWidgets as QtW, QtGui

from psygnal import Signal
from magicgui.signature import MagicParameter
from magicgui.widgets import (
    FunctionGui,
    FileEdit,
    EmptyWidget,
    Widget,
    Container,
    Image,
    Table,
    Label,
)
from magicgui.application import use_app
from magicgui.widgets.bases import ButtonWidget, ValueWidget
from magicgui import types as _mgui_types
from macrokit import Symbol

from magicclass._gui.keybinding import as_shortcut
from magicclass._gui.mgui_ext import (
    AbstractAction,
    FunctionGuiPlus,
    Action,
    Clickable,
    is_clickable,
    _LabeledWidgetAction,
    mguiLike,
)
from magicclass._gui.utils import (
    copy_class,
    callable_to_classes,
    show_dialog_from_mgui,
    connect_magicclasses,
)
from magicclass._gui._macro import GuiMacro, DummyMacro
from magicclass._gui._macro_utils import (
    inject_recorder,
    inject_silencer,
    inject_validator_only,
    value_widget_callback,
    MagicGuiPostRunCallback,
)
from magicclass._gui._icon import get_icon
from magicclass._gui._gui_modes import PopUpMode, ErrorMode

from magicclass.utils import (
    get_signature,
    Tooltips,
    move_to_screen_center,
    argcount,
    is_instance_method,
    method_as_getter,
    eval_attribute,
)
from magicclass.widgets import Separator, FreeWidget
from magicclass.fields import MagicField, FieldGroup
from magicclass.signature import (
    ConfirmDict,
    MagicMethodSignature,
    is_annotated,
    get_additional_option,
    split_annotated_type,
    upgrade_signature,
)
from magicclass._exceptions import MagicGuiBuildError
from magicclass.wrappers import abstractapi
from magicclass.types import BoundLiteral
from magicclass.functools import wraps
from magicclass.box._fields import BoxMagicField

if TYPE_CHECKING:
    import numpy as np
    import napari

defaults = {
    "popup_mode": PopUpMode.popup,
    "error_mode": ErrorMode.msgbox,
    "close_on_run": True,
    "macro-max-history": 100000,
    "macro-highlight": False,
    "macro-attribute-check": True,
    "macro-signature-check": True,
    "macro-name-check": True,
    "undo-max-history": 100,
    "raise-conversion-error": False,
}

_RESERVED = frozenset(
    {
        "__magicclass_parent__",
        "__magicclass_children__",
        "_close_on_run",
        "_error_mode",
        "_popup_mode",
        "_my_symbol",
        "_macro_instance",
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
        "_initialized",
    }
)


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


_ANCESTORS: WeakValueDictionary[tuple[int, int], MagicTemplate] = WeakValueDictionary()


_T = TypeVar("_T", bound="MagicTemplate")
_F = TypeVar("_F", bound=Callable)


class _MagicTemplateMeta(ABCMeta):
    """This metaclass enables type checking of nested magicclasses."""

    @overload
    def __get__(self: type[_T], obj: Any | None, objtype=None) -> _T: ...

    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> Self: ...

    def __get__(self, obj, objtype=None):
        return self


def _typeof(current_self) -> type:
    """Compatible with the copy_class function."""
    tp = type(current_self)
    return getattr(tp, "__original_class__", tp)


def _find_gui_class(self) -> type[BaseGui] | None:
    """
    Find a superclass of BaseGui.

    At the time of class construction, the magicclass is not a subclass of BaseGui.
    By using this function, MagicTemplate can find the correct class to call the method.
    """
    for superclass in type(self).__mro__[1:]:
        if issubclass(superclass, BaseGui):
            return superclass
        elif superclass is Container:
            return superclass
    return None


class MagicTemplate(
    MutableSequence["Widget | AbstractAction"], metaclass=_MagicTemplateMeta
):
    __doc__ = ""
    __magicclass_parent__: None | MagicTemplate
    __magicclass_children__: WeakSet[MagicTemplate]
    _close_on_run: bool
    _component_class: type[Clickable]
    _error_mode: ErrorMode
    _list: list[AbstractAction | Widget]
    _macro_instance: GuiMacro
    _my_symbol: Symbol
    _popup_mode: PopUpMode
    annotation: Any
    changed: Signal
    enabled: bool
    gui_only: bool
    height: int
    icon: Any
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
    native: QtW.QWidget
    options: dict
    param_kind: inspect._ParameterKind
    parent: Widget | None
    parent_changed: Signal
    tooltip: str
    visible: bool
    widget_type: str
    width: int

    def __init_subclass__(cls, **kwargs):
        check_override(cls)

    @overload
    def __getitem__(self, key: int | str) -> Widget | AbstractAction: ...

    @overload
    def __getitem__(self, key: slice) -> list[Widget | AbstractAction]: ...

    def __getitem__(self, key):
        if cls := _find_gui_class(self):
            return cls.__getitem__(self, key)
        raise NotImplementedError()

    def __setitem__(self, key: int, value: Any):
        raise NotImplementedError()

    def __delitem__(self, key: int) -> None:
        if cls := _find_gui_class(self):
            return cls.__delitem__(self, key)
        raise NotImplementedError()

    def __len__(self) -> int:
        if cls := _find_gui_class(self):
            return cls.__len__(self)
        raise NotImplementedError()

    if TYPE_CHECKING:

        def __iter__(self) -> Iterator[Widget | AbstractAction]:
            raise NotImplementedError()

        def index(self, value: Any, start: int, stop: int) -> int:
            raise NotImplementedError()

        def remove(self, value: Widget | AbstractAction | str):
            raise NotImplementedError()

    def show(self, run: bool = False) -> None:
        if cls := _find_gui_class(self):
            return cls.show(self, run)
        raise NotImplementedError()

    def hide(self) -> None:
        if cls := _find_gui_class(self):
            return cls.hide(self)
        raise NotImplementedError()

    def close(self) -> None:
        if cls := _find_gui_class(self):
            return cls.close(self)
        raise NotImplementedError()

    def _fast_insert(
        self, key: int, widget: Widget | AbstractAction | Callable
    ) -> None:
        raise NotImplementedError()

    def insert(self, key: int, widget: Widget | AbstractAction | Callable) -> None:
        self._fast_insert(key, widget)
        self._unify_label_widths()

    def render(self) -> np.ndarray:
        if cls := _find_gui_class(self):
            return cls.render(self)
        raise NotImplementedError()

    def _unify_label_widths(self):
        raise NotImplementedError()

    def reset_choices(self, *args):
        if cls := _find_gui_class(self):
            return cls.reset_choices(self, *args)
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
        return _find_viewer_ancestor(parent_self.native)

    @property
    def parent_dock_widget(self) -> QtW.QDockWidget | None:
        """
        Return dock widget object if magic class is a dock widget of a main
        window widget, such as a napari Viewer.
        """
        parent_self = self._search_parent_magicclass()
        try:
            dock = parent_self.native.parent()
            if not isinstance(dock, QtW.QDockWidget):
                dock = None
        except AttributeError:
            dock = None

        return dock

    def find_ancestor(self, ancestor: type[_T], cache: bool = False) -> _T:
        """
        Find magic class ancestor whose type matches the input.

        This method is useful when a child widget class is defined outside a magic
        class while it needs access to its parent.

        Parameters
        ----------
        ancestor : type of MagicTemplate
            Type of ancestor to search for.
        cache : bool, default False
            If true, the result will be cached. Caching is not safe if the widget is
            going to be used as a child of other widgets.

        Returns
        -------
        MagicTemplate
            Magic class object if found.
        """
        if cache and (anc := _ANCESTORS.get((id(self), id(ancestor)), None)):
            return anc

        if not isinstance(ancestor, type):
            raise TypeError(
                "The first argument of 'find_ancestor' must be a type but got "
                f"{type(ancestor)}"
            )

        current_self = self
        while _typeof(current_self) is not ancestor:
            current_self = current_self.__magicclass_parent__
            if current_self is None:
                raise RuntimeError(
                    f"Magic class {ancestor.__name__} not found. {ancestor.__name__} "
                    f"is not an ancestor of {self.__class__.__name__}"
                )
        if cache:
            _ANCESTORS[(id(self), id(ancestor))] = current_self
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
            # load default macro recorder.
            from . import _napari_type  # noqa: F401
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
        copy: bool, default False
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
            into_cls = cls
            while (
                isinstance(predefined, abstractapi)
                and (loc := predefined.get_location()) is not None
            ):
                predefined.resolve()
                predefined = getattr(loc, func.__name__, None)
                into_cls = loc

            if predefined is not None:
                # Update signature to the parent one. This step is necessary when widget
                # design is defined on the parent side. Parameters should be replaced
                # with a simplest one to avoid creating useless widgets.
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

                # if abstractapi, mark as resolved
                if isinstance(predefined, abstractapi):
                    predefined.resolve()

            if copy:
                copyto_list = get_additional_option(func, "copyto", [])
                copyto_list.append(into_cls.__name__)
                upgrade_signature(func, additional_options={"copyto": copyto_list})
            else:
                upgrade_signature(func, additional_options={"into": into_cls.__name__})
            return method

        return wrapper if method is None else wrapper(method)

    def _unwrap_method(
        self,
        method_name: str,
        widget: FunctionGui | Clickable,
        moveto: str,
        copyto: list[str],
    ):
        """
        This private method converts class methods that are wrapped by its child widget
        class into widget in child widget. Practically same widget is shared between
        parent and child, but only visible in the child side.

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
            If `child_clsname` was not found in child widget list. This error will
            NEVER be raised in the user's side.
        """
        if moveto is not None:
            matcher = copyto + [moveto]
        else:
            matcher = copyto

        _found = 0
        _n_match = len(matcher)
        for _, child_ins in self._iter_child_magicclasses():
            _name = child_ins.__class__.__name__
            if _name in matcher:
                n_children = len(child_ins)

                # get the position of predefined child widget
                try:
                    index = _get_index(child_ins, method_name)
                    new = False
                except ValueError:
                    index = n_children
                    new = True

                widget._unwrapped = True
                self._fast_insert(len(self), widget, remove_label=True)
                copy = _name in copyto

                if not is_clickable(widget):
                    if copy:
                        widget = widget.copy()
                    if new:
                        child_ins._fast_insert(n_children, widget)
                    else:
                        del child_ins[index]
                        child_ins._fast_insert(index, widget)

                else:
                    # NOTE: wrapping button with action is not supported in the
                    # method above.
                    widget.visible = copy
                    if new:
                        child_widget = child_ins._create_widget_from_method(
                            _empty_func(method_name)
                        )
                        child_widget.text = widget.text
                        child_ins._fast_insert(n_children, child_widget)
                    else:
                        child_widget = child_ins[index]

                    child_widget.changed.disconnect()
                    child_widget.changed.connect(widget.changed)
                    child_widget.tooltip = widget.tooltip
                    child_widget._doc = widget._doc
                    child_widget._get_running = lambda: widget.running

                _found += 1
                if _found == _n_match:
                    break

        else:
            raise RuntimeError(
                f"{method_name} not found in any of the nested classes in class "
                f"{self.__class__.__name__}"
            )

    @contextmanager
    def config_context(
        self,
        error_mode=None,
        close_on_run=None,
        recursive: bool = True,
    ):
        """
        Context manager to temporarily change the configuration of the widget.

        Parameters
        ----------
        error_mode : ErrorMode, optional
            Error mode to use.
        """
        if error_mode is not None:
            old_error_mode = self._error_mode
            self._error_mode = ErrorMode(error_mode)
        else:
            old_error_mode = self._popup_mode
        if close_on_run is not None:
            old_close_on_run = self._close_on_run
        else:
            old_close_on_run = self._close_on_run

        child_contexts: list[ContextManager] = []
        try:
            if recursive:
                for child in self.__magicclass_children__:
                    ctx = child.config_context(
                        error_mode=error_mode,
                        close_on_run=close_on_run,
                        recursive=True,
                    )
                    ctx.__enter__()
                    child_contexts.append(ctx)
            yield
        finally:
            for ctx in child_contexts:
                ctx.__exit__(None, None, None)
            self._error_mode = old_error_mode
            self._close_on_run = old_close_on_run

    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and
        nested classes are converted to magicgui widgets.
        """
        raise NotImplementedError()

    def _convert_an_attribute_into_widget(
        self, name: str, attr: Any, tooltips: Tooltips
    ) -> Widget:
        if isinstance(attr, type):
            # Nested magic-class
            widget = attr()
            object.__setattr__(self, name, widget)
            if isinstance(widget, BaseGui):
                connect_magicclasses(self, widget, name)

        elif isinstance(attr, MagicField):
            # If MagicField is given by field() function.
            widget = self._create_widget_from_field(name, attr)
            if isinstance(widget, BaseGui):
                connect_magicclasses(self, widget, name)
            if isinstance(attr, BoxMagicField):
                for wdt in widget:
                    if isinstance(wdt, BaseGui):
                        connect_magicclasses(self, wdt, name)
            if not widget.tooltip:
                widget.tooltip = tooltips.attributes.get(name, "")

        elif isinstance(attr, FunctionGui):
            widget = attr.copy()
            first_widget = widget[0]
            if not hasattr(first_widget, "bind"):  # TODO: instance check in the future
                raise TypeError(
                    f"The first widget of FunctionGui {attr!r} must be ValueWidget."
                )
            first_widget.bind(self)  # bind self to the first argument

        elif isinstance(attr, Widget) and not isinstance(attr, FieldGroup):
            warnings.warn(
                f"Widget {name!r} is given as a class attribute. This is not "
                "recommended, as it is shared between all the instances. "
                "Please use a field or vfield instead.",
                UserWarning,
                stacklevel=2,
            )
            widget = attr

        elif _is_separator(attr):
            widget = Separator()
        else:
            # convert class method into instance method
            widget = getattr(self, name, None)

        return widget

    def _create_widget_from_field(self, name: str, fld: MagicField) -> Widget:
        """
        Called when magic-class encountered a MagicField in its definition.

        Parameters
        ----------
        name : str
            Name of variable
        fld : MagicField
            A field object that describes what type of widget it should be.
        """
        raise NotImplementedError()

    def _create_widget_from_method(self, obj: MethodType):
        """Convert instance methods into GUI, such as push buttons or actions."""
        if isinstance(obj, abstractapi):
            obj.check_resolved()

        if hasattr(obj, "__name__"):
            obj_name = obj.__name__
        else:
            _inner_func = obj
            while hasattr(_inner_func, "func"):
                _inner_func = _inner_func.func
            obj_name = getattr(_inner_func, "__name__", str(_inner_func))
        text = obj_name.replace("_", " ")
        widget = self._component_class(
            name=obj_name, text=text, gui_only=True, parent=self.native
        )

        func = _create_gui_method(self, obj)

        # Prepare a button or action
        widget.tooltip = Tooltips(func).desc
        widget._doc = func.__doc__

        # Get the number of parameters except for empty widgets.
        # With these lines, "bind" method of magicgui works inside magicclass.
        fgui_info = callable_to_classes(func)
        n_empty = sum(
            1
            for _wdg_cls, _prm in fgui_info
            if _wdg_cls is EmptyWidget or _prm.options.get("bind", None) is not None
        )
        nparams = argcount(func) - n_empty
        if len(fgui_info) == 0:
            _first_is_file_edit = False
        else:
            _first_is_file_edit = issubclass(fgui_info[0][0], FileEdit)

        has_preview = get_additional_option(func, "preview", None) is not None

        if nparams == 0 and not has_preview:
            # We don't want a dialog with a single widget "Run" to show up.
            def run_function():
                # NOTE: callback must be defined inside function. Magic class must be
                # "compiled" otherwise function wrappings are not ready!
                mgui = _build_mgui(widget, func, self)
                _set_parent(mgui, self)
                out = mgui()

                return out

        elif nparams == 1 and _first_is_file_edit and not has_preview:
            # We don't want to open a magicgui dialog and again open a file dialog.

            def run_function():
                mgui = _build_mgui(widget, func, self)
                _set_parent(mgui, self)
                out = show_dialog_from_mgui(mgui)
                self._popup_mode.connect_close_callback(mgui)
                return out

        else:
            _prep_func = _define_popup(self, func, widget)

            def run_function():
                mgui = _build_mgui(widget, func, self)
                print("run")
                _need_title_bar = self._popup_mode.need_title_bar()
                if not mgui._initialized_for_magicclass:  # connect only once
                    _prep_func(mgui)
                    if _need_title_bar:
                        mgui.label = ""
                        # to avoid name collision
                        mgui.name = f"mgui-{id(mgui._function)}"
                        mgui.margins = (0, 0, 0, 0)
                        if not isinstance(mgui[0], Separator):
                            title = Separator(
                                orientation="horizontal", title=text, button=True
                            )
                            title.btn_clicked.connect(mgui.hide)
                            mgui.insert(0, title)
                    mgui._initialized_for_magicclass = True

                    if self._close_on_run and not mgui._auto_call:
                        self._popup_mode.connect_close_callback(mgui)

                if nparams == 1 and _first_is_file_edit:
                    fdialog: FileEdit = mgui[int(_need_title_bar)]
                    if result := fdialog._show_file_dialog(
                        fdialog.mode,
                        caption=fdialog._btn_text,
                        start_path=str(fdialog.value),
                        filter=fdialog.filter,
                    ):
                        fdialog.value = result
                    else:
                        return None

                mgui.activated.emit()
                self._popup_mode.activate_magicgui(mgui, self)
                return None

        widget.changed.connect(run_function)

        # If design is given, load the options.
        widget.from_options(func)

        # keybinding
        keybinding = get_additional_option(func, "keybinding", None)
        if keybinding is not None:
            shortcut = as_shortcut(keybinding)
            widget.set_shortcut(shortcut)
        if isinstance(obj, abstractapi) and obj.get_location() is not None:
            widget.visible = False
        return widget

    def _search_parent_magicclass(self) -> MagicTemplate:
        """Find the ancestor."""
        current_self = self
        while (
            parent := getattr(current_self, "__magicclass_parent__", None)
        ) is not None:
            current_self = parent
        return current_self

    def _iter_child_magicclasses(
        self,
        level: int = 0,
        max_level: int = 999999,
    ) -> Iterable[tuple[int, MagicTemplate]]:
        """Iterate over all the child magic classes"""
        if level >= max_level:
            return
        for child in self.__magicclass_children__:
            yield level + 1, child
            yield from child._iter_child_magicclasses(level=level + 1)

    def _call_with_return_callback(self, fname: str, *args, **kwargs) -> None:
        from magicclass.core import get_function_gui

        fgui = get_function_gui(self, fname)
        fgui(*args, **kwargs)
        return None


class BaseGui(MagicTemplate):
    def __init__(
        self, close_on_run=True, popup_mode=PopUpMode.popup, error_mode=ErrorMode.msgbox
    ):
        self._macro_instance = GuiMacro(self, options=defaults)
        self.__magicclass_parent__: BaseGui | None = None
        self.__magicclass_children__: WeakSet[MagicTemplate] = WeakSet()
        self._close_on_run = close_on_run
        self._popup_mode = popup_mode or PopUpMode.popup
        self._error_mode = error_mode or ErrorMode.msgbox
        self._my_symbol = Symbol.var("ui")
        self._icon = None

    def __init_subclass__(cls, **kwargs):
        pass

    @property
    def icon(self):
        """Icon of this GUI."""
        return self._icon

    @icon.setter
    def icon(self, val):
        icon = get_icon(val)
        qicon = icon.get_qicon(self)
        self._icon = icon
        if hasattr(self.native, "setIcon"):
            self.native.setIcon(qicon)
        else:
            self.native.setWindowIcon(qicon)


class ContainerLikeGui(BaseGui, mguiLike):
    # This class enables similar API between magicgui widgets and additional widgets
    # in magicclass such as menu and toolbar.
    _component_class = Action
    changed = Signal(object)
    _list: list[AbstractAction | ContainerLikeGui]
    native: QtW.QMenu | QtW.QToolBar

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

    def _update_icon(self):
        for child in self._list:
            if hasattr(child, "_update_icon"):
                child._update_icon()

    def _create_widget_from_field(self, name: str, fld: MagicField):
        if fld.not_ready():
            raise TypeError(
                f"MagicField {name} does not contain enough information for widget "
                "creation"
            )

        fld.name = fld.name or name
        action = fld.get_action(self)

        if action.support_value and fld.record:
            # By default, set value function will be connected to the widget.
            getvalue = type(fld) in (MagicField, BoxMagicField)
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
        raise AttributeError("Can't set item to widgets. Use append or insert instead.")

    def __delitem__(self, key: int | str) -> None:
        if isinstance(key, str):
            key = self.index(key)
        self.native.removeAction(self[key].native)
        del self._list[key]

    def append(self, obj: Callable | ContainerLikeGui | AbstractAction) -> None:
        return self.insert(len(self._list), obj)

    def index(self, value: Any, start: int = 0, stop: int = 9223372036854775807) -> int:
        """Return index of a specific widget instance (or widget name)."""
        if isinstance(value, str):
            value = self[value]
        return super().index(value, start, stop)

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
            arr = np.asarray(bits).reshape(h, w, c)
        else:
            bits.setsize(h * w * c)
            arr = np.frombuffer(bits, np.uint8).reshape(h, w, c)

        return arr[:, :, [2, 1, 0, 3]]

    def _repr_png_(self):
        """Return PNG representation of the widget for QtConsole."""
        from io import BytesIO

        try:
            from imageio import imwrite
        except ImportError:
            print(
                "(For a nicer magicmenu widget representation in "
                "Jupyter, please `pip install imageio`)"
            )
            return None

        with BytesIO() as file_obj:
            imwrite(file_obj, self.render(), format="png")
            file_obj.seek(0)
            return file_obj.read()

    def close(self):
        """Close the widget."""
        return self.native.close()

    def hide(self):
        """Hide the widget."""
        return self.native.hide()

    def show(self, run=True):
        """Show the widget."""
        return self.native.show()

    def __iter__(self) -> Iterator[ContainerLikeGui | AbstractAction]:
        return iter(self._list)

    def __len__(self) -> int:
        return len(self._list)


def _get_widget_name(widget: Widget):
    # To escape the local scope
    return widget.name


def _set_parent(mgui: FunctionGui, ui: BaseGui):
    mgui.native.setParent(
        ui._search_parent_magicclass().native,
        mgui.native.windowFlags(),
    )


def _create_gui_method(self: BaseGui, obj: MethodType):
    func_sig = inspect.signature(obj)

    # Method type cannot set __signature__ attribute.
    @functools.wraps(obj)
    def func(*args, **kwargs):
        return obj(*args, **kwargs)

    func.__signature__ = func_sig

    # This block enables instance methods in "bind" or "choices" of ValueWidget.
    all_params: list[inspect.Parameter] = []
    for param in func.__signature__.parameters.values():
        if is_annotated(param.annotation):
            annot, opt = split_annotated_type(param.annotation)
            param = MagicParameter(
                param.name,
                param.kind,
                default=param.default,
                annotation=annot,
                gui_options=opt,
            )

        if isinstance(param, MagicParameter):
            _arg_bind = param.options.get("bind", None)
            _arg_choices = param.options.get("choices", None)
            _new_option = param.options.copy()

            # If bound method is a class method, use self.method(widget).
            if isinstance(_arg_bind, str):
                try:
                    _arg_bind = eval_attribute(type(self), _arg_bind)
                except Exception:
                    pass
                else:
                    warnings.warn(
                        "Binding method name string is deprecated for the safety "
                        "reason. Please use method itself.",
                        DeprecationWarning,
                        stacklevel=2,
                    )

            if isinstance(_arg_bind, BoundLiteral):
                _arg_bind = _arg_bind.eval(type(self))

            if is_instance_method(_arg_bind):
                _new_option["bind"] = method_as_getter(self, _arg_bind)

            # If a MagicFiled is bound, bind the value of the connected widget.
            elif isinstance(_arg_bind, MagicField):
                _new_option["bind"] = _arg_bind.as_remote_getter(self)

            # If choices are provided by a class method, use self.method(widget).
            if isinstance(_arg_choices, str):
                _arg_choices = eval_attribute(type(self), _arg_choices)

            if is_instance_method(_arg_choices):
                _new_option["choices"] = method_as_getter(self, _arg_choices)

            _param = MagicParameter(
                name=param.name,
                kind=param.kind,
                default=param.default,
                annotation=split_annotated_type(param.annotation)[0],
                gui_options=_new_option,
            )
        else:
            _param = param

        all_params.append(_param)

    func.__signature__ = func.__signature__.replace(parameters=all_params)
    if isinstance(func.__signature__, MagicMethodSignature):
        func.__signature__.additional_options = getattr(
            func_sig, "additional_options", {}
        )
    return func


def _build_mgui(widget_: Clickable, func: Callable, parent: BaseGui):
    """Build a magicgui from a function for the give button/action."""
    if widget_.mgui is not None:
        return widget_.mgui
    try:
        sig = getattr(func, "__signature__", None)
        if isinstance(sig, MagicMethodSignature):
            opt = sig.additional_options
        else:
            opt = {}

        # confirmation
        if "confirm" in opt:
            func = _implement_confirmation(func, parent, opt["confirm"])

        # Wrap function to deal with errors in a right way.
        func = parent._error_mode.wrap_handler(func, parent=parent)

        call_button = opt.get("call_button", None)
        layout = opt.get("layout", "vertical")
        labels = opt.get("labels", True)
        auto_call = opt.get("auto_call", False)
        mgui = FunctionGuiPlus(
            func, call_button, layout=layout, labels=labels, auto_call=auto_call
        )
        # set function GUI.
        widget_.mgui = mgui
        qmgui: QtW.QWidget = mgui.native
        qmgui.setWindowTitle(widget_.text or widget_.name or "")
        if parent._popup_mode is PopUpMode.popup:
            QtGui.QShortcut(QtGui.QKeySequence("Esc"), qmgui, activated=mgui.close)
            QtGui.QShortcut(
                QtGui.QKeySequence("Shift+Return"),
                qmgui,
                activated=lambda: mgui(),
            )

        preview_setting = opt.get("preview", None)
        if preview_setting is not None:
            btn_text, is_auto_call, previewer = preview_setting
            mgui.append_preview(
                previewer.__get__(parent), btn_text, auto_call=is_auto_call
            )
        setup_func = opt.get("setup", None)
        if setup_func is not None:
            setup_func(parent, mgui)

    except Exception as e:
        msg = (
            "Exception was raised during building magicgui from method "
            f"{func.__name__}.\n{e.__class__.__name__}: {e}"
        )
        widget_.mgui = None
        raise MagicGuiBuildError(msg)

    return _connect_functiongui_event(mgui, opt)


def _connect_functiongui_event(
    mgui: FunctionGuiPlus, opt: dict[str, Any]
) -> FunctionGuiPlus:
    _on_calling = opt.get("on_calling", [])
    for cb in _on_calling:
        mgui.calling.connect(cb)

    _on_called = opt.get("on_called", [])
    for cb in _on_called:
        mgui.called.connect(lambda: cb(mgui))
    return mgui


def _get_index(container: Container[Widget], widget_or_name: Widget | str) -> int:
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
    into: str | None = get_additional_option(method, "into")
    if into is None:
        return self
    for _, child_instance in self._iter_child_magicclasses():
        if child_instance.__class__.__name__ == into:
            break
    else:
        raise ValueError(f"{widget_or_name} not found.")
    return child_instance


def convert_function(obj: Callable, default: str | None = None, is_method: bool = True):
    """Convert function for macro recording and validation."""
    _record_policy = get_additional_option(obj, "record", default)
    if _record_policy is None:
        new_attr = inject_recorder(obj, is_method)
    elif _record_policy == "false":
        new_attr = inject_validator_only(obj, is_method)
    elif _record_policy == "all-false":
        new_attr = inject_silencer(obj, is_method)
    else:
        raise ValueError(f"Invalid record policy: {_record_policy}")
    return new_attr


def convert_attributes(
    cls: type[_T], hide: tuple[type, ...], record: bool = True
) -> dict[str, Any]:
    """
    Convert class attributes into macro recordable ones.

    Returned dictionary can be directly used for the third argument of `type`
    constructor. To avoid converting all the callables in subclasses, subclasses that
    will be iterated over can be restricted using `hide` argument.

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
    _pass = (
        property,
        classmethod,
        staticmethod,
        type,
        Widget,
        MagicField,
        abstractapi,
    )
    mro = [c for c in cls.__mro__ if c not in hide]
    default = None if record else "false"
    for subcls in reversed(mro):
        for name, obj in subcls.__dict__.items():
            _isfunc = callable(obj)
            if isinstance(obj, _MagicTemplateMeta):
                new_attr = copy_class(obj, cls.__qualname__, name=name)
            elif name.startswith("_") or isinstance(obj, _pass) or not _isfunc:
                # private method, non-action-like object or not-callable object are
                # passed.
                new_attr = obj
            elif _isfunc:
                if hasattr(Container, name):
                    # Container methods should not be converted.
                    new_attr = obj
                else:
                    new_attr = convert_function(obj, default)
            else:
                new_attr = obj

            _dict[name] = new_attr
    # replace the macro object with the dummy one.
    if not record:
        _dict["macro"] = macro
    return _dict


_T0 = TypeVar("_T0", Widget, AbstractAction, BaseGui)


@overload
def normalize_insertion(parent: BaseGui, obj: Callable) -> FunctionGui: ...


@overload
def normalize_insertion(parent: BaseGui, obj: _T0) -> _T0: ...


def normalize_insertion(parent: BaseGui, obj: Callable | Widget | AbstractAction):
    if isinstance(obj, Callable):
        # Sometimes users want to dynamically add new functions to GUI.
        if isinstance(obj, FunctionGui):
            if obj.parent is None:
                MagicGuiPostRunCallback.install(parent, obj)
            _obj = obj
        else:
            obj = convert_function(obj, is_method=False).__get__(parent)
            _obj = parent._create_widget_from_method(obj)

        method_name = getattr(obj, "__name__", None)
        if method_name and not hasattr(parent, method_name):
            object.__setattr__(parent, method_name, obj)
    else:
        _obj = obj
    return _obj


_dummy_macro = DummyMacro()


@property
def macro(self: BaseGui):
    """Return the dummy macro object"""
    return _dummy_macro


def _define_popup(self: BaseGui, obj, widget: Clickable):
    # deal with popup mode.
    popup_mode = self._popup_mode
    if popup_mode == PopUpMode.popup:
        # To be popped up correctly, window flags of FunctionGui should be
        # "windowFlags" and should appear at the center.
        def _prep(mgui: FunctionGui):
            if mgui.native.parent() is not self.native:
                _set_parent(mgui, self)
                move_to_screen_center(mgui.native)
                mgui.show()

    elif popup_mode == PopUpMode.parentlast:

        def _prep(mgui: FunctionGui):
            parent_self = self._search_parent_magicclass()
            parent_self.append(mgui)

    elif popup_mode == PopUpMode.first:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            child_self.insert(0, mgui)

    elif popup_mode == PopUpMode.last:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            child_self.append(mgui)

    elif popup_mode == PopUpMode.above:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            i = _get_index(child_self, widget)
            child_self.insert(i, mgui)

    elif popup_mode == PopUpMode.below:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            i = _get_index(child_self, widget)
            child_self.insert(i + 1, mgui)

    elif popup_mode == PopUpMode.dock:
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

    elif popup_mode == PopUpMode.parentsub:

        def _prep(mgui: FunctionGui):
            from .class_gui import find_window_ancestor

            parent_self = find_window_ancestor(self)
            parent_self._widget._mdiarea.addSubWindow(mgui.native)

    elif popup_mode == PopUpMode.dialog:

        def _prep(mgui: FunctionGui):
            mgui.call_button.visible = False

    else:
        raise RuntimeError(popup_mode)
    return _prep


_void = object()


def _is_separator(attr) -> bool:
    if isinstance(attr, str) and attr == "separator":
        return True
    if attr is getattr(_mgui_types, "Separator", _void):
        return True
    return False


def _implement_confirmation(
    method: MethodType,
    self: BaseGui,
    opt: ConfirmDict,
):
    """Implement confirmation callback to a method."""
    sig = inspect.signature(method)

    @functools.wraps(method)
    def _method(*args, **kwargs):
        if self[method.__name__].running:
            arguments = sig.bind(*args, **kwargs)
            arguments.apply_defaults()
            all_args = arguments.arguments
            all_args.update(self=self)
            need_confirmation = False
            condition = opt["condition"]
            if isinstance(condition, str):
                try:
                    need_confirmation = eval(condition, {}, all_args)
                except Exception as e:
                    msg = e.args[0]
                    e.args = (
                        f"Exception happened on evaluating condition {condition!r}.\n"
                        f"{type(e).__name__}: {msg}",
                    )
                    raise e
            elif callable(condition):
                need_confirmation = condition(self)
            else:
                warnings.warn(
                    f"Condition {condition} should be callable or string but got type "
                    f"{type(condition)}. No confirmation was executed.",
                    UserWarning,
                )
            if need_confirmation:
                callback = opt["callback"]
                text = opt["text"]
                callback(text.format(**all_args), self)

        return method(*args, **kwargs)

    if hasattr(method, "__signature__"):
        _method.__signature__ = method.__signature__

    return _method


def _empty_func(name: str) -> Callable[[Any], None]:
    """Create a named function that does nothing."""

    def f(x):
        pass

    f.__name__ = name
    return f


def _find_viewer_ancestor(widget: QtW.QWidget) -> napari.Viewer | None:
    """Return the closest parent napari Viewer."""
    try:
        parent = widget.parent()
        while parent:
            if hasattr(parent, "_qt_viewer"):  # QMainWindow
                return parent._qt_viewer.viewer

            parent = parent.parent()
        return None
    except RuntimeError:
        return None
