from __future__ import annotations
from magicgui.signature import MagicSignature
import inspect
from .utils import get_signature

def upgrade_signature(func, gui_options: dict = None, caller_options: dict = None):
    gui_options = gui_options or {}
    caller_options = caller_options or {}
    
    sig = get_signature(func)
    
    new_gui_options = MagicMethodSignature.get_gui_options(sig).copy()
    new_gui_options.update(gui_options)
    
    new_caller_options = getattr(sig, "caller_options", {}).copy()
    new_caller_options.update(caller_options)

    func.__signature__ = MagicMethodSignature.from_signature(
            sig, gui_options=new_gui_options, caller_options=new_caller_options)

    return func

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
        caller_options: dict[str] = None
    ):
        super().__init__(parameters=parameters, return_annotation=return_annotation, gui_options=gui_options)
        self.caller_options = caller_options
    
    @classmethod
    def from_signature(cls, sig: inspect.Signature, gui_options=None, caller_options=None) -> MagicMethodSignature:
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
            caller_options=caller_options
            )
    
    @classmethod
    def get_gui_options(cls, self:inspect.Signature|MagicSignature):
        if type(self) is inspect.Signature:
            return {}
        else:
            return {k: v.options for k, v in self.parameters.items()}