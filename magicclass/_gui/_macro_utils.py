from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import inspect
from functools import partial, partialmethod, wraps as functools_wraps
from macrokit import Symbol, Expr, Head, symbol
from magicgui.widgets import FunctionGui
from magicgui.widgets._bases import ValueWidget
from .utils import get_parameters
from magicclass.utils import get_signature, thread_worker
from magicclass.signature import MagicMethodSignature


if TYPE_CHECKING:
    from ._base import MagicTemplate


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
_IS_RECORDABLE = "__is_recordable__"


def inject_recorder(func: Callable, is_method: bool = True) -> Callable:
    """Inject macro recording functionality into a function."""
    sig = get_signature(func)
    if is_method:
        sig = sig.replace(
            parameters=list(sig.parameters.values())[1:],
            return_annotation=sig.return_annotation,
        )
        _func = func
        _is_partial = isinstance(func, (partial, partialmethod))
    else:
        if isinstance(func, partial):

            @functools_wraps(func)
            def _func(self, *args, **kwargs):
                return func(*args, **kwargs)

            _already_recordable = _is_recordable(func.func)
            _func.func = func.func  # to make the function partialmethod-like
            _is_partial = True

        else:

            @functools_wraps(func)
            def _func(self, *args, **kwargs):
                return func(*args, **kwargs)

            _already_recordable = _is_recordable(func)
            _is_partial = False

        _func.__signature__ = sig.replace(
            parameters=[_SELF] + list(sig.parameters.values()),
            return_annotation=sig.return_annotation,
        )

        if _already_recordable:
            # The wrapped function is already recordable so we don't have to
            # inject macro recorder again.
            return _func

    if _is_partial:
        _record_macro = _define_macro_recorder_for_partial(sig, _func)
    else:
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
        setattr(_recordable, _IS_RECORDABLE, True)
        return _recordable

    else:
        _func._set_recorder(_record_macro)
        return _func


def _define_macro_recorder(sig: inspect.Signature, func: Callable):
    if isinstance(sig, MagicMethodSignature):
        opt = sig.additional_options
        _auto_call = opt.get("auto_call", False)
    else:
        _auto_call = False

    if sig.return_annotation is inspect.Parameter.empty:

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

    else:
        _cname_ = "_call_with_return_callback"

        def _record_macro(bgui: MagicTemplate, *args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            kwargs = dict(bound.arguments.items())
            expr = Expr.parse_method(bgui, _cname_, (func.__name__,), kwargs)
            if _auto_call:
                # Auto-call will cause many redundant macros. To avoid this, only the last
                # input will be recorded in magic-class.
                last_expr = bgui.macro[-1]
                if (
                    last_expr.head == Head.call
                    and last_expr.args[0].head == Head.getattr
                    and last_expr.at(0, 1) == expr.at(0, 1)
                    and last_expr.args[1] == expr.args[1]
                    and len(bgui.macro) > 0
                ):
                    bgui.macro.pop()
                    bgui.macro._erase_last()

            bgui.macro.append(expr)
            bgui.macro._last_setval = None
            return None

    return _record_macro


def _define_macro_recorder_for_partial(
    sig: inspect.Signature,
    func: partial | partialmethod,
):
    base_func = func.func
    if isinstance(sig, MagicMethodSignature):
        opt = sig.additional_options
        _auto_call = opt.get("auto_call", False)
    else:
        _auto_call = False

    if sig.return_annotation is inspect.Parameter.empty:

        def _record_macro(bgui: MagicTemplate, *args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            kwargs = bound.arguments
            expr = Expr.parse_method(bgui, base_func, (), kwargs)
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

    else:
        _cname_ = "_call_with_return_callback"

        def _record_macro(bgui: MagicTemplate, *args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            kwargs = bound.arguments
            expr = Expr.parse_method(bgui, _cname_, (base_func.__name__,), kwargs)
            if _auto_call:
                # Auto-call will cause many redundant macros. To avoid this, only the last
                # input will be recorded in magic-class.
                last_expr = bgui.macro[-1]
                if (
                    last_expr.head == Head.call
                    and last_expr.args[0].head == Head.getattr
                    and last_expr.at(0, 1) == expr.at(0, 1)
                    and last_expr.args[1] == expr.args[1]
                    and len(bgui.macro) > 0
                ):
                    bgui.macro.pop()
                    bgui.macro._erase_last()

            bgui.macro.append(expr)
            bgui.macro._last_setval = None
            return None

    return _record_macro


def _is_recordable(func: Callable):
    if hasattr(func, _IS_RECORDABLE):
        return getattr(func, _IS_RECORDABLE)
    if hasattr(func, "__func__"):
        return _is_recordable(func.__func__)
    return False
