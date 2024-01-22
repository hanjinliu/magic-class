# Serialize/Deserialize GUI

It is useful in some cases to save the state of the GUI and restore it later. In most
cases, widget states are defined by the widget values.

In `magic-class`, simple `serialize` and `deserialize` functions are available. These
methods can be used to save and load the state of the `magicgui`'s `Container` widgets
or any magic-class widgets. All the value widgets or value-like widgets (widgets that
have a `value` attribute) are recursively converted into dictionaries.

## Basic Usage

`serialize` and `deserialize` are available in the `magicclass.serialize` module.
`serialize` converts the widget state to a dictionary, and `deserialize` does the
opposite.

Here's an example of serializing a `magicgui`'s `FunctionGui`.

```python
from magicgui import magicgui
from magicclass.serialize import serialize, deserialize

@magicgui
def func(x: int = 1, y: str = "X"):
    pass

serialize(func)
```

``` title="Output"
{'x': 1, 'y': 'X'}
```

And it can be deserialized back to the `FunctionGui` using `deserialize`.

```python
deserialize(func, {"x": 2, "y": "Y"})
print(func)
```

``` title="Output"
<FunctionGui func(x: int = 2, y: str = 'Y')>
```

Same functions can be used to serialize and deserialize magic-class widgets.

```python
from magicclass import magicclass, field

@magicclass
class Parameters:
    x = field(1)
    y = field("X")

    def print(self):
        """Print the parameters"""
        print("x =", self.x.value, ", y =", self.y.value)

params = Parameters()
serialize(params)
```

``` title="Output"
{'x': 1, 'y': 'X'}
```

!!! note
    You may have noticed that a magic-class widget became very similar to a
    [`pydantic`](https://pydantic-docs.helpmanual.io/) model.

## Custom Serialization

If a custom `Container` subclass or a magic-class widget need a special way for
serialization and deserialization, you can define `__magicclass_serialize__` and
`__magicclass_deserialize__` methods to do this.

In the following example, widget values are saved as a tuple instead of separate
dictionary items.

```python
from magicclass import magicclass, field

@magicclass
class A:
    x = field(1)
    y = field("X")

    def __magicclass_serialize__(self):
        return {"custom_value": (self.x.value, self.y.value)}

    def __magicclass_deserialize__(self, data):
        self.x.value, self.y.value = data["custom_value"]
```
