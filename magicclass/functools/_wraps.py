from __future__ import annotations

from typing import Callable, TypeVar
import inspect
from docstring_parser import parse, compose


_C = TypeVar("_C", Callable, type)


def wraps(template: Callable | inspect.Signature) -> Callable[[_C], _C]:
    """
    Update signature using a template. If class is wrapped, then all the methods
    except for those start with "__" will be wrapped.

    Parameters
    ----------
    template : Callable or inspect.Signature object
        Template function or its signature.

    Returns
    -------
    Callable
        A wrapper which take a function or class as an input and returns same
        function or class with updated signature(s).
    """
    from ..utils import iter_members

    def wrapper(f: _C) -> _C:
        if isinstance(f, type):
            for name, attr in iter_members(f):
                if callable(attr) or isinstance(attr, type):
                    wrapper(attr)
            return f

        old_signature = inspect.signature(f)

        old_params = old_signature.parameters

        if callable(template):
            template_signature = inspect.signature(template)
        elif isinstance(template, inspect.Signature):
            template_signature = template
        else:
            raise TypeError(
                "template must be a callable object or signature, "
                f"but got {type(template)}."
            )

        # update empty signatures
        template_params = template_signature.parameters
        new_params: list[inspect.Parameter] = []

        for key, param in old_params.items():
            if (
                param.annotation is inspect.Parameter.empty
                and param.default is inspect.Parameter.empty
            ):
                new_params.append(
                    template_params.get(
                        key,
                        inspect.Parameter(key, inspect.Parameter.POSITIONAL_OR_KEYWORD),
                    )
                )
            else:
                new_params.append(param)

        # update empty return annotation
        if old_signature.return_annotation is inspect.Parameter.empty:
            return_annotation = template_signature.return_annotation
        else:
            return_annotation = old_signature.return_annotation

        # update signature
        f.__signature__ = inspect.Signature(
            parameters=new_params, return_annotation=return_annotation
        )

        # update docstring
        fdoc = parse(f.__doc__)
        tempdoc = parse(template.__doc__)
        fdoc.short_description = fdoc.short_description or tempdoc.short_description
        fdoc.long_description = fdoc.long_description or tempdoc.long_description
        fdoc.meta = fdoc.meta or tempdoc.meta
        f.__doc__ = compose(fdoc)

        return f

    return wrapper
