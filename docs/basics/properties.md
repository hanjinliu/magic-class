# Use magicproperty in magic-class

In `magicclass`, properties will not be conveted into widgets. The reason for this is
that properties are usually used to get references to one of the child widgets.
``` python
from magicclass import magicclass, field

@magicclass
class A:
    @magicclass
    class B:
        x = field(int)

    @property
    def bx(self):
        return self.B.x
```

However, another property-like class `magicproperty` is available to build
a `FunctionGui`-like widget.

!!! note

    `magicproperty` is a subclass of `MagicField`.


## How to Use `magicproperty`

Basically, it is used exactly the same as the built-in `property` class, except that you
have to provide at least one type annotation for widget creation.

``` python
from magicclass import magicclass, magicproperty

@magicclass
class A:
    @magicproperty
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, val: int):
        self._x = val

    @magicproperty
    def string(self) -> str:
        return self._s

    @string.setter
    def string(self, val: str):
        self._s = val

ui = A()
ui.show()
```

![](../images_autogen/properties-0.png)

Values are updated after the "Set" button is clicked, or set programmatically.

``` python
ui.x = 10  # update the value and the GUI
ui.string = "Hello"  # update the value and the GUI
```

## Configuration of `magicproperty`

`magicproperty` can be configured similar to `magicgui`. Here's some examples of how to
configure.

``` python
@magicclass
class A:
    # set widget label
    @magicproperty(label="X")
    def x(self) -> int:
        ...

    # widget type and options
    @magicproperty(widget_type="Slider", options={"min": 0, "max": 10})
    def x(self) -> int:
        ...

    # auto-calling
    @magicproperty(auto_call=True)
    def x(self) -> int:
        ...

    # customize the button text
    @magicproperty(call_button="update x value")
    def x(self) -> int:
        ...
```

## Setter-only property

Although it's rare, built-in `property` can be setter-only. In this case, you
can only set a value and getting a value is forbidden.

``` python
class A:
    x = property()

    @x.setter
    def x(self, val):
        print("set x to", val)

    # python >= 3.9
    @property().setter
    def x(self, val):
        print("set x to", val)

a = A()
a.x = 10  # OK
a.x  # AttributeError
```

Unlike `property`, however, the getter of `magicproperty` doesn't need to be
defined because widget itself has its own value.

``` python
@magicclass
class A:
    x = magicproperty(widget_type="Slider")

    @x.setter
    def x(self, val: int):
        print("set x to", val)

    # python >= 3.9
    @magicproperty(widget_type="Slider").setter
    def x(self, val: int):
        print("set x to", val)

a = A()
a.x = 10  # OK
a.x  # Out: 10
```

An advantage of setter-only `magicproperty` is that you don't have to prepare
an additional attribute `_x` for the property `x`.

!!! note

    You can even create a `magicproperty` without any descriptors.

    ``` python
    @magicclass
    class A:
        x = magicproperty(annotation=int)
        y = magicproperty(widget_type="RangeEdit")
    ```

    In this case, getter will get the value of the widget and setter will update the
    widget value.
