from __future__ import annotations
import inspect
from typing import Callable, Iterable, Union, TYPE_CHECKING, TypeVar, overload
import warnings
from magicgui.widgets import FunctionGui

from .utils import show_messagebox
from .types import Color
from .signature import upgrade_signature

if TYPE_CHECKING:
    from ._gui import BaseGui

nStrings = Union[str, Iterable[str]]

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
    width: int = None,
    height: int = None,
    min_width: int = None,
    min_height: int = None,
    max_width: int = None,
    max_height: int = None,
    text: str = None,
    icon_path: str = None,
    font_size: int = None,
    font_family: int = None,
    font_color: Color = None,
    background_color: Color = None,
    visible: bool = None,
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
    font_size : int, optional
        Font size of the text.
    visible : bool default is True
        Button visibility.
    """

    caller_options = locals()
    caller_options = {k: v for k, v in caller_options.items() if v is not None}

    @overload
    def wrapper(obj: type[T]) -> type[T]:
        ...

    @overload
    def wrapper(obj: F) -> F:
        ...

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


def do_not_record(method: F) -> F:
    """Wrapped method will not be recorded in macro."""
    upgrade_signature(method, additional_options={"record": False})
    return method


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


class Canceled(RuntimeError):
    """Raised when a function is canceled"""


@overload
def confirm(
    *,
    text: str | None,
    condition: Callable[..., bool] | str | None,
    callback: Callable[[str, BaseGui], None] | None = None,
) -> Callable[[F], F]:
    ...


@overload
def confirm(
    f: F,
    *,
    text: str | None,
    condition: Callable[..., bool] | str | None,
    callback: Callable[[str, BaseGui], None] | None = None,
) -> F:
    ...


def confirm(
    f: F | None = None,
    *,
    text: str | None = None,
    condition: Callable[[BaseGui], bool] | str = None,
    callback: Callable[[str, BaseGui], None] | None = None,
):
    """
    Confirm if it is OK to run function in GUI.

    Useful when the function will irreversibly delete or update something in GUI.
    Confirmation will be executed only when function is called in GUI.

    Parameters
    ----------
    text : str, optional
        Confirmation message, such as "Are you sure to run this function?". Format
        string can also be used here, in which case arguments will be passed. For
        instance, to execute confirmation on function ``f(a, b)``, you can use
        format string ``"Running with a = {a} and b = {b}"`` then confirmation
        message will be "Running with a = 1, b = 2" if ``f(1, 2)`` is called.
        By default, message will be "Do you want to run {name}?" where "name" is
        the function name.
    condition : callable or str, optional
        Condition of when confirmation will show up. If callable, it must accept
        ``condition(self)`` and return boolean object. If string, it must be
        evaluable as literal with input arguments as local namespace. For instance,
        function ``f(a, b)`` decorated by ``confirm(condition="a < b + 1")`` will
        evaluate ``a < b + 1`` to check if confirmation is needed. Always true by
        default.
    callback : callable, optional
        Callback function when confirmation is needed. Must take a ``str`` and a
        ``BaseGui`` object as inputs. By default, message box will be shown. Useful
        for testing.
    """
    if condition is None:
        condition = lambda x: True
    if callback is None:
        callback = _default_confirmation

    def _decorator(method: F) -> F:
        _name = method.__name__

        # set text
        if text is None:
            _text = f"Do you want to run {_name}?"
        elif isinstance(text, str):
            _text = text
        else:
            raise TypeError(
                f"The first argument of 'confirm' must be a str but got {type(text)}."
            )
        upgrade_signature(
            method,
            additional_options={
                "confirm": {
                    "text": _text,
                    "condition": condition,
                    "callback": callback,
                }
            },
        )
        return method

    if f is not None:
        return _decorator(f)
    return _decorator


def _default_confirmation(text: str, gui: BaseGui):
    ok = show_messagebox(
        mode="question",
        title="Confirmation",
        text=text,
        parent=gui.native,
    )
    if not ok:
        raise Canceled("Canceled")


def nogui(method: F) -> F:
    """Wrapped method will not be converted into a widget."""
    upgrade_signature(method, additional_options={"gui": False})
    return method


def mark_preview(function: Callable, text: str = "Preview") -> Callable[[F], F]:
    """
    Define a preview of a function.

    This decorator is useful for advanced magicgui creation. A "Preview" button
    appears in the bottom of the widget built from the input function and the
    decorated function will be called with the same arguments.
    Following example shows how to define a previewer that prints the content of
    the selected file.

    .. code-block:: python

        def func(self, path: Path):
            ...

        @mark_preview(func)
        def _func_prev(self, path: Path):
            with open(path, mode="r") as f:
                print(f.read())

    Parameters
    ----------
    function : callable
        To which function previewer will be defined.
    text : str, optional
        Text of preview button.
    """

    def _wrapper(preview: F) -> F:
        sig_preview = inspect.signature(preview)
        sig_func = inspect.signature(function)
        params_preview = sig_preview.parameters
        params_func = sig_func.parameters

        less = len(params_func) - len(params_preview)
        if less == 0:
            if params_preview.keys() != params_func.keys():
                raise TypeError(
                    f"Arguments mismatch between {sig_preview!r} and {sig_func!r}."
                )
            # If argument names are identical, input arguments don't have to be filtered.
            _filter = lambda a: a

        elif less > 0:
            idx: list[int] = []
            for i, param in enumerate(params_func.keys()):
                if param in params_preview:
                    idx.append(i)
            # If argument names are not identical, input arguments have to be filtered so
            # that arguments match the inputs.
            _filter = lambda _args: (a for i, a in enumerate(_args) if i in idx)

        else:
            raise TypeError(
                f"Number of arguments of preview function {preview!r} must be equal"
                f"or smaller than that of running function {function!r}."
            )

        def _preview(*args):
            # find proper parent instance in the case of classes being nested
            from ._gui import BaseGui

            if len(args) > 0 and isinstance(args[0], BaseGui):
                ins = args[0]
                prev_ns = preview.__qualname__.split(".")[-2]
                while ins.__class__.__name__ != prev_ns:
                    ins = ins.__magicclass_parent__
                args = (ins,) + args[1:]
            # filter input arguments
            return preview(*_filter(args))

        if not isinstance(function, FunctionGui):
            upgrade_signature(
                function, additional_options={"preview": (text, _preview)}
            )
        else:
            from ._gui._function_gui import append_preview

            append_preview(function, _preview, text=text)
        return preview

    return _wrapper
