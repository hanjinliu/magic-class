# Set Custom Icons

An icon often tells more than a text. Using them in your GUI will be a good idea
especially in a tool bar.

Basically you'll set icons with the `icon` keyword argument of `@set_design` decorator.
There are several ways to do that in `magic-class`.

## Image File as an Icon

If you have your icon file in such as .jpg or .svg format, you can use the path.

``` python
from magicclass import magicclass, magictoolbar, set_design

icon_path = "path/to/icon.png"

@magicclass
class A:
    @magictoolbar
    class toolbar:
        @set_design(icon=icon_path)
        def func(self):
            ...
```

## Array as an Icon

You may want to apply some transformation to an icon image. In this case, an array-like
object can be used.

``` python
from magicclass import magicclass, magictoolbar, set_design
from skimage import io

img = io.imread("path/to/image.png")  # read image as a np.ndarray
icon = -img  # invert image

@magicclass
class A:
    @magictoolbar
    class toolbar:
        @set_design(icon=icon)
        def func(self):
            ...
```

## Iconify icons

As `magicgui` also supports it, you can use `iconify` to convert a string to an icon.

- [pyconify](https://github.com/pyapp-kit/pyconify)
- [iconify](https://github.com/iconify/iconify)

``` python
from magicclass import magicclass, magictoolbar, set_design

@magicclass
class A:
    @magictoolbar
    class toolbar:
        @set_design(icon="mdi:bell")  # <-- string to icon
        def func(self):
            ...
```
