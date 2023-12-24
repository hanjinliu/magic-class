# Best Practice

Here's some tips that will be useful for better GUI design.

## Shared Input Parameters

If you want to control input parameters outside each `magicgui` widget, the example
below is the most naive implementation.

``` python
from magicclass import magicclass, magicmenu, field, abstractapi, set_design

@magicclass
class Main:
    @magicmenu
    class Menu:
        add = abstractapi()
        sub = abstractapi()

    a = field(float)
    b = field(float)
    result = field(float, record=False)

    @set_design(location=Menu)
    def add(self):
        """Add two values"""
        self.result.value = self.a.value + self.b.value

    @set_design(location=Menu)
    def sub(self):
        """Subtract two values"""
        self.result.value = self.a.value - self.b.value
```

However, after you calculated "4.0 + 2.0" and "6.0 - 3.0", macro
will be recorded like

``` python
ui.a.value = 4.0
ui.b.value = 2.0
ui.add()
ui.a.value = 6.0
ui.b.value = 3.0
ui.sub()
```

This is perfectly reproducible but is not user friendly. If users want to run functions
programmatically, they'll prefer styles like `add(1, 2)`. Unfriendliness is more obvious
when you changed the values of `a` and `b` alternately many times before adding them and
saw its macro recorded like

``` python title="macro"
ui.a.value = 3.0
ui.b.value = 1.0
ui.a.value = 6.0
ui.b.value = 2.0
ui.a.value = 9.0
ui.b.value = 3.0
ui.add()
```

To avoid this, you can use the ["bind" option](make_better/bind.md).

``` python hl_lines="16 21"
from typing import Annotated
from magicclass import magicclass, magicmenu, field

@magicclass
class Main:
    @magicmenu
    class Menu:
        add = abstractapi()
        sub = abstractapi()

    a = field(float, record=False)  # <- don't record
    b = field(float, record=False)  # <- don't record
    result = field(float, record=False)

    @set_design(location=Menu)
    def add(self, a: Annotated[float, {"bind": a}], b: Annotated[float, {"bind": b}]):
        """Add two values"""
        self.result.value = a + b

    @set_design(location=Menu)
    def sub(self, a: Annotated[float, {"bind": a}], b: Annotated[float, {"bind": b}]):
        """Subtract two values"""
        self.result.value = a - b
```

Widget created by this code works completely identical to the previous one. Also, macro
will be recorded in a better way.

``` python title="macro"
ui.add(a=4.0, b=2.0)
ui.sub(a=6.0, b=3.0)
```
