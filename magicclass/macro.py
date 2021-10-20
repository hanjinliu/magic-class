from __future__ import annotations
from contextlib import contextmanager
from functools import wraps
import inspect
from copy import deepcopy
from enum import Enum, auto
from collections import UserList
from pathlib import Path
from typing import Callable, Iterable, Iterator, Any, overload, TypeVar
from types import FunctionType, MethodType
import numpy as np

T = TypeVar("T")

class Symbol:
    
    # Map of how to convert object into a symbol.
    _type_map: dict[type, Callable[[Any], str]] = {
        type: lambda e: e.__name__,
        FunctionType: lambda e: e.__name__,
        Enum: lambda e: repr(str(e.name)),
        Path: lambda e: f"r'{e}'",
    }
    
    _id_map: dict[int, Symbol] = {}
    
    def __init__(self, seq: str, type: type = Any):
        self.data = str(seq)
        self.type = type
        self.valid = True
    
    def __repr__(self) -> str:
        return ":" + self.data
    
    def __str__(self) -> str:
        return self.data
    
    def __hash__(self) -> int:
        return id(self)
    
    @classmethod
    def from_id(cls, obj: Any):
        _id = id(obj)
        try:
            out = cls._id_map[_id]
        except KeyError:
            out = symbol(obj)
            cls._id_map[_id] = out
        return out
    
    def as_annotation(self):
        return f"# {self}: {self.type}"
    
    def as_parameter(self, default=inspect._empty):
        return inspect.Parameter(self.data, 
                                 inspect.Parameter.POSITIONAL_OR_KEYWORD, 
                                 default=default,
                                 annotation=self.type)
    
    @classmethod
    def register_type(cls, type: type[T], function: Callable[[T], str]):
        if not callable(function):
            raise TypeError("The second argument must be callable.")
        cls._type_map[type] = function
    
def symbol(obj: Any) -> Symbol:
    if isinstance(obj, Symbol):
        return obj
    elif id(obj) in Symbol._id_map.keys():
        return Symbol._id_map[id(obj)]
    
    valid = True
    
    if isinstance(obj, str):
        seq = repr(obj)
    elif np.isscalar(obj): # int, float, bool, ...
        seq = obj
    elif isinstance(obj, (tuple, list)):
        seq = type(obj)([symbol(a) for a in obj])
    elif type(obj) in Symbol._type_map:
        seq = Symbol._type_map[type(obj)](obj)
    else:
        for k, func in Symbol._type_map.items():
            if isinstance(obj, k):
                seq = func(obj)
                break
        else:
            seq = f"var{hex(id(obj))}" # hexadecimals are easier to distinguish
            valid = False
            
    sym = Symbol(seq, type(seq))
    sym.valid = valid
    if not valid:
        Symbol._id_map[id(obj)] = sym
    return sym

def register_type(type: type[T], function: Callable[[T], str]):
    return Symbol.register_type(type, function)
        
class Head(Enum):
    init    = "init"
    getattr = "getattr"
    setattr = "setattr"
    getitem = "getitem"
    setitem = "setitem"
    call    = "call"
    assign  = "assign"
    value   = "value"
    comment = "comment"

_QUOTE = "'"

def sy(arg):
    return str(arg).strip(_QUOTE)

class Expr:
    """
    Python expression class. Inspired by Julia (https://docs.julialang.org/en/v1/manual/metaprogramming/),
    this class enables efficient macro recording and macro operation.
    
    Expr objects are mainly composed of "head" and "args". "Head" denotes what kind of operation it is,
    and "args" denotes the arguments needed for the operation. Other attributes, such as "symbol", is not
    necessary as a Expr object but it is useful to create executable codes.
    """
    n: int = 0
    
    # a map of how to conver expression into string.
    _map: dict[Head, Callable[[Expr], str]] = {
        Head.init   : lambda e: f"{sy(e.args[0])} = {e.args[1]}({', '.join(map(str, e.args[2:]))})",
        Head.getattr: lambda e: f"{sy(e.args[0])}.{sy(e.args[1])}",
        Head.setattr: lambda e: f"{sy(e.args[0])}.{sy(e.args[1])} = {e.args[2]}",
        Head.getitem: lambda e: f"{sy(e.args[0])}[{e.args[1]}]",
        Head.setitem: lambda e: f"{sy(e.args[0])}[{e.args[1]}] = {e.args[2]}",
        Head.call   : lambda e: f"{sy(e.args[0])}({', '.join(map(str, e.args[1:]))})",
        Head.assign : lambda e: f"{sy(e.args[0])}={e.args[1]}",
        Head.value  : lambda e: str(e.args[0]),
        Head.comment: lambda e: f"# {e.args[0]}",
    }
    
    def __init__(self, head: Head, args: Iterable[Any]):
        self.head = Head(head)
        if head == Head.value:
            self.args = list(args)
        else:
            self.args = list(map(self.__class__.parse, args))
            
        self.number = self.__class__.n
        self.__class__.n += 1
    
    def __repr__(self) -> str:
        return self._repr()
    
    def _repr(self, ind: int = 0) -> str:
        """
        Recursively expand expressions until it reaches value/assign expression.
        """
        if self.head in (Head.value, Head.assign):
            return str(self)
        out = [f"head: {self.head.name}\n{' '*ind}args:\n"]
        for i, arg in enumerate(self.args):
            out.append(f"{i:>{ind+2}}: {arg._repr(ind+4)}\n")
        return "".join(out)
    
    def __str__(self) -> str:
        return self.__class__._map[self.head](self)
    
    def __eq__(self, expr: Expr) -> bool:
        if self.head != Head.value:
            raise TypeError(f"Expression must be value, got {self.head}")
        if isinstance(expr, str):
            return self.args[0] == expr
        elif isinstance(expr, self.__class__):
            return self.args[0] == expr.args[0]
        else:
            raise ValueError(f"'==' is not supported between Expr and {type(expr)}")
    
    def copy(self):
        return deepcopy(self)
    
    def eval(self, __globals: dict[str: Any] = None, __locals: dict[str: Any] = None):
        return eval(str(self), __globals, __locals)
        
    @classmethod
    def parse_method(cls, obj: Any, func: Callable, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Expr:
        """
        Make a method call expression.
        Expression: obj.func(*args, **kwargs)
        """
        method = cls(head=Head.getattr, args=[Symbol.from_id(obj), func])
        inputs = [method] + cls.convert_args(args, kwargs)
        return cls(head=Head.call, args=inputs)

    @classmethod
    def parse_init(cls, 
                   obj: Any,
                   init_cls: type, 
                   args: tuple[Any, ...] = None, 
                   kwargs: dict[str, Any] = None) -> Expr:
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        sym = Symbol.from_id(obj)
        inputs = [sym, init_cls] + cls.convert_args(args, kwargs)
        sym.valid = True
        return cls(head=Head.init, args=inputs)
    
    @classmethod
    def parse_call(cls, 
                   func: Callable, 
                   args: tuple[Any, ...] = None, 
                   kwargs: dict[str, Any] = None) -> Expr:
        """
        Make a function call expression.
        Expression: func(*args, **kwargs)
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        inputs = [func] + cls.convert_args(args, kwargs)
        return cls(head=Head.call, args=inputs)
        
    @classmethod
    def convert_args(cls, args: tuple[Any, ...], kwargs: dict[str|Symbol, Any]) -> list:
        inputs = []
        for a in args:
            inputs.append(a)
                
        for k, v in kwargs.items():
            inputs.append(cls(Head.assign, [k, v]))
        return inputs
    
    @classmethod
    def parse(cls, a: Any) -> Expr:
        return a if isinstance(a, cls) else cls(Head.value, [symbol(a)])
    
    def iter_args(self) -> Iterator[Symbol]:
        """
        Recursively iterate along all the arguments.
        """
        for arg in self.args:
            if isinstance(arg, self.__class__):
                yield from arg.iter_args()
            elif isinstance(arg, Symbol):
                yield arg
            else:
                raise RuntimeError(arg)
    
    def iter_values(self) -> Iterator[Expr]:
        """
        Recursively iterate along all the values.
        """
        for arg in self.args:
            if isinstance(arg, self.__class__):
                if arg.head == Head.value:
                    yield arg
                else:
                    yield from arg.iter_values()
    
    
    def iter_expr(self) -> Iterator[Expr]:
        """
        Recursively iterate over all the nested Expr, until it reached to non-nested Expr.
        This method is useful in macro generation.
        """        
        yielded = False
        for arg in self.args:
            if isinstance(arg, self.__class__):
                yield from arg.iter_expr()
                yielded = True
        
        if not yielded:
            yield self
    
    def format(self, mapping: dict[Symbol, Expr], inplace: bool = False) -> Expr:
        if not inplace:
            self = self.copy()
        for arg in self.iter_values():
            try:
                new = mapping[arg.args[0]]
            except KeyError:
                pass
            else:
                arg.args[0] = new
        return self
    
class Macro(UserList):
    """
    List with pretty output customized for macro.
    """    
    def __init__(self, iterable: Iterable = (), *, active: bool = True):
        super().__init__(iterable)
        self.active = active
        
    def append(self, __object: Expr):
        if not isinstance(__object, Expr):
            raise TypeError("Cannot append objects to Macro except for MacroExpr objecs.")
        return super().append(__object)
    
    def __str__(self) -> str:
        return "\n".join(map(str, self))
    
    @overload
    def __getitem__(self, key: int | str) -> Expr: ...

    @overload
    def __getitem__(self, key: slice) -> Macro[Expr]: ...
        
    def __getitem__(self, key):
        return super().__getitem__(key)
    
    def __iter__(self) -> Iterator[Expr]:
        return super().__iter__()
    
    def __repr__(self) -> str:
        return ",\n".join(repr(expr) for expr in self)
    
    @contextmanager
    def context(self, active: bool):
        was_active = self.active
        self.active = active
        yield
        self.active = was_active
    
    def record(self, function=None, *, returned_callback: Callable[[Expr], Expr]=None):
        def wrapper(func):
            if isinstance(func, MethodType):
                if func.__name__ == "__init__":
                    def make_expr(*args, **kwargs):
                        return Expr.parse_init(args[0], args[0].__class__, args[1:], kwargs)
                elif func.__name__ == "__call__":
                    def make_expr(*args, **kwargs):
                        return Expr.parse_call(Expr(Head.getattr, [args[0], func]), args[1:], kwargs)
                else:
                    def make_expr(*args, **kwargs):
                        return Expr.parse_method(args[0], func, args[1:], kwargs)
                    
            else:
                def make_expr(*args, **kwargs):
                    return Expr.parse_call(func, args, kwargs)
                    
            @wraps(func)
            def macro_recorder_equipped(*args, **kwargs):
                with self.context(False):
                    out = func(*args, **kwargs)
                if self.active:
                    expr = make_expr(*args, **kwargs)
                    if returned_callback is not None:
                        expr = out(expr)
                    self.append(expr)
                return out
            return macro_recorder_equipped
        
        return wrapper if function is None else wrapper(function)
