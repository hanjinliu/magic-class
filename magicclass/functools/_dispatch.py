from __future__ import annotations

import sys
from typing import Callable, Sequence, Any, get_type_hints, overload, TYPE_CHECKING
from abc import get_cache_token
import functools
import inspect

from magicgui.signature import MagicParameter

from magicclass.signature import (
    get_signature,
    split_annotated_type,
    upgrade_signature,
    is_annotated,
)

if TYPE_CHECKING:
    from typing_extensions import _AnnotatedAlias


def singledispatch(func):
    """
    Single dispatch function aware of GUI options in magic-class.

    Dispatched functions are converted into a multi-valued widget. GUI configurations
    are also possible using ``@set_options`` decorator.
    """
    import types, weakref

    registry = {}
    dispatch_cache = weakref.WeakKeyDictionary()
    cache_token = None

    def dispatch(cls):
        """generic_func.dispatch(cls) -> <function implementation>

        Runs the dispatch algorithm to return the best available implementation
        for the given *cls* registered on *generic_func*.

        """
        nonlocal cache_token
        if cache_token is not None:
            current_token = get_cache_token()
            if cache_token != current_token:
                dispatch_cache.clear()
                cache_token = current_token
        try:
            impl = dispatch_cache[cls]
        except KeyError:
            try:
                impl = registry[cls]
            except KeyError:
                impl = functools._find_impl(cls, registry)
            dispatch_cache[cls] = impl
        return impl

    def register(cls, func=None, *, gui_options: dict = {}):
        """generic_func.register(cls, func) -> func

        Registers a new implementation for the given *cls* on a *generic_func*.

        """
        nonlocal cache_token
        if func is None:
            if isinstance(cls, type):
                return lambda f: register(cls, f)
            ann = getattr(cls, "__annotations__", {})
            if not ann:
                raise TypeError(
                    f"Invalid first argument to `register()`: {cls!r}. "
                    f"Use either `@register(some_class)` or plain `@register` "
                    f"on an annotated function."
                )
            func = cls

            argname, cls = next(iter(get_type_hints(func).items()))

            # Here, we also support Annotated type.
            if is_annotated(cls):
                cls, _ = split_annotated_type(cls)
            elif not isinstance(cls, type):
                raise TypeError(
                    f"Invalid annotation for {argname!r}. " f"{cls!r} is not a class."
                )
            if gui_options:
                upgrade_signature(func, gui_options={argname: gui_options})

        registry[cls] = func
        if cache_token is None and hasattr(cls, "__abstractmethods__"):
            cache_token = get_cache_token()
        dispatch_cache.clear()
        return func

    def wrapper(*args, **kw):
        if not args:
            raise TypeError(f"{funcname} requires at least " "1 positional argument")

        return dispatch(args[0].__class__)(*args, **kw)

    funcname = getattr(func, "__name__", "singledispatch function")
    registry[object] = func
    wrapper.register = register
    wrapper.dispatch = dispatch
    wrapper.registry = types.MappingProxyType(registry)
    wrapper._clear_cache = dispatch_cache.clear
    functools.update_wrapper(wrapper, func)
    return wrapper


class singledispatchmethod(functools.singledispatchmethod):
    """
    Single dispatch method aware of GUI options in magic-class.

    Dispatched functions are converted into a multi-valued widget. GUI configurations
    are also possible using ``@set_options`` decorator.
    """

    def __init__(self, func):
        if not callable(func) and not hasattr(func, "__get__"):
            raise TypeError(f"{func!r} is not callable or a descriptor")

        self.dispatcher = singledispatch(func)
        self.func = func
        if sys.version_info < (3, 10):
            self._wrapped_func = func
        functools.update_wrapper(
            self, func, assigned=("__name__", "__qualname__", "__doc__")
        )

    # fmt: off
    @overload
    def register(self, cls: type | _AnnotatedAlias, func: Callable | None, *, options: dict = {}): ...
    @overload
    def register(self, cls: Callable, *, options: dict = {}): ...
    # fmt: on

    def register(self, cls=None, func=None, *, option={}) -> Any:
        if cls is not None:
            return self.dispatcher.register(cls, func=func, gui_options=option)

        def wrapper(cls, func):
            return self.dispatcher.register(cls, func=func, gui_options=option)

        return wrapper

    @property
    def __signature__(self):
        params = []
        for _func in self.dispatcher.registry.values():
            sig = get_signature(_func)
            params.append(list(sig.parameters.values())[1])
        param1 = _merge_parameters(params)

        parameters = list(sig.parameters.values())
        parameters[1] = param1
        return sig.replace(parameters=parameters)

    @__signature__.setter
    def __signature__(self, sig):
        self.func.__signature__ = sig

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise TypeError("singledispatchmethod must be called on an instance")


def _merge_parameters(params: Sequence[inspect.Parameter]) -> MagicParameter:
    from magicclass.widgets import UnionWidget

    annotations = []
    name = None
    for param in params:
        if param.annotation is MagicParameter.empty:
            # If the first dispatch is not annotated (i.e. the default behavior),
            # do not add an empty widget.
            continue
        if name is None:
            name = param.name
            default = param.default
        annotations.append(param.annotation)

    return MagicParameter(
        name=name,
        kind=MagicParameter.POSITIONAL_OR_KEYWORD,
        default=default,
        gui_options={"widget_type": UnionWidget, "annotations": annotations},
    )
