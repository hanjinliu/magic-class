# Pre-run Confirmation

Sometimes you want to confirm the input before running the function, especially when
the function needs a long time to run or irreversibly changes the GUI state. The
process of confirmation is usually GUI specific, as you'll not want a window to pop up
when running the function from the script.

## `confirm` decorator

`magic-class` provides a decorator to add confirmation process to a function.

```python
from magicclass import magicclass, confirm

@magicclass
class A:
    @confirm(text="Are you sure to run this function?")
    def func(self):
        ...
```

When you click the button, a confirmation window will pop up before running the
function, but if you run the function from the script, the `@confirm` does nothing.

## Conditional Confirmation

You can pass a condition to `@confirm` decorator. The confirmation window will pop up
only when the condition is satisfied.

``` python
from magicclass import magicclass, confirm

@magicclass
class A:
    # use executable string as condition
    @confirm(condition="ratio < 0 or 1 < ratio", text="ratio out of range, continue?")
    def func(self, ratio: float):
        ...
```
