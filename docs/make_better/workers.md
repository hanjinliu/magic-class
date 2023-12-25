# Multi-threading

Multi-threading is an important idea in GUI development. If you want to implement
background execution or progress bar, you'll usually have to rely on multi-threading.

`thread_worker` makes multi-threaded implementation much easier, without rewriting the
existing single-threaded code. It is available in:

``` python
from magicclass.utils import thread_worker
```

!!! note

    It is named after the `thread_worker` function originally defined in `superqt` and `napari`, which create a new function that will return a "worker" of the original
    function.

    ``` python
    from napari.utils import thread_worker

    @thread_worker
    def func():
        # do something

    worker = func()  # worker is ready to run the original "func"
    worker.start()  # the original "func" actually get called
    ```

    On the other hand, `magic-class`'s `thread_worker` is a class. It returns a
    `thread_worker` object instead of a new function. A `thread_worker` object will
    create a function that will start a worker every time it is accessed via
    `self.func`. Although they are designed differently, they share very similar API.

## Basic Usage

Decorate the methods you want to be multi-threaded and that's it!

``` python
import time
from magicclass import magicclass
from magicclass.utils import thread_worker

@magicclass
class Main:
    @thread_worker
    def func(self):
        for i in range(10):
            time.sleep(0.2)  # time consuming function
            print(i)

ui = Main()
ui.show()
```

![](../_images/workers-0.png)

During execution of `func`, the GUI window will not get frozen because
function is running in another thread.

!!! note

    If you are running functions programatically, GUI window will be disabled as usual.
    This is because the `run` method of `QRunnable` is called in the main thread,
    otherwise the second line of code will be executed *before* the first line of code
    actually finishes.

    ``` python
    @magicclass
    class Main:
        @thread_worker
        def f0(self):
            ...
        @thread_worker
        def f1(self):
            ...

    ui = Main()
    ui.f0()
    ui.f1()  # this function will be called before f0 finishes
    ```

    This behavior is important to keep manual and programatical execution
    consistent.

If decorated method is a generator, worker will iterate over it until it ends. In the
following example:

``` python
import time
from magicclass import magicclass
from magicclass.utils import thread_worker

@magicclass
class Main:
    @thread_worker
    def func(self):
        for i in range(3):
            print(i)
            yield i

ui = Main()
ui.show()
```

after you click the "func" button you'll get output like this.

``` title="Output"
0
1
2
```

## Connect Callbacks

If you update widgets in a `thread_worker`, GUI crashes.

``` python
import time
from magicclass import magicclass, vfield
from magicclass.utils import thread_worker

@magicclass
class Main:
    yielded_value = vfield(str)
    returned_value = vfield(str)

    @thread_worker
    def func(self, n: int = 10):
        for i in range(n):
            self.yielded_value = str(i)
            time.sleep(0.3)
        self.returned_value = "finished"  # updates the widget

ui = Main()
ui.show()
```

This is because updating widgets must be done in the main thread but `thread_worker` is
executed in a separate thread.

Just like `superqt` and `napari`, you can connect callback functions to `thread_worker`
objects. These callback functions are called in the main thread so that you can update
widgets safely.

There are six types of callbacks.

- `started` ... called when worker started.
- `returned` ... called when worker returned some values.
- `errored` ... called when worker raised an error.
- `yielded` ... called when worker yielded values.
- `finished` ... called when worker finished.
- `aborted` ... called when worker was aborted by some reasons.

Following example shows how you can update widget every 0.3 second.

``` python
import time
from magicclass import magicclass, vfield
from magicclass.utils import thread_worker

@magicclass
class Main:
    yielded_value = vfield(str)
    returned_value = vfield(str)

    @thread_worker
    def func(self, n: int = 10):
        for i in range(n):
            yield str(i)
            time.sleep(0.3)
        return "finished"

    @func.yielded.connect
    def _on_yield(self, value):
        self.yielded_value = value

    @func.returned.connect
    def _on_return(self, value):
        self.returned_value = value

ui = Main()
ui.show()
```

## Better Way to Define Callbacks

The `returned` callbacks and the `yielded` callbacks are very useful for letting users
know the progress and results of the function. However, a problem occurs when you send a
lot of information to the callback funcition.

``` python
import time
from magicclass import magicclass, vfield
from magicclass.utils import thread_worker

@magicclass
class Main:
    result_1 = vfield(str)
    result_2 = vfield(str)
    result_3 = vfield(str)

    @thread_worker
    def func(self, a: int, b: int):
        r1 = very_heavy_computation_1(a, b)
        r2 = very_heavy_computation_2(a, b)
        r3 = very_heavy_computation_3(a, b)
        return r1, r2, r2

    @func.returned.connect
    def _on_return(self, value):
        r1, r2, r3 = value  # hmmm...
        self.result_1 = r1
        self.result_2 = r2
        self.result_3 = r3

ui = Main()
ui.show()
```

You'll have to return all the values required for updating the widgets. In terms of
readability, this code is awful. You also have to annotate the second argument of
`_on_return` with a very long `tuple[...]` type.

Here, you can use `thread_worker.callback` static method. This method converts a function into a `Callback` object, which will be called if a thread worker detected it
as a returned/yielded value.

``` python
import time
from magicclass import magicclass, vfield
from magicclass.utils import thread_worker

@magicclass
class Main:
    result_1 = vfield(str)
    result_2 = vfield(str)
    result_3 = vfield(str)

    @thread_worker
    def func(self, a: int, b: int):
        r1 = very_heavy_computation_1(a, b)
        r2 = very_heavy_computation_2(a, b)
        r3 = very_heavy_computation_3(a, b)

        # write things in a function
        @thread_worker.callback
        def _return_callback():
            self.result_1 = r1
            self.result_2 = r2
            self.result_3 = r3
        return _return_callback

    @thread_worker
    def gen(self):
        @thread_worker.callback
        def _yield_callback():
            # r1, r2, r3 are non-local variables
            self.result_1 = r1
            self.result_2 = r2
            self.result_3 = r3
        for a in range(5):
            r1 = very_heavy_computation_1(a, 0)
            r2 = very_heavy_computation_2(a, 0)
            r3 = very_heavy_computation_3(a, 0)
            yield _yield_callback

ui = Main()
ui.show()
```

## Use Progress Bar

### How to use it?

Just like `napari`, you can use the embeded progress bar to display the
progress of the current function call using `progress=...` argument.
Same options are available in `magic-class` but you can choose which
progress bar to use.

1. If the main window does not have `magicgui.widgets.ProgressBar` widget, a popup
   progress bar widget will be created.

    ``` python
    @magicclass
    class Main:
        @thread_worker(progress={"total": 10})
        def func(self):
        for i in range(10):
            time.sleep(0.1)
    ```

2. If the main window has at least one `magicgui.widgets.ProgressBar` widget, the first
   one will be used.

    ``` python
    @magicclass
    class Main:
        pbar = field(ProgressBar)
        @thread_worker(progress={"total": 10})
        def func(self):
        for i in range(10):
            time.sleep(0.1)
    ```

3. If "pbar" option is given, progress bar specified by this option will be used.

    ``` python
    @magicclass
    class Main:
        pbar1 = field(ProgressBar)
        pbar2 = field(ProgressBar)

        @thread_worker(progress={"total": 10, "pbar": pbar1})
        def func(self):
            for i in range(10):
                time.sleep(0.1)
    ```

### How to set proper total iteration numbers?

I most cases, iteration numbers vary between function calls depending on the widget
states. In `magic-class`, you can pass a function or an evaluable literal string to the
"total" argument.

``` python
@magicclass
class Main:
    # Use a getter function.

    def _get_total(self):
        return 10

    @thread_worker(progress={"total": _get_total})
    def func0(self):
        n_iter = self._get_total()
        for i in range(n_iter):
            time.sleep(0.1)
            yield

    # Use a literal. Only the function arguments are available in the namespace.

    @thread_worker(progress={"total": "n_iter"})
    def func1(self, n_iter: int = 10):
        for i in range(n_iter):
            time.sleep(0.1)
            yield

    # Use a literal. Any evaluable literal can be used.

    @thread_worker(progress={"total": "width * height"})
    def func2(self, width: int = 3, height: int = 4):
        for w in range(width):
            for h in range(height):
                print(w * h, end=", ")
                time.sleep(0.1)
                yield
            print()

    # Use a literal. Of course, "self" is the most powerful way.

    n = field(int)

    @thread_worker(progress={"total": "self.n.value"})
    def func3(self):
        for i in range(self.n.value):
            time.sleep(0.1)
            yield
```

### Better way to pass progress bar parameters

Parameteres for the progress bar should be passed as a dictionary. This is not good for
many reasons such as readability and type hinting. You can use `with_progress` method
for the progress bar configuration.

``` python
@magicclass
class Main:
    # instead of `@thread_worker(progress={"total": 10})`
    @thread_worker.with_progress(total=10)
    def func(self):
    for i in range(10):
        time.sleep(0.1)
```

## Nesting `thread_worker`

To reuse thread worker functions, you would want to nest them. However,
this should be done carefully. If the nested thread worker updates the
widget, the outer thread worker crashes the GUI.

``` python
@magicclass
class Main:
    @thread_worker
    def outside(self):
        self.inside()  # This line will crash the GUI, even though
        # the function that update the widget is in the callback of
        # `self.inside`.
        # When a thread worker is called programatically, the function
        # body and the callbacks are all called in the main thread.
        # This means that even `self.function_that_update_widget` is
        # called inside this method.

    @thread_worker
    def inside(self):
        self.very_heavy_computation()
        return thread_worker.callback(self.function_that_update_widget)
```

### A naive solution

One way to avoid this is to use `thread_worker.callback`.

``` python
@magicclass
class Main:
    @thread_worker
    def outside(self):
        # self.inside() will be called as as callback so it won't crash the GUI
        return thread_worker.callback(self.inside)

    @thread_worker
    def inside(self):
        self.very_heavy_computation()
        return thread_worker.callback(self.function_that_update_widget)
```

### Better but advanced solution

Methods decorated with `thread_worker` have a `arun` attribute, which will run the
function in a non-blocking way (asynchronously). More precisely, `arun` will return a
generator that convert all the yielded and returned value into yielded values. This
means that you can use `yield from` to send all the callbacks of the nested thread
worker to the outer thread worker.

``` python
@magicclass
class Main:
    @thread_worker
    def outside(self):
        # `arun` takes the same arguments as the original function.
        yield from self.inside.arun(1)

    @thread_worker
    def inside(self, i: int):
        self.function_that_update_widget()
```

## Asynchronous ValueWidget Callbacks

!!! warning

    This feature is experimental. It may not work in some cases.

[Fields](../basics/fields.md) are equipped with `connect` method to connect callbacks to
them.

``` python
@magicclass
class Main:
    x = field(int)

    @x.connect
    def _x_changed(self, value):
        print(value)  # print the new value every time it changes
```

Then, what if the callback function is computationally expensive? The GUI will freeze
during the execution, which makes user experience very bad. This problem is prominent
when you want to implement functions like below.

- Image sweeping ... images are large collections of data. Updating the image while
  moving a slider widget will be very slow.
- Data fetching ... Fetching data from the internet is slower compared to updating
  widgets locally.

`connect_async` is a method that connects a callback function as a `thread_worker`
with proper configurations. All the rules follows the standard `thread_worker` method.

``` python
@magicclass
class Main:
    x = field(int)
    display = field(str)

    @x.connect_async
    def _x_changed(self, value):
        # If you want to update the widget, you have to use yield/return
        # callbacks.
        yield f"updating ..."
        time.sleep(1)
        return f"changed to {value}"

    @_x_changed.yielded.connect
    @_x_changed.returned.connect
    def _update(self, text: str):
        self.display.value = text
```

To avoid running widget callback functions multiple times, you can pass `timeout`
argument to `connect_async`. If the previous run is still ongoing, it will be aborted if
the new run is started within the timeout period. `timeout=0` means that the previous
run will never be aborted, and `timeout=float("inf")` means that the previous run will
be always aborted if not finished.

``` python
@magicclass
class Main:
    ...

    @x.connect_async(timeout=0.1)
    def _x_changed(self, value):
        ...
```
