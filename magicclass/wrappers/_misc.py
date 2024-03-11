from __future__ import annotations

import inspect
from typing import Any, Callable, TYPE_CHECKING, TypeVar, overload
import warnings
from magicgui.widgets import FunctionGui

from magicclass.types import Color
from magicclass.signature import get_additional_option, upgrade_signature

if TYPE_CHECKING:
    from magicclass._gui import MagicTemplate
    from magicclass.fields import MagicField

_F = TypeVar("_F", bound=Callable)


def set_options(
    layout: str = "vertical",
    labels: bool = True,
    call_button: bool | str | None = None,
    auto_call: bool = False,
    **options,
) -> Callable[[_F], _F]:
    """
    Set MagicSignature to functions.

    By decorating a method with this function, `magicgui` will create a widget with
    these options. These codes are similar in appearance.

    >>> # A magicgui way
    >>> @magicgui(a={...})
    >>> def func(a):
    ...     print(a)

    >>> # A magicclass way
    >>> @magicclass
    >>> class A:
    ...     @set_options(a={...})
    ...     def func(self, a):
    ...         print(a)

    Parameters
    ----------
    layout : str, default "vertical"
        The type of layout to use in FunctionGui. Must be 'horizontal' or 'vertical'.
    labels : bool, default True
        Whether labels are shown in the FunctionGui.
    call_button : bool or str, optional
        If `True`, create an additional button that calls the original
        function when clicked.  If a `str`, set the button text. If None (the
        default), it defaults to True when `auto_call` is False, and False
        otherwise.
    auto_call : bool, optional
        If `True`, changing any parameter in either the GUI or the widget attributes
        will call the original function with the current settings. by default False
    options : dict
        Parameter options.
    """

    def wrapper(func: _F) -> _F:
        if options:
            sig = inspect.signature(func)
            rem = options.keys() - sig.parameters.keys()
            if rem:
                warnings.warn(
                    f"Unknown arguments found in set_options of {func.__name__}: {rem}",
                    UserWarning,
                )

        upgrade_signature(
            func,
            gui_options=options,
            additional_options={
                "call_button": call_button,
                "layout": layout,
                "labels": labels,
                "auto_call": auto_call,
            },
        )

        return func

    return wrapper


def set_design(
    width: int | None = None,
    height: int | None = None,
    min_width: int | None = None,
    min_height: int | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
    text: str | Callable[[str], str] | None = None,
    icon: str | int | None = None,
    location: type[MagicTemplate] | MagicField | None = None,
    font_size: int | None = None,
    font_family: str | None = None,
    font_color: Color | None = None,
    background_color: Color | None = None,
    visible: bool | None = None,
) -> Callable[[_F], _F]:
    """
    Change button/action design by calling setter when the widget is created.

    Parameters
    ----------
    width : int, optional
        Button width. Call `button.width = width`.
    height : int, optional
        Button height. Call `button.height = height`.
    min_width : int, optional
        Button minimum width. Call `button.min_width = min_width`.
    min_height : int, optional
        Button minimum height. Call `button.min_height = min_height`.
    max_width : int, optional
        Button maximum width. Call `button.max_width = max_width`.
    max_height : int, optional
        Button maximum height. Call `button.max_height = max_height`.
    text : str or callable, optional
        Button text. Call `button.text = text`. A function can be given to set the text
        from the function name.
    icon : str, optional
        Path to icon file. `min_width` and `min_height` will be automatically set to the
        icon size if not given.
    location : magic-class or magic-field of magic-class, optional
        If given, the button will be added to the given magic-class.
    font_size : int, optional
        Font size of the text.
    visible : bool default True
        Button visibility.
    """
    caller_options = {}
    if width is not None:
        caller_options["width"] = int(width)
    if height is not None:
        caller_options["height"] = int(height)
    if min_width is not None:
        caller_options["min_width"] = int(min_width)
    if min_height is not None:
        caller_options["min_height"] = int(min_height)
    if max_width is not None:
        caller_options["max_width"] = int(max_width)
    if max_height is not None:
        caller_options["max_height"] = int(max_height)
    if font_size is not None:
        caller_options["font_size"] = int(font_size)
    if font_family is not None:
        caller_options["font_family"] = str(font_family)
    if font_color is not None:
        caller_options["font_color"] = font_color
    if background_color is not None:
        caller_options["background_color"] = background_color
    if visible is not None:
        caller_options["visible"] = bool(visible)
    if icon is not None:
        caller_options["icon"] = icon

    def wrapper(obj):
        if callable(text):
            caller_options["text"] = text(obj.__name__)
        elif text is not None:
            caller_options["text"] = str(text)
        if isinstance(obj, type):
            if location is not None:
                raise TypeError("Cannot use location argument on classes.")
            _post_init = getattr(obj, "__post_init__", lambda self: None)

            def __post_init__(self):
                _post_init(self)
                for k, v in caller_options.items():
                    setattr(self, k, v)

            obj.__post_init__ = __post_init__
        else:
            upgrade_signature(obj, caller_options=caller_options)
            if location is not None:
                location.wraps(obj)
        return obj

    return wrapper


@overload
def do_not_record(method: None = None, recursive: bool = True) -> Callable[[_F], _F]:
    ...


@overload
def do_not_record(method: _F, recursive: bool = True) -> _F:
    ...


def do_not_record(method=None, recursive=False):
    """
    Wrapped method will not be recorded in macro.

    Parameters
    ----------
    recursive : bool, default False
        If True, all recordable methods called inside this method will also be
        suppressed.
    """

    def wrapper(f):
        if recursive:
            record = "all-false"
        else:
            record = "false"
        upgrade_signature(f, additional_options={"record": record})
        return f

    return wrapper if method is None else wrapper(method)


def bind_key(*key) -> Callable[[_F], _F]:
    """
    Define a keybinding to a button or an action.
    This function accepts several styles of shortcut expression.

    >>> @bind_key("Ctrl-A")         # napari style
    >>> @bind_key("Ctrl+A")         # Qt style
    >>> @bind_key("Ctrl+K, Ctrl+V") # Key combo

    """
    if len(key) == 1 and isinstance(key[0], str):
        key = key[0]
        # check Ctrl-A style
        lower = key.lower()
        for k in ["ctrl", "cmd", "shift", "alt"]:
            if f"{k}-" in lower:
                lower = lower.replace(f"{k}-", f"{k}+")
        key = lower
    else:
        warnings.warn(
            "`bind_key` now accepts only one string argument. "
            "Please use such as `bind_key('Ctrl+A')`.",
            DeprecationWarning,
        )
        if isinstance(key[0], tuple):
            key = key[0]

    def wrapper(method: _F) -> _F:
        upgrade_signature(method, additional_options={"keybinding": key})
        return method

    return wrapper


def nogui(method: _F) -> _F:
    """Wrapped method will not be converted into a widget."""
    upgrade_signature(method, additional_options={"gui": False})
    return method


def setup_function_gui(target: Callable):
    """
    Mark a function as a setup function for a FunctionGui.

    Function decorated with `setup_function_gui(func)` will be called when the
    FunctionGui widget for method `func` was built. This decorator is used to
    define complicated setting of a FunctionGui, which is not achievable by
    simple configurations.

    >>> @magicclass
    >>> class A:
    ...     def func(self, x: int, xmax: int):
    ...         # target function
    ...
    ...     @setup_function_gui(func)
    ...     def _setup_func(self, gui: FunctionGui):
    ...         @gui.xmax.changed.connect
    ...         def _(xmax_value):
    ...             gui.x.max = xmax_value
    """

    def wrapper(setup: Callable[[MagicTemplate, FunctionGui], None]):
        setup_qualname = setup.__qualname__
        target_qualname = target.__qualname__
        setup_qualname_list = setup_qualname.split(".")
        if (
            len(setup_qualname_list) > 1
            and setup_qualname_list[-2] != target_qualname.split(".")[-2]
        ):
            # have to search for the proper parent instance
            def _setup(self: MagicTemplate, mgui: FunctionGui):
                prev_ns = setup_qualname_list[-2]
                while self.__class__.__name__ != prev_ns:
                    self = self.__magicclass_parent__
                return setup(self, mgui)

        else:
            _setup = setup
        upgrade_signature(target, additional_options={"setup": _setup})
        upgrade_signature(setup, additional_options={"gui": False})
        return setup

    return wrapper


_Fn = TypeVar("_Fn", bound=Callable[[FunctionGui], Any])


def mark_on_calling(function: Callable) -> Callable[[_Fn], _Fn]:
    def _wrapper(on_calling: _Fn) -> _Fn:
        if opt := get_additional_option(function, "on_calling", None):
            opt.append(on_calling)
        else:
            upgrade_signature(function, additional_options={"on_calling": [on_calling]})
        return on_calling

    return _wrapper


def mark_on_called(function: Callable) -> Callable[[_Fn], _Fn]:
    def _wrapper(on_called: _Fn) -> _Fn:
        if opt := get_additional_option(function, "on_called", None):
            opt.append(on_called)
        else:
            upgrade_signature(function, additional_options={"on_called": [on_called]})
        return on_called

    return _wrapper
