from __future__ import annotations
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Iterable, Any
import numpy as np

_HARD_TO_RECORD = (np.ndarray,) # This is a temporal solution to avoid recording layer as an numpy

def _safe_str(obj):
    if isinstance(obj, _HARD_TO_RECORD):
        out = f"var{id(obj)}"
    elif isinstance(obj, Path):
        out = f"r'{obj}'"
    elif hasattr(obj, "__name__"):
        out = obj.__name__
    elif isinstance(obj, str):
        out = repr(obj)
    else:
        out = str(obj)
    return out

class Macro(list):
    def append(self, __object:Expr):
        if not isinstance(__object, Expr):
            raise TypeError("Cannot append objects to Macro except for MacroExpr objecs.")
        return super().append(__object)
    
    def __str__(self) -> str:
        return "\n".join(map(str, self))
        
class Head(Enum):
    init    = auto()
    method  = auto()
    getattr = auto()
    setattr = auto()
    getitem = auto()
    setitem = auto()
    call    = auto()
    assign  = auto()
    value   = auto()
    comment = auto()

QUOTE = "'"

class Expr:
    """
    Python expression class. Inspired by Julia (https://docs.julialang.org/en/v1/manual/metaprogramming/),
    this class enables efficient macro recording and macro operation.
    
    Expr objects are mainly composed of "head" and "args". "Head" denotes what kind of operation it is,
    and "args" denotes the arguments needed for the operation. Other attributes, such as "symbol", is not
    necessary as a Expr object but it is useful to create executable codes.
    """    
    n = 0
    _map = {
        Head.init   : lambda e: f"{e.symbol} = {e.args[0]}({', '.join(map(str, e.args[1:]))})",
        Head.method : lambda e: f"{e.symbol}.{e.args[0]}({', '.join(map(str, e.args[1:]))})",
        Head.getattr: lambda e: f"{e.symbol}.{str(e.args[0]).strip(QUOTE)}",
        Head.setattr: lambda e: f"{e.symbol}.{str(e.args[0]).strip(QUOTE)} = {e.args[1]}",
        Head.getitem: lambda e: f"{e.symbol}[{e.args[0]}]",
        Head.setitem: lambda e: f"{e.symbol}[{e.args[0]}] = {e.args[1]}",
        Head.call   : lambda e: f"{e.symbol}({', '.join(map(str, e.args))})",
        Head.assign : lambda e: f"{e.symbol}={e.args[0]}",
        Head.value  : lambda e: str(e.args[0]),
        Head.comment: lambda e: f"# {e.args[0]}",
    }
    
    def __init__(self, head:Head, args:Iterable[Any], symbol:str="ui"):
        self.head = head
        if head == Head.value:
            self.args = args
        else:
            self.args = list(map(self.__class__.parse, args))
        self.symbol = symbol
        self.number = self.__class__.n
        self.__class__.n += 1
    
    def __repr__(self) -> str:
        return self._repr()
    
    def _repr(self, ind:int=0):
        if self.head == Head.value:
            return str(self)
        out = [f"head: {self.head.name}\n{' '*ind}args:\n"]
        for i, arg in enumerate(self.args):
            out.append(f"{i:>{ind+2}}: {arg._repr(ind+4)}\n")
        return "".join(out)
    
    def __str__(self) -> str:
        return self.__class__._map[self.head](self)
    
    @classmethod
    def parse_method(cls, func:Callable, args:tuple[Any], kwargs:dict[str, Any], symbol:str="ui"):
        head = Head.method
        inputs = [func]
        for a in args:
            inputs.append(a)
                
        for k, v in kwargs.items():
            inputs.append(cls(Head.assign, [v], symbol=k))
        return cls(head=head, args=inputs, symbol=symbol)

    @classmethod
    def parse_init(cls, other_cls:type, args:tuple[Any], kwargs:dict[str, Any], symbol:str="ui"):
        self = cls.parse_method(other_cls, args, kwargs, symbol=symbol)
        self.head = Head.init
        return self
    
    @classmethod
    def parse(cls, a: Any):
        return a if isinstance(a, cls) else cls(Head.value, [_safe_str(a)])
    
    def str_as(self, symbol:str):
        old_symbol = self.symbol
        self.symbol = symbol
        out = str(self)
        self.symbol = old_symbol
        return out