# Customize Macro Recording

Magic class depends its macro recording functionalities on [macro-kit](https://github.com/hanjinliu/macro-kit).
To customize macro recording, you can use functions and methods in `macrokit`.

## Define How to Record Objects

`macrokit` does not record all the values as strings because the string form of a value
could be very long (such as an image data). To define a rule of how to record a certain
type of objects, you can use `register_type` function (actually this is how
`magic-class` registers `Path` and `Enum` to make macro compatible with type mapping
rules of `magicgui`).

``` python
from macrokit import register_type
```

`register_type` takes two arguments: a type to register and a function. You have to
define the conversion rule in the second argument. The example below shows how to
record `numpy.ndarray` in the standard `np.array([...])` style.

``` python
import numpy as numpy

@register_type(np.ndarray)
def numpy_to_str(arr):
    return f"np.array({arr.tolist()})"
```
