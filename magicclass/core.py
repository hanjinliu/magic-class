from __future__ import annotations
from functools import wraps as functools_wraps
import inspect
from types import ModuleType
import warnings
from weakref import WeakValueDictionary
from typing import Any, TYPE_CHECKING, Callable
from macrokit import Symbol, Expr

from magicclass._gui.class_gui import (
    ClassGuiBase,
    ClassGui,
    FrameClassGui,
    GroupBoxClassGui,
    MainWindowClassGui,
    SubWindowsClassGui,
    ScrollableClassGui,
    DraggableClassGui,
    ButtonClassGui,
    CollapsibleClassGui,
    HCollapsibleClassGui,
    SplitClassGui,
    TabbedClassGui,
    StackedClassGui,
    ToolBoxClassGui,
    ResizableClassGui,
    ListClassGui,
)
from magicclass._gui._base import (
    PopUpMode,
    ErrorMode,
    defaults,
    MagicTemplate,
    check_override,
    convert_attributes,
)
from magicclass._gui import ContextMenuGui, MenuGui, ToolBarGui
from magicclass._app import get_app
from magicclass.types import WidgetType

# activate type registration things.
from magicclass import _register_types

del _register_types

if TYPE_CHECKING:
    from magicclass.stylesheets import StyleSheet
    from magicclass._gui import MenuGuiBase
    from magicclass._gui.mgui_ext import Clickable
    from magicclass._gui._function_gui import FunctionGuiPlus
    from magicclass.types import WidgetTypeStr, PopUpModeStr, ErrorModeStr
    from magicclass.help import HelpWidget
    from macrokit import Macro

_BASE_CLASS_SUFFIX = ".base"

_TYPE_MAP: dict[WidgetType, type[ClassGuiBase]] = {
    WidgetType.none: ClassGui,
    WidgetType.scrollable: ScrollableClassGui,
    WidgetType.draggable: DraggableClassGui,
    WidgetType.split: SplitClassGui,
    WidgetType.collapsible: CollapsibleClassGui,
    WidgetType.hcollapsible: HCollapsibleClassGui,
    WidgetType.button: ButtonClassGui,
    WidgetType.toolbox: ToolBoxClassGui,
    WidgetType.tabbed: TabbedClassGui,
    WidgetType.stacked: StackedClassGui,
    WidgetType.list: ListClassGui,
    WidgetType.groupbox: GroupBoxClassGui,
    WidgetType.frame: FrameClassGui,
    WidgetType.resizable: ResizableClassGui,
    WidgetType.subwindows: SubWindowsClassGui,
    WidgetType.mainwindow: MainWindowClassGui,
}


def magicclass(
    class_: type | None = None,
    *,
    layout: str = "vertical",
    labels: bool = True,
    name: str = None,
    visible: bool | None = None,
    close_on_run: bool = None,
    popup_mode: PopUpModeStr | PopUpMode = None,
    error_mode: ErrorModeStr | ErrorMode = None,
    widget_type: WidgetTypeStr | WidgetType = WidgetType.none,
    icon: Any | None = None,
    stylesheet: str | StyleSheet = None,
    properties: dict[str, Any] = None,
    record: bool = True,
    symbol: str = "ui",
):
    """
    Decorator that can convert a Python class into a widget.

    >>> @magicclass
    >>> class C:
    >>>     ...
    >>> ui = C()
    >>> ui.show()  # open GUI

    Parameters
    ----------
    class_ : type, optional
        Class to be decorated.
    layout : str, "vertical" or "horizontal", default is "vertical"
        Layout of the main widget.
    labels : bool, default is True
        If true, magicgui labels are shown.
    name : str, optional
        Name of GUI.
    visible : bool, optional
        Initial visibility of GUI. Useful when magic class is nested.
    close_on_run : bool, default is True
        If True, magicgui created by every method will be deleted after the method is
        completed without exceptions, i.e. magicgui is more like a dialog.
    popup_mode : str or PopUpMode, default is PopUpMode.popup
        Option of how to popup FunctionGui widget when a button is clicked.
    error_mode : str or ErrorMode, default is ErrorMode.msgbox
        Option of how to raise errors during function calls.
    widget_type : WidgetType or str, optional
        Widget type of container.
    icon : Any, optional
        Path to the icon image or any object that can be converted into an icon.
    stylesheet : str or StyleSheet object, optional
        Set stylesheet to the widget if given.
    properties : dict, optional
        Set properties to the widget if given. This argument is useful when you want
        to set width, height or margin without defining __post_init__.
    record : bool, default is True
        If True, macro recording is enabled.
    symbol : str, default is "ui"
        The identifier used in macro to represent this widget.

    Returns
    -------
    Decorated class or decorator.
    """
    if popup_mode is None:
        popup_mode = defaults["popup_mode"]
    if close_on_run is None:
        close_on_run = defaults["close_on_run"]
    if error_mode is None:
        error_mode = defaults["error_mode"]

    if isinstance(widget_type, str):
        widget_type = widget_type.lower()

    widget_type = WidgetType(widget_type)

    def wrapper(cls) -> type[ClassGui]:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")

        class_gui = _TYPE_MAP[widget_type]

        if not issubclass(cls, MagicTemplate):
            check_override(cls)

        # get class attributes first
        doc = cls.__doc__
        sig = inspect.signature(cls)
        annot = cls.__dict__.get("__annotations__", {})
        mod = cls.__module__
        qualname = cls.__qualname__

        new_attrs = convert_attributes(cls, hide=class_gui.__mro__, record=record)
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (class_gui, oldclass), new_attrs)

        newclass.__signature__ = sig
        newclass.__doc__ = doc
        newclass.__module__ = mod
        newclass.__qualname__ = qualname

        # concatenate annotations
        newclass.__annotations__ = class_gui.__annotations__.copy()
        newclass.__annotations__.update(annot)

        @functools_wraps(oldclass.__init__)
        def __init__(self: MagicTemplate, *args, **kwargs):
            # Without "app = " Jupyter freezes after closing the window!
            app = get_app()

            gui_kwargs = dict(
                layout=layout,
                labels=labels,
                name=name or cls.__name__,
                visible=visible,
                close_on_run=close_on_run,
                popup_mode=PopUpMode(popup_mode),
                error_mode=ErrorMode(error_mode),
            )

            # Inheriting Container's constructor is the most intuitive way.
            if kwargs and "__init__" not in cls.__dict__:
                gui_kwargs.update(kwargs)
                kwargs = {}

            class_gui.__init__(self, **gui_kwargs)

            with self.macro.blocked():
                super(oldclass, self).__init__(*args, **kwargs)

            self._convert_attributes_into_widgets()

            if widget_type in (WidgetType.collapsible, WidgetType.button):
                self.text = self.name

            if icon:
                self.icon = icon
            if stylesheet:
                self.native.setStyleSheet(str(stylesheet))
            if hasattr(self, "__post_init__"):
                with self.macro.blocked():
                    self.__post_init__()
            if properties:
                for k, v in properties.items():
                    setattr(self, k, v)
            self._my_symbol = _as_symbol(symbol)

        newclass.__init__ = __init__

        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__

        return newclass

    if class_ is None:
        return wrapper
    else:
        return wrapper(class_)


def magicmenu(
    class_: type = None,
    *,
    close_on_run: bool = None,
    popup_mode: str | PopUpMode = None,
    error_mode: str | ErrorMode = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    record: bool = True,
):
    """Decorator that converts a Python class into a menu bar."""
    return _call_magicmenu(**locals(), menugui_class=MenuGui)


def magiccontext(
    class_: type = None,
    *,
    into: Callable | None = None,
    close_on_run: bool = None,
    popup_mode: str | PopUpMode = None,
    error_mode: str | ErrorMode = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    record: bool = True,
):
    """Decorator that converts a Python class into a context menu."""

    if popup_mode is None:
        popup_mode = defaults["popup_mode"]
    if close_on_run is None:
        close_on_run = defaults["close_on_run"]
    if error_mode is None:
        error_mode = defaults["error_mode"]

    if popup_mode in (
        PopUpMode.above,
        PopUpMode.below,
        PopUpMode.first,
        PopUpMode.last,
    ):
        raise ValueError(f"Mode {popup_mode.value} is not compatible with Menu.")

    def wrapper(cls) -> type[ContextMenuGui]:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")

        if not issubclass(cls, MagicTemplate):
            check_override(cls)

        # get class attributes first
        doc = cls.__doc__
        sig = inspect.signature(cls)
        mod = cls.__module__
        qualname = cls.__qualname__

        new_attrs = convert_attributes(cls, hide=ContextMenuGui.__mro__, record=record)
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (ContextMenuGui, oldclass), new_attrs)

        newclass.__signature__ = sig
        newclass.__doc__ = doc
        newclass.__module__ = mod
        newclass.__qualname__ = qualname

        @functools_wraps(oldclass.__init__)
        def __init__(self: MagicTemplate, *args, **kwargs):
            # Without "app = " Jupyter freezes after closing the window!
            app = get_app()

            gui_kwargs = dict(
                close_on_run=close_on_run,
                popup_mode=PopUpMode(popup_mode),
                error_mode=ErrorMode(error_mode),
                labels=labels,
                name=name or cls.__name__,
            )

            # Inheriting Container's constructor is the most intuitive way.
            if kwargs and "__init__" not in cls.__dict__:
                gui_kwargs.update(kwargs)
                kwargs = {}

            ContextMenuGui.__init__(self, **gui_kwargs)

            with self.macro.blocked():
                super(oldclass, self).__init__(*args, **kwargs)

            self._convert_attributes_into_widgets()

            if icon:
                self.icon = icon
            if hasattr(self, "__post_init__"):
                with self.macro.blocked():
                    self.__post_init__()
            if into is not None:
                from .signature import upgrade_signature

                upgrade_signature(into, additional_options={"context_menu": self})

        newclass.__init__ = __init__

        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__

        return newclass

    return wrapper if class_ is None else wrapper(class_)


def magictoolbar(
    class_: type = None,
    *,
    close_on_run: bool = None,
    popup_mode: str | PopUpMode = None,
    error_mode: str | ErrorMode = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    record: bool = True,
):
    """Decorator that converts a Python class into a menu bar."""
    return _call_magicmenu(**locals(), menugui_class=ToolBarGui)


def _call_magicmenu(
    class_: type = None,
    close_on_run: bool = True,
    popup_mode: str | PopUpMode = None,
    error_mode: str | ErrorMode = None,
    labels: bool = True,
    name: str = None,
    icon: Any | None = None,
    record: bool = True,
    menugui_class: type[MenuGuiBase] = None,
):
    """
    Parameters
    ----------
    class_ : type, optional
        Class to be decorated.
    close_on_run : bool, default is True
        If True, magicgui created by every method will be deleted after the method is completed without
        exceptions, i.e. magicgui is more like a dialog.
    popup_mode : bool, default is True
        If True, magicgui created by every method will be poped up, else they will be appended as a
        part of the main widget.

    Returns
    -------
    Decorated class or decorator.
    """

    if popup_mode is None:
        popup_mode = defaults["popup_mode"]
    if close_on_run is None:
        close_on_run = defaults["close_on_run"]
    if error_mode is None:
        error_mode = defaults["error_mode"]

    if popup_mode in (
        PopUpMode.above,
        PopUpMode.below,
        PopUpMode.first,
        PopUpMode.last,
    ):
        raise ValueError(f"Mode {popup_mode.value} is not compatible with Menu.")

    def wrapper(cls) -> type[menugui_class]:
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")

        if not issubclass(cls, MagicTemplate):
            check_override(cls)

        # get class attributes first
        doc = cls.__doc__
        sig = inspect.signature(cls)
        mod = cls.__module__
        qualname = cls.__qualname__

        new_attrs = convert_attributes(cls, hide=menugui_class.__mro__, record=record)
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (menugui_class, oldclass), new_attrs)

        newclass.__signature__ = sig
        newclass.__doc__ = doc
        newclass.__module__ = mod
        newclass.__qualname__ = qualname

        @functools_wraps(oldclass.__init__)
        def __init__(self: MagicTemplate, *args, **kwargs):
            # Without "app = " Jupyter freezes after closing the window!
            app = get_app()

            gui_kwargs = dict(
                close_on_run=close_on_run,
                popup_mode=PopUpMode(popup_mode),
                error_mode=ErrorMode(error_mode),
                labels=labels,
                name=name or cls.__name__,
            )

            # Inheriting Container's constructor is the most intuitive way.
            if kwargs and "__init__" not in cls.__dict__:
                gui_kwargs.update(kwargs)
                kwargs = {}

            menugui_class.__init__(self, **gui_kwargs)

            with self.macro.blocked():
                super(oldclass, self).__init__(*args, **kwargs)

            self._convert_attributes_into_widgets()

            if icon:
                self.icon = icon
            if hasattr(self, "__post_init__"):
                with self.macro.blocked():
                    self.__post_init__()

        newclass.__init__ = __init__

        # Users may want to override repr
        newclass.__repr__ = oldclass.__repr__

        return newclass

    return wrapper if class_ is None else wrapper(class_)


magicmenu.__doc__ += _call_magicmenu.__doc__
magiccontext.__doc__ += _call_magicmenu.__doc__

_HELPS: WeakValueDictionary[int, MagicTemplate] = WeakValueDictionary()


def build_help(ui: MagicTemplate, parent=None) -> HelpWidget:
    """
    Build a widget for user guide. Once it is built, widget will be cached.

    Parameters
    ----------
    ui : MagicTemplate
        Magic class UI object.

    Returns
    -------
    HelpWidget
        Help of the input UI.
    """
    ui_id = id(ui)
    if ui_id in _HELPS.keys():
        help_widget = _HELPS[ui_id]
    else:
        from .help import HelpWidget

        if parent is None:
            parent = ui.native
        help_widget = HelpWidget(ui, parent=parent)
        _HELPS[ui_id] = help_widget
    return help_widget


def get_button(ui: MagicTemplate | ModuleType, name: str | None = None) -> Clickable:
    """
    Get the button/action object for the given method.

    This function is a helper function for magicclass. Using this method is
    always safer than directly accessing it by ``ui["method"]``.
    Either of following expression is allowed.

    >>> get_button(ui, "method")
    >>> get_button(ui.method)

    """
    if name is None:
        if hasattr(ui, "__self__") and callable(ui):
            func = ui
            ui = func.__self__
            name = func.__name__
        else:
            raise TypeError(
                "The first argument of `get_button() must be a method if "
                "the method name is not given."
            )
    widget: Clickable = ui[name]

    if not hasattr(widget, "mgui"):
        raise TypeError(f"Widget {widget} does not have FunctionGui inside it.")

    if widget._unwrapped:
        from magicclass.signature import get_additional_option

        opt = get_additional_option(getattr(ui, name), "into", None)
        if opt is not None:
            for child_instance in ui._iter_child_magicclasses():
                _name = child_instance.__class__.__name__
                if _name == opt:
                    widget = child_instance[name]
                    return widget
            raise ValueError(f"Could not find {opt} in {ui}.")
    return widget


def get_function_gui(
    ui: MagicTemplate | ModuleType, name: str = None
) -> FunctionGuiPlus:
    """
    Get the FunctionGui object hidden beneath push button or menu action.

    This function is a helper function for magicclass. Using this method is
    always safer than directly accessing it by ``ui["method"].mgui``.
    Either of following expression is allowed.

    >>> get_function_gui(ui, "method")
    >>> get_function_gui(ui.method)

    """
    if name is None:
        if hasattr(ui, "__self__") and callable(ui):
            func = ui
            ui = func.__self__
            name = func.__name__
        else:
            raise TypeError(
                "The first argument of `get_function_gui() must be a method if "
                "the method name is not given."
            )
    else:
        func = getattr(ui, name)
    widget: Clickable = ui[name]

    if not hasattr(widget, "mgui"):
        raise TypeError(f"Widget {widget} does not have FunctionGui inside it.")

    if widget.mgui is not None:
        return widget.mgui

    from ._gui._base import _build_mgui, _create_gui_method

    func = _create_gui_method(ui, func)
    mgui = _build_mgui(widget, func, ui)
    return mgui


def repeat(ui: MagicTemplate, index: int = -1) -> None:
    """
    Repeat last operation on GUI using recorded macro.

    Parameters
    ----------
    ui : MagicTemplate
        Target magic-class widget.
    index : int, default is -1
        Which execution will be repeated. Any object that support list slicing can be used.
        By default the last operation will be repeated.
    """
    warnings.warn(
        "repeat() is deprecated and will be removed soon. Use `ui.macro.repeat_method()` "
        "to specify call options in more detail.",
        DeprecationWarning,
    )
    line = ui.macro[index]
    try:
        line.eval({"ui": ui})
    except Exception as e:
        msg = e.args[0]
        msg = f"Caused by >>> {line}. {msg}"
        raise e
    return None


def update_widget_state(ui: MagicTemplate, macro: Macro | str | None = None) -> None:
    """
    Update widget values based on a macro.

    This helper function works similar to the ``update_widget`` method of ``FunctionGui``.
    In most cases, this function will be used for restoring a state from a macro recorded
    before. Value changed signal will not be emitted within this operation.

    Parameters
    ----------
    ui : MagicTemplate
        Magic class instance.
    macro : Macro or str, optional
        An executable macro or string that dictates how GUI will be updated.
    """
    from macrokit import Head, Macro

    if macro is None:
        macro = ui.macro
    elif isinstance(macro, str):
        s = macro
        macro = Macro()
        for line in s.split("\n"):
            macro.append(line)
    elif not isinstance(macro, Macro):
        raise TypeError(
            f"The second argument must be a Macro or str, got {type(macro)}."
        )

    for expr in macro:
        if expr.head is Head.call:
            # ui.func(...)
            fname = str(expr.at(0, 1))
            args, kwargs = expr.eval_call_args()
            if fname.startswith("_"):
                if fname != "_call_with_return_callback":
                    continue
                fgui = get_function_gui(ui, args[0])

            else:
                fgui = get_function_gui(ui, fname)

            with fgui.changed.blocked():
                for key, value in kwargs.items():
                    getattr(fgui, key).value = value

        elif expr.head is Head.assign:
            # ui.field.value = ...
            # ui.vfield = ...
            expr.eval({}, {str(ui._my_symbol): ui})

    return None


class Parameters:
    def __init__(self):
        self.__name__ = self.__class__.__name__
        self.__qualname__ = self.__class__.__qualname__

        sig = [
            inspect.Parameter(name="self", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        for name, attr in inspect.getmembers(self):
            if name.startswith("__") or callable(attr):
                continue
            sig.append(
                inspect.Parameter(
                    name=name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=attr,
                )
            )
        if hasattr(self.__class__, "__annotations__"):
            annot = self.__class__.__annotations__
            for name, t in annot.items():
                sig.append(
                    inspect.Parameter(
                        name=name,
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=t,
                    )
                )

        self.__signature__ = inspect.Signature(sig)

    def __call__(self, *args) -> None:
        params = list(self.__signature__.parameters.keys())[1:]
        for a, param in zip(args, params):
            setattr(self, param, a)

    def as_dict(self) -> dict[str, Any]:
        """
        Convert parameter fields into a dictionary.

        >>> class params(Parameters):
        >>>     i = 1
        >>>     j = 2

        >>> p = params()
        >>> p.as_dict() # {"i": 1, "j": 2}
        """
        params = list(self.__signature__.parameters.keys())[1:]
        return {param: getattr(self, param) for param in params}


def _as_symbol(s: str) -> Symbol | Expr:
    if isinstance(s, str):
        return Symbol(s)
    elif not isinstance(s, (Symbol, Expr)):
        raise TypeError(f"Expected a string or Symbol, got {type(s)}.")
    return s
