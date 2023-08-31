from __future__ import annotations

from typing import Any, TYPE_CHECKING
from macrokit import Expr, Head, Symbol, parse

if TYPE_CHECKING:
    from magicclass._gui import BaseGui


def _is_thread_worker_call(line: Expr, ns: dict[str, Any]) -> bool:
    if line.head is not Head.call:
        return False
    _f = line.args[0]
    if not (isinstance(_f, Expr) and _f.head is Head.getattr):
        return False
    func_obj = _f.eval(ns)
    return hasattr(func_obj, "__thread_worker__")


def _rewrite_thread_worker_call(line: Expr) -> Expr:
    assert line.head is Head.call
    a0 = line.args[0]
    assert a0.head is Head.getattr
    _with_arun = Expr(Head.getattr, [a0, "arun"])
    expr = Expr(Head.call, [_with_arun] + line.args[1:])
    return parse(f"yield from {expr}")


def _rewrite_callback(lines: list[Expr]) -> Expr:
    func_body = Expr(Head.block, lines)
    cb_expr = Symbol("__magicclass_temp_callback")
    funcdef = Expr(Head.function, [Expr(Head.call, [cb_expr]), func_body])
    funcdef_dec = Expr(Head.decorator, [parse("thread_worker.callback"), funcdef])
    cb_yield = Expr(Head.yield_, [cb_expr])
    cb_await = Expr(Head.call, [Expr(Head.getattr, [cb_expr, "await_call"])])
    return Expr(Head.block, [funcdef_dec, cb_yield, cb_await])


CAN_PASS = frozenset(
    [Head.yield_, Head.comment, Head.class_, Head.function, Head.decorator]
)
DECORATOR = parse("thread_worker(force_async=True)")


def to_async_code(code: Expr, ui: BaseGui) -> Expr:
    """Convert the code to async-compatible code."""
    assert code.head is Head.block
    lines: list[Expr] = []
    stack: list[Expr] = []

    def _flush_stack():
        if stack:
            lines.append(_rewrite_callback(stack))
            stack.clear()
        return None

    ns = {str(ui._my_symbol): ui}
    for line in code.args:
        if _is_thread_worker_call(line, ns):
            _flush_stack()
            lines.append(_rewrite_thread_worker_call(line))
        elif line.head in CAN_PASS:
            lines.append(line)
        else:
            stack.append(line)
    if stack:
        lines.append(_rewrite_callback(stack))
    _fn = Symbol("_")
    func_body = Expr(Head.block, lines)
    funcdef = Expr(Head.function, [Expr(Head.call, [_fn, ui._my_symbol]), func_body])
    funcdef_dec = Expr(Head.decorator, [DECORATOR, funcdef])
    descriptor = Expr(Head.call, [Expr(Head.getattr, [_fn, "__get__"]), ui._my_symbol])
    funccall = Expr(Head.call, [descriptor])  # -> _.__get__(ui)()
    return Expr(Head.block, [funcdef_dec, funccall])


def run_async(code: Expr, ui: BaseGui, ns: dict[str, Any] = {}) -> Any | None:
    """Run the code in a thread worker."""
    from .thread_worker import thread_worker

    _ns = dict(
        **{
            str(ui._my_symbol): ui,
            "thread_worker": thread_worker,
        },
    )
    _ns.update(ns)
    return to_async_code(code, ui).eval(_ns)
