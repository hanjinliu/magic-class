from __future__ import annotations
from functools import wraps
import inspect
from typing import Callable, Iterable, Iterator, Union, TYPE_CHECKING, TypeVar, overload
from typing_extensions import ParamSpec
from magicgui.widgets import Label
from macrokit import Expr

from ._typing import Color
from .signature import upgrade_signature

if TYPE_CHECKING:
    from .gui import BaseGui
    from .gui.mgui_ext import Action
    from magicgui.widgets._bases import ButtonWidget

nStrings = Union[str, Iterable[str]]

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


def set_options(
    layout: str = "vertical",
    labels: bool = True,
    call_button: bool | str | None = None,
    auto_call: bool = False,
    **options,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Set MagicSignature to functions.

    By decorating a method with this function, ``magicgui`` will create a widget with these
    options.

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

    def wrapper(func: Callable[P, R]) -> Callable[P, R]:
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
    width: int = None,
    height: int = None,
    min_width: int = None,
    min_height: int = None,
    max_width: int = None,
    max_height: int = None,
    text: str = None,
    icon_path: str = None,
    icon_size: tuple[int, int] = None,
    font_size: int = None,
    font_family: int = None,
    font_color: Color = None,
    background_color: Color = None,
    visible: bool = True,
):
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
    icon_path : str, optional
        Path to icon file. ``min_width`` and ``min_height`` will be automatically set to the icon size
        if not given.
    icon_size : tuple of two int, optional
        Icon size.
    font_size : int, optional
        Font size of the text.
    visible : bool default is True
        Button visibility.
    """
    if icon_size is not None:
        if min_width is None:
            min_width = icon_size[0]
        if min_height is None:
            min_height = icon_size[1]

    caller_options = locals()

    @overload
    def wrapper(obj: type[T]) -> type[T]:
        ...

    @overload
    def wrapper(obj: Callable[P, R]) -> Callable[P, R]:
        ...

    def wrapper(obj):
        if isinstance(obj, type):
            _post_init = getattr(obj, "__post_init__", lambda self: None)

            def __post_init__(self):
                _post_init(self)
                for k, v in caller_options.items():
                    if v is not None:
                        setattr(self, k, v)

            obj.__post_init__ = __post_init__
        else:
            upgrade_signature(obj, caller_options=caller_options)
        return obj

    return wrapper


def click(
    enables: nStrings = None,
    disables: nStrings = None,
    enabled: bool = True,
    shows: nStrings = None,
    hides: nStrings = None,
    visible: bool = True,
):
    """
    Set options of push buttons related to button clickability.

    Parameters
    ----------
    enables : str or iterable of str, optional
        Enables other button(s) in this list when clicked.
    disables : str or iterable of str, optional
        Disables other button(s) in this list when clicked.
    enabled : bool, default is True
        The initial clickability state of the button.
    shows : str or iterable of str, optional
        Make other button(s) in this list visible when clicked.
    hides : str or iterable of str, optional
        Make other button(s) in this list invisible when clicked.
    visible: bool, default is True
        The initial visibility of the button.
    """
    enables = _assert_iterable(enables)
    disables = _assert_iterable(disables)
    shows = _assert_iterable(shows)
    hides = _assert_iterable(hides)

    def wrapper(func):
        @wraps(func)
        def f(self, *args, **kwargs):
            out = func(self, *args, **kwargs)
            for button in _iter_widgets(self, enables):
                button.enabled = True
            for button in _iter_widgets(self, disables):
                button.enabled = False
            for button in _iter_widgets(self, shows):
                button.visible = True
            for button in _iter_widgets(self, hides):
                button.visible = False

            return out

        caller_options = {"enabled": enabled, "visible": visible}
        upgrade_signature(f, caller_options=caller_options)
        return f

    return wrapper


def do_not_record(method: Callable[P, R]) -> Callable[P, R]:
    """Wrapped method will not be recorded in macro."""
    upgrade_signature(method, additional_options={"record": False})
    return method


def bind_key(*key) -> Callable[[Callable[P, R]], Callable[P, R]]:
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

    def wrapper(
        method: Callable[P, R],
    ) -> Callable[P, R]:
        upgrade_signature(method, additional_options={"keybinding": key})
        return method

    return wrapper


def confirm(text: str, call_button_text: str = "OK"):
    """
    Confirm if it is OK to run function in GUI. Useful when the function will irreversibly
    delete or update something in GUI.

    Parameters
    ----------
    text : str
        Confirmation text, such as "Are you sure to run this function?".
    call_button_text : str, default is "OK"
        Text shown on the call button.
    """
    if not isinstance(text, str):
        raise TypeError(
            f"The first argument of 'confirm' must be a str bug got {type(text)}"
        )

    def _decorator(method: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(method)
        if len(sig.parameters) != 1:
            raise ValueError(
                "Currently 'confirm' only supports methods that take no argument."
            )

        @do_not_record
        @set_options(
            call_button=call_button_text,
            labels=False,
            label={"widget_type": Label, "value": text},
        )
        def _method(self: BaseGui, label=None):
            out = method(self)
            expr = Expr.parse_method(self, method, (), {})
            self.macro.append(expr)
            return out

        _method.__name__ = method.__name__
        _method.__qualname__ = method.__qualname__
        _method.__module__ = method.__module__
        return _method

    return _decorator


def nogui(method: Callable[P, R]) -> Callable[P, R]:
    """Wrapped method will not be converted into a widget."""
    upgrade_signature(method, additional_options={"gui": False})
    return method


def _assert_iterable(obj):
    if obj is None:
        obj = []
    elif isinstance(obj, str) or callable(obj):
        obj = [obj]
    return obj


def _iter_widgets(
    self: BaseGui, descriptors: Iterable[list[str]] | Iterable[Callable]
) -> Iterator[ButtonWidget | Action]:
    for f in descriptors:
        if callable(f):
            # A.B.func -> B.func, if self is an object of A.
            f = f.__qualname__.split(self.__class__.__name__)[1][1:]

        if isinstance(f, str):
            *clsnames, funcname = f.split(".")
            # search for parent class that match the description.
            ins = self
            for a in clsnames:
                if a != "":
                    ins = getattr(ins, a)
                else:
                    ins = ins.__magicclass_parent__

            button = ins[funcname]
        else:
            raise TypeError(f"Unexpected type in click decorator: {type(f)}")
        yield button
