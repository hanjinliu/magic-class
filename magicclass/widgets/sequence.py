from __future__ import annotations
from typing import Any, Iterable, TypeVar, overload
from typing_extensions import get_args, get_origin
import inspect
from magicgui.widgets import create_widget, Container, PushButton
from magicgui.widgets._bases.value_widget import UNSET, ValueWidget

_V = TypeVar("_V")
    
class ListEdit(Container):
    def __init__(
        self,
        value: Iterable[_V] = UNSET,
        annotation: type = None, # such as int, str, ...
        layout: str = "horizontal",
        options: dict = None,
        **kwargs,
    ):
        if value is not UNSET:
            types = set(type(a) for a in value)
            if len(types) == 1:
                self._type = types.pop()
            else:
                self._type = str
                
        else:
            self._type = annotation if annotation is not inspect._empty else str
            value = []
            
        self.child_options = options or {}
        
        super().__init__(layout=layout, labels=False, **kwargs)
        self.margins = (0, 0, 0, 0)
        
        button_plus = PushButton(text="+")
        button_plus.changed.connect(lambda: self.append_new())
        
        button_minus = PushButton(text="-")
        button_minus.changed.connect(self.delete_last)
        
        self.append(button_plus)
        self.append(button_minus)
        
        for a in value:
            self.append_new(a)
    
    def __getitem__(self, k: int | str) -> ValueWidget:
        return super().__getitem__(k)
    
    def append_new(self, value=UNSET):
        i = len(self) - 2
        widget = create_widget(value=value, annotation=self._type, name=f"value_{i}",
                               options=self.child_options)
        self.insert(i, widget)
    
    def delete_last(self):
        try:
            self.pop(-3)
        except IndexError:
            pass
    
    @property
    def value(self):
        return ListDataView(self)

    @value.setter
    def value(self, vals:Iterable[_V]):
        for i in reversed(range(len(self))):
            if not isinstance(self[i], PushButton):
                self.pop(i)
        for v in vals:
            self.append_new(v)        
    
class ListDataView:
    def __init__(self, widget: ListEdit):
        self.widget: list[ValueWidget] = list(
            filter(lambda x: not isinstance(x, PushButton), widget)
            )
    
    def __repr__(self):
        return repr([w.value for w in self.widget])
    
    def __str__(self):
        return str([w.value for w in self.widget])
    
    def __len__(self):
        return len(self.widget)
    
    @overload
    def __getitem__(self, i: int) -> _V: ...
    @overload
    def __getitem__(self, key: slice) -> list[_V]: ...
    @overload
    def __setitem__(self, key: int, value: _V) -> None: ...
    @overload
    def __setitem__(self, key: slice, value: _V | Iterable[_V]) -> None: ...
    
    def __getitem__(self, key: int | slice):
        if isinstance(key, int):
            return self.widget[key].value
        else:
            return [w.value for w in self.widget[key]]
    
    def __setitem__(self, key: int | slice, value):
        if isinstance(key, int):
            self.widget[key].value = value
        else:
            if isinstance(value, type(self.widget[0].value)):
                for w in self.widget[key]:
                    w.value = value
            else:
                for w, v in zip(self.widget[key], value):
                    w.value = v
                    
class TupleEdit(Container):
    def __init__(
        self,
        value: Iterable[Any] = UNSET,
        annotation: type = None, # such as int, str, tuple[int, str], ...
        layout: str = "horizontal",
        options: dict = None,
        **kwargs,
    ):
            
        if value is not UNSET:
            self._types = tuple(type(a) for a in value)    
        else:
            orig = get_origin(annotation)
            args = get_args(annotation)
            
            if orig is tuple and args:
                self._types = args
            elif orig is None and len(args) == 0:
                self._types = (annotation,) * 2
            
            value = (UNSET,) * len(self._types)

        super().__init__(layout=layout, labels=False, **kwargs)
        self.margins = (0, 0, 0, 0)
        self.child_options = options or {}
        
        for i, a in enumerate(value):
            i = len(self)
            widget = create_widget(value=a, annotation=self._types[i], name=f"value_{i}", 
                                   options=self.child_options)
            self.insert(i, widget)

    
    def __getitem__(self, k: int | str) -> ValueWidget:
        return super().__getitem__(k)
    
    @property        
    def value(self):
        return tuple(w.value for w in self)

    @value.setter
    def value(self, vals: Iterable):
        if len(vals) != len(self):
            raise ValueError("Length of tuple does not match.")
        for w, v in zip(self, vals):
            w.value = v