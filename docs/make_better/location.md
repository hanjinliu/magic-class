# Call Parent Methods from its Child

When you want to define a function under the parent class while put its push button or
action in the child widget for better widget design, code will look very complicated and
will be hard to maintain. This problem usually happens when you want a menu bar, since
menu actions always execute something using the parameters of the parent and often
update its parent.

You can use the `location=...` argument of `@set_design` decorator to put buttons in
other locations.

## Basic Syntax

You have to do is:

1. Define child class
2. Define parent method
3. Define a child method with the same name as that of parent's (not necessary but
   recommended)
4. Call `@set_design(location=ParentClass)`

Following example shows how to call `set_param` and `print_param` functions from its
child class `Child`.

``` python
from magicclass import magicclass, field, set_design

@magicclass
class Parent:
    param = 0.1

    @magicclass(layout="horizontal")
    class Child:
        # A frame of buttons
        def set_param(self): ...
        def print_param(self): ...

    # a result widget
    result = field(widget_type="LineEdit", options={"enabled": False})

    @set_design(location=Child)
    def set_param(self, value: float):
        self.param = value

    @set_design(location=Child)
    def print_param(self):
        self.result.value = self.param

ui = Parent()
ui.show()
```

![](../_images/location-0.png)

The `Parent` methods will not appear in the parent widget because they already exist in
the child widget.

??? info "why pre-definition?"

    Method pre-definition in Step 3. is not a must. It is recommended, however, in
    several reasons:

    1. It plays as an "index" of functions. One can know what functions are implemented
       in the GUI, and in what order they will appear in widgets.
    2. If the widget is composed of nested magic classes and other widgets or fields,
       the order of widgets will not be sorted due to different timing of widget
       creation.

## Use `@abstractapi` decorator

Method pre-definition cannot be statically checked by IDEs; if you mistakenly re-defined
a method with misspelled name, or you forgot to re-define a method, the GUI will have an
button that does nothing with no warning nor error.

``` python
@magicclass
class Parent:
    @magicclass
    class Child:
        def run_fucntion(self): ...  # <------ misspelled!!

    @set_design(location=Child)
    def run_function(self, value: float):
        """Do something"""

ui = Parent()
ui.show()
```

To avoid this, you can use `abstractapi` class to define abstract methods. Abstract API
will be resolve only if the function is re-defined in the parent widget or overriden by
such as its subclass.

``` python
@magicclass
class Parent:
    @magicclass
    class Child:
        run_fucntion = abstractapi()  # <------ misspelled!!

    @set_design(location=Child)
    def run_function(self, value: float):
        """Do something"""

ui = Parent()  # AbstracAPIError will be raised here
```

`abstractapi` is not necessarily used as a decorator. It can be instantiated as if a
field object.

``` python
@magicclass
class Parent:
    @magicclass
    class Child:
        run_fucntion = abstractapi()  # <------ like this
```

## Find Ancestor Widgets

If your purpose is just to get the ancestor widget, you can use `find_ancestor` method
instead. `self.find_ancestor(X)` will iteratively search for the widget parent until it
reaches an instance of `X`.

``` python
@magicclass
class Main:
    @magicclass
    class A:
        def func(self):
            ancestor = self.find_ancestor(Main)
            # do something on the ancestor widget
```

In terms of calling parent methods, `find_ancestor` works very similar to what you do
with `@set_design(location=ParentClass)`. However, there are some cases where using
`find_ancestor` is better.

- You can define child widget class outside the parent widget class (even in a
  separate file).

    ``` python title="child.py"
    from magicclass import magicmenu

    @magicmenu
    class A:
        def func(self):
            ancestor = self.find_ancestor(Main)
            # do something on the ancestor widget
    ```

    ``` python title="main.py"
    from magicclass import magicclass
    from .child import A

    @magicclass
    class Main:
        A = A
    ```

- Recorded macro will be different. In the case of calling `find_ancestor`, macro will
  be recorded as `"ui.ChildClass.method(...)"` while it will be `"ui.method(...)"` if
  you used `@wraps`. In terms of readability, usually `@wraps` will be better.

!!! note
    If parent widget will not change, you can cache the parent widget by
    `self.find_ancestor(Main, cache=True)`. This is faster so is useful if
    the function will be repeatitively called.

## Field Locations

Same strategy can be used for [fields](../basics/fields.md).

``` python
from magicclass import magicclass, field, abstractapi

@magicclass
class A:
    @magicclass(layout="horizontal")
    class Parameters:
        a = abstractapi()
        b = abstractapi()

    a = field(int, location=Parameters)
    b = field(int, location=Parameters)
    def add(self):
        print(self.a.value + self.b.value)

ui = A()
ui.show()
```

![](../_images/location-1.png)
