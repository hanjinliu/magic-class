from __future__ import annotations
from typing import Any
from magicgui.signature import MagicSignature
from magicgui.widgets import FunctionGui
import inspect
from .utils import get_signature

def upgrade_signature(func, gui_options: dict = None, caller_options: dict = None,
                      additional_options: dict = None):
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
    additional_options : dict, optional
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
    
    new_caller_options = getattr(sig, "caller_options", {}).copy()
    new_caller_options.update(caller_options)

    new_additional_options = getattr(sig, "additional_options", {}).copy()
    new_additional_options.update(additional_options)

    func.__signature__ = MagicMethodSignature.from_signature(
            sig, 
            gui_options=new_gui_options, 
            caller_options=new_caller_options,
            additional_options=new_additional_options
            )

    return func

def get_additional_option(obj: Any, option: str, default = None):
    if isinstance(obj, FunctionGui):
        sig = getattr(obj._function, "__signature__", None)
    else:
        sig = getattr(obj, "__signature__", None)
    if isinstance(sig, MagicMethodSignature):
        opt = sig.additional_options
        return opt.get(option, default)
    else:
        return default
    

class MagicMethodSignature(MagicSignature):
    """
    This class also retains parameter options for PushButton itself, aside from the FunctionGui options
    that will be needed when the button is pushed.
    """    
    def __init__(
        self,
        parameters = None,
        *,
        return_annotation = inspect.Signature.empty,
        gui_options: dict[str, dict] = None,
        caller_options: dict[str] = None,
        additional_options: dict[str] = None,
    ):
        super().__init__(parameters=parameters, return_annotation=return_annotation, gui_options=gui_options)
        self.caller_options = caller_options or {}
        self.additional_options = additional_options or {}
    
    @classmethod
    def from_signature(cls, sig: inspect.Signature, gui_options=None, caller_options=None,
                       additional_options=None) -> MagicMethodSignature:
        if not isinstance(sig, inspect.Signature):
            raise TypeError("'sig' must be an instance of 'inspect.Signature'")
        
        # prepare parameters again
        parameters = {k: inspect.Parameter(param.name,
                                           param.kind,
                                           default=param.default,
                                           annotation=param.annotation) 
                      for k, param in sig.parameters.items()}
        
        return cls(
            list(parameters.values()),
            return_annotation=sig.return_annotation,
            gui_options=gui_options,
            caller_options=caller_options,
            additional_options=additional_options,
            )
    
    @classmethod
    def get_gui_options(cls, self: inspect.Signature|MagicSignature):
        if type(self) is inspect.Signature:
            return {}
        else:
            return {k: v.options for k, v in self.parameters.items()}