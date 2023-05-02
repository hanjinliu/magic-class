from __future__ import annotations
import inspect
from typing import Callable, TypeVar, TYPE_CHECKING
from magicgui.widgets import FunctionGui

from magicclass.signature import upgrade_signature

_F = TypeVar("_F", bound=Callable)


if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    _P = ParamSpec("_P")
    _R = TypeVar("_R")

    class PreviewFunction(Callable[_P, _R]):
        __name__: str
        __qualname__: str

        def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            """Run function."""

        def during_preview(self, f: _F) -> _F:
            """Wrapped function will be used as a context manager during preview."""


def impl_preview(
    function: Callable | None = None,
    text: str = "Preview",
    auto_call: bool = False,
):
    """
    Define a preview of a function.

    This decorator is useful for advanced magicgui creation. A "Preview" button
    appears in the bottom of the widget built from the input function and the
    decorated function will be called with the same arguments.
    Following example shows how to define a previewer that prints the content of
    the selected file.

    >>> @magicclass
    >>> class MyGui:
    ...     def func(self, path: Path):
    ...         ...
    ...
    ...     @impl_preview(func)
    ...     def _func_prev(self, path: Path):
    ...         with open(path, mode="r") as f:
    ...             print(f.read())

    Parameters
    ----------
    function : callable, optional
        To which function previewer will be defined. If not provided, the to-be-
        decorated function itself will be used as the preview function.
    text : str, optional
        Text of the preview button or checkbox.
    auto_call : bool, default is False
        Whether the preview function will be auto-called. If true, a check box will
        appear above the call button, and the preview function is auto-called during
        it is checked.
    """
    mark_self = False

    def _outer_wrapper(target_func: Callable) -> PreviewFunction:
        target_func_sig = inspect.signature(target_func)

        def _wrapper(preview: _F) -> _F:
            _is_generator = inspect.isgeneratorfunction(preview)
            if _is_generator:
                _preview_context_generator = preview
                preview = lambda: None
                for attr in ["__name__", "__qualname__", "__module__"]:
                    if hasattr(_preview_context_generator, attr):
                        setattr(
                            preview, attr, getattr(_preview_context_generator, attr)
                        )

            _preview = impl_arg_filter(preview, target_func, target_func_sig)
            _preview.__wrapped__ = preview
            _preview.__name__ = getattr(preview, "__name__", "_preview")
            _preview.__qualname__ = getattr(preview, "__qualname__", "")

            def _set_during_preview(during: _F) -> _F:
                _during = impl_arg_filter(during, target_func, target_func_sig)
                _preview._preview_context = _during
                return during

            if not isinstance(target_func, FunctionGui):
                upgrade_signature(
                    target_func,
                    additional_options={"preview": (text, auto_call, _preview)},
                )
            else:
                from magicclass._gui._function_gui import append_preview

                append_preview(target_func, _preview, text=text, auto_call=auto_call)

            # add method
            if _is_generator:
                _set_during_preview(_preview_context_generator)
                return _preview_context_generator
            preview.during_preview = _set_during_preview
            return preview

        if mark_self:
            return _wrapper(target_func)
        return _wrapper

    if function is not None:
        return _outer_wrapper(function)
    else:
        mark_self = True
        return _outer_wrapper


mark_preview = impl_preview


def get_arg_filter(
    prev: Callable, tgt: Callable, tgt_sig: inspect.Signature
) -> Callable:
    tgt_params = tgt_sig.parameters
    prev_sig = inspect.signature(prev)
    prev_params = prev_sig.parameters

    less = len(tgt_params) - len(prev_params)
    if less == 0:
        if prev_params.keys() != tgt_params.keys():
            raise TypeError(f"Arguments mismatch between {prev_sig!r} and {tgt_sig!r}.")
        # If argument names are identical, input arguments don't have to be filtered.
        _filter = lambda a: a

    elif less > 0:
        idx: list[int] = []
        for i, param in enumerate(tgt_params.keys()):
            if param in prev_params:
                idx.append(i)
        # If argument names are not identical, input arguments have to be filtered so
        # that arguments match the inputs.
        _filter = lambda _args: (a for i, a in enumerate(_args) if i in idx)

    else:
        raise TypeError(
            f"Number of arguments of function {prev!r} must be subset of "
            f"that of running function {tgt!r}."
        )
    return _filter


def impl_arg_filter(f: _F, tgt: Callable, tgt_sig: inspect.Signature) -> _F:
    _filter = get_arg_filter(f, tgt, tgt_sig)

    def _func(*args):
        from magicclass._gui import BaseGui

        # find proper parent instance in the case of classes being nested
        if len(args) > 0 and isinstance(args[0], BaseGui):
            ins = args[0]
            qualnames = f.__qualname__.split(".")
            if len(qualnames) >= 2:
                prev_ns = qualnames[-2]
                while ins.__class__.__name__ != prev_ns:
                    if ins.__magicclass_parent__ is None:
                        break
                    ins = ins.__magicclass_parent__
                args = (ins,) + args[1:]

        with ins.macro.blocked():
            # filter input arguments
            out = f(*_filter(args))
        return out

    return _func
