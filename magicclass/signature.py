from __future__ import annotations

import sys
from typing import Any, Callable, TypedDict, overload, Literal, TYPE_CHECKING
from typing_extensions import Annotated, get_origin, get_args

from magicgui.signature import MagicSignature, MagicParameter
from magicgui.widgets import FunctionGui
import inspect

from macrokit import Mock
from magicclass.utils import get_signature

__all__ = [
    "MagicMethodSignature",
    "MagicSignature",
    "MagicParameter",
    "get_additional_option",
    "upgrade_signature",
    "is_annotated",
    "split_annotated_type",
]

if TYPE_CHECKING:
    from magicclass._gui import BaseGui


class ConfirmDict(TypedDict):
    text: str
    condition: str | Mock | Callable
    callback: Callable[[str, BaseGui], Any]


class AdditionalOptions(TypedDict, total=False):
    record: bool
    keybinding: str
    into: str
    copyto: str
    moveto: str
    gui: bool
    on_called: list[Callable]
    confirm: ConfirmDict


def upgrade_signature(
    func,
    gui_options: dict | None = None,
    caller_options: dict | None = None,
    additional_options: AdditionalOptions = None,
):
    """
    Upgrade function signature to MagicMethodSignature. The input function may have
    a inspect.Signature or magicgui.signature.Magicsignature.

    Parameters
    ----------
    func : callable
        Input function.
    gui_options : dict, optional
        Options of FunctionGui.
    caller_options : dict, optional
        Options of PushButton.
    additional_options : AdditionalOptions, optional
        Additional options that will be used in magic class.

    Returns
    -------
    callable
        Same function with upgraded signature
    """
    gui_options = gui_options or {}
    caller_options = caller_options or {}
    additional_options = additional_options or {}

    sig = get_signature(func)

    new_gui_options = MagicMethodSignature.get_gui_options(sig).copy()
    new_gui_options.update(gui_options)

    # Annotated options should also be updated
    for k, v in sig.parameters.items():
        annot = v.annotation
        if is_annotated(annot):
            _, widget_option = split_annotated_type(annot)
            if k in new_gui_options:
                widget_option.update(new_gui_options[k])

    new_caller_options = getattr(sig, "caller_options", {}).copy()
    new_caller_options.update(caller_options)

    new_additional_options = getattr(sig, "additional_options", {}).copy()
    new_additional_options.update(additional_options)

    func.__signature__ = MagicMethodSignature.from_signature(
        sig,
        gui_options=new_gui_options,
        caller_options=new_caller_options,
        additional_options=new_additional_options,
    )

    return func


# fmt: off
@overload
def get_additional_option(obj: Any, option: Literal["preview"], default: Any = None) -> tuple[str, bool, Callable]: ...
@overload
def get_additional_option(obj: Any, option: Literal["confirm"], default: Any = None) -> ConfirmDict: ...
@overload
def get_additional_option(obj: Any, option: Literal["gui"], default: Any = None) -> bool: ...
@overload
def get_additional_option(obj: Any, option: Literal["record"], default: Any = None) -> str: ...
@overload
def get_additional_option(obj: Any, option: Literal["setup"], default: Any = None) -> Callable: ...
@overload
def get_additional_option(obj: Any, option: str, default: Any = None) -> Any: ...
# fmt: on


def get_additional_option(obj, option, default=None):
    """Safely get an additional option from any objects."""
    if isinstance(obj, FunctionGui):
        sig = getattr(obj._function, "__signature__", None)
    else:
        sig = getattr(obj, "__signature__", None)
    if isinstance(sig, MagicMethodSignature):
        opt = sig.additional_options
        return opt.get(option, default)
    else:
        return default


class _void:
    """private sentinel."""


class MagicMethodSignature(MagicSignature):
    """
    This class also retains parameter options for PushButton itself, aside from the FunctionGui options
    that will be needed when the button is pushed.
    """

    def __init__(
        self,
        parameters=None,
        *,
        return_annotation=inspect.Signature.empty,
        gui_options: dict[str, dict] = None,
        caller_options: dict[str] = None,
        additional_options: dict[str] = None,
    ):
        super().__init__(
            parameters=parameters,
            return_annotation=return_annotation,
            gui_options=gui_options,
        )
        self.caller_options = caller_options or {}
        self.additional_options = additional_options or {}

    @classmethod
    def from_signature(
        cls,
        sig: inspect.Signature,
        gui_options=None,
        caller_options=None,
        additional_options=None,
    ) -> MagicMethodSignature:
        if not isinstance(sig, inspect.Signature):
            raise TypeError("'sig' must be an instance of 'inspect.Signature'")

        # prepare parameters again
        parameters = {
            k: inspect.Parameter(
                param.name,
                param.kind,
                default=param.default,
                annotation=param.annotation,
            )
            for k, param in sig.parameters.items()
        }

        return cls(
            list(parameters.values()),
            return_annotation=sig.return_annotation,
            gui_options=gui_options,
            caller_options=caller_options,
            additional_options=additional_options,
        )

    @classmethod
    def get_gui_options(cls, sig: inspect.Signature | MagicSignature) -> dict:
        if type(sig) is inspect.Signature:
            out: dict = {}
            for k, v in sig.parameters.items():
                annot = v.annotation
                if is_annotated(annot):
                    _, widget_option = split_annotated_type(annot)
                    out[k] = widget_option
            return out
        else:
            return {k: v.options for k, v in sig.parameters.items()}

    def replace(
        self,
        *,
        parameters=_void,
        return_annotation: Any = _void,
    ) -> MagicMethodSignature:
        """Create a customized copy of the Signature.

        Pass ``parameters`` and/or ``return_annotation`` arguments
        to override them in the new copy.
        """
        if parameters is _void:
            parameters = self.parameters.values()

        if return_annotation is _void:
            return_annotation = self.return_annotation
        cls = type(self)
        return cls(
            parameters,
            return_annotation=return_annotation,
            gui_options=cls.get_gui_options(self),
            caller_options=self.caller_options,
            additional_options=self.additional_options,
        )


if sys.version_info < (3, 9):
    dict_ = dict
else:
    dict_ = dict[str, Callable]


class ValidatorDict(dict_):
    """Dictionary of validators"""

    def __init__(self, sig: inspect.Signature):
        self._sig = sig
        super().__init__()

    def validate(
        self, obj: Any, *args, **kwargs
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        """Validate arguments and return validated arguments."""
        if self:
            bound = self._sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = bound.arguments.copy()
            for name, validator in self.items():
                val = arguments[name]
                bound.arguments[name] = validator(obj, val, arguments)
            args, kwargs = bound.args, bound.kwargs
        return args, kwargs


def create_validators(sig: inspect.Signature) -> ValidatorDict:
    """Construct a validator dict from a signature."""
    validators = ValidatorDict(sig)
    for param in sig.parameters.values():
        if is_annotated(param.annotation):
            validator = param.annotation.__metadata__[0].pop("validator", None)
            if validator is not None:
                validators[param.name] = _normalize_validator(validator)
    return validators


def _normalize_validator(validator: Callable) -> Callable:
    if not callable(validator):
        raise TypeError("validator must be a callable.")
    sig = inspect.signature(validator)
    if len(sig.parameters) == 1:

        def out(self, value: Any, args: dict[str, Any]):
            return validator(value)

    elif len(sig.parameters) == 2:

        def out(self, value: Any, args: dict[str, Any]):
            return validator(self, value)

    elif len(sig.parameters) == 3:
        out = validator
    else:
        raise TypeError(
            f"validator must have 1-3 parameters but given function is `{sig}`."
        )
    return out


def is_annotated(annotation: Any) -> bool:
    """Check if a type hint is an Annotated type."""
    return get_origin(annotation) is Annotated


def split_annotated_type(annotation) -> tuple[Any, dict]:
    """Split an Annotated type into its base type and options dict."""
    if not is_annotated(annotation):
        raise TypeError("Type hint must be an 'Annotated' type.")

    typ, *meta = get_args(annotation)
    all_meta = {}
    for m in meta:
        if not isinstance(m, dict):
            raise TypeError(
                "Invalid Annotated format for magicgui. Arguments must be a dict"
            )
        all_meta.update(m)

    return typ, all_meta
