from __future__ import annotations
import inspect
from typing import Any, Callable, TYPE_CHECKING, TypeVar, overload
import warnings
from magicgui.widgets import FunctionGui

from magicclass.utils import show_messagebox
from magicclass.types import Color
from magicclass.signature import get_additional_option, upgrade_signature

if TYPE_CHECKING:
    from magicclass._gui import BaseGui

R = TypeVar("R")
T = TypeVar("T")
F = TypeVar("F", bound=Callable)


def set_options(
    layout: str = "vertical",
    labels: bool = True,
    call_button: bool | str | None = None,
    auto_call: bool = False,
    **options,
) -> Callable[[F], F]:
    """
    Set MagicSignature to functions.

    By decorating a method with this function, ``magicgui`` will create a widget with these
    options. These codes are similar in appearance.

    .. code-block:: python

        # A magicgui way
        @magicgui(a={...})
        def func(a):
            ...

        # A magicclass way
        @magicclass
        class A:
            @set_options(a={...})
            def func(self, a):
                ...

    Parameters
    ----------
    layout : str, default is "vertical"
        The type of layout to use in FunctionGui. Must be one of {'horizontal', 'vertical'}.
    labels : bool, default is True
        Whether labels are shown in the FunctionGui.
    call_button : bool or str, optional
        If ``True``, create an additional button that calls the original
        function when clicked.  If a ``str``, set the button text. If None (the
        default), it defaults to True when ``auto_call`` is False, and False
        otherwise.
    auto_call : bool, optional
        If ``True``, changing any parameter in either the GUI or the widget attributes
        will call the original function with the current settings. by default False
    options : dict
        Parameter options.
    """

    def wrapper(func: F) -> F:
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
    text: str | None = None,
    icon: str | None = None,
    font_size: int | None = None,
    font_family: int | None = None,
    font_color: Color | None = None,
    background_color: Color | None = None,
    visible: bool | None = None,
) -> Callable[[type[T]], type[T]] | Callable[[F], F]:
    """
    Change button/action design by calling setter when the widget is created.

    Parameters
    ----------
    width : int, optional
        Button width. Call ``button.width = width``.
    height : int, optional
        Button height. Call ``button.height = height``.
    min_width : int, optional
        Button minimum width. Call ``button.min_width = min_width``.
    min_height : int, optional
        Button minimum height. Call ``button.min_height = min_height``.
    max_width : int, optional
        Button maximum width. Call ``button.max_width = max_width``.
    max_height : int, optional
        Button maximum height. Call ``button.max_height = max_height``.
    text : str, optional
        Button text. Call ``button.text = text``.
    icon : str, optional
        Path to icon file. ``min_width`` and ``min_height`` will be automatically set to the icon size
        if not given.
    font_size : int, optional
        Font size of the text.
    visible : bool default is True
        Button visibility.
    """
    caller_options = locals()
    caller_options = {k: v for k, v in caller_options.items() if v is not None}

    def wrapper(obj):
        if isinstance(obj, type):
            _post_init = getattr(obj, "__post_init__", lambda self: None)

            def __post_init__(self):
                _post_init(self)
                for k, v in caller_options.items():
                    setattr(self, k, v)

            obj.__post_init__ = __post_init__
        else:
            upgrade_signature(obj, caller_options=caller_options)
        return obj

    return wrapper


@overload
def do_not_record(method: None = None, recursive: bool = True) -> Callable[[F], F]:
    ...


@overload
def do_not_record(method: F, recursive: bool = True) -> F:
    ...


def do_not_record(method=None, recursive=False):
    """
    Wrapped method will not be recorded in macro.

    Parameters
    ----------
    recursive : bool, default is False
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


def bind_key(*key) -> Callable[[F], F]:
    """
    Define a keybinding to a button or an action.
    This function accepts several styles of shortcut expression.

    >>> @bind_key("Ctrl-A")         # napari style
    >>> @bind_key("Ctrl", "A")      # separately
    >>> @bind_key(Key.Ctrl + Key.A) # use Key class
    >>> @bind_key(Key.Ctrl, Key.A)  # use Key class separately

    """
    if isinstance(key[0], tuple):
        key = key[0]

    def wrapper(method: F) -> F:
        upgrade_signature(method, additional_options={"keybinding": key})
        return method

    return wrapper


def nogui(method: F) -> F:
    """Wrapped method will not be converted into a widget."""
    upgrade_signature(method, additional_options={"gui": False})
    return method


def setup_function_gui(target: Callable):
    """
    Mark a function as a setup function for a FunctionGui.

    Function decorated with ``setup_function_gui(func)`` will be called when the
    FunctionGui widget for method ``func`` was built. This decorator is used to
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

    def wrapper(setup: Callable[[BaseGui, FunctionGui], None]):
        setup_qualname = setup.__qualname__
        target_qualname = target.__qualname__
        if setup_qualname.split(".")[-2] != target_qualname.split(".")[-2]:
            # have to search for the proper parent instance
            def _setup(self: BaseGui, mgui: FunctionGui):
                prev_ns = setup_qualname.split(".")[-2]
                while self.__class__.__name__ != prev_ns:
                    self = self.__magicclass_parent__
                return setup(self, mgui)

        else:
            _setup = setup
        upgrade_signature(target, additional_options={"setup": _setup})
        upgrade_signature(setup, additional_options={"nogui": True})
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
