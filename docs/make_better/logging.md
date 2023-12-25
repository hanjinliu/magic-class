---
title: Logging in magic-class
---

# Logger Widget

It is important to keep a log if your GUI is complicated. In data
science, it is also helpful to show the results with rich text, tables,
and figures.

In `magicclass`, you can use the logger widget to show the rich messages.

``` python
from magicclass.widgets import Logger

log = Logger()  # create a logger widget.
log.show()  # show the logger widget.
```

## Print texts

There are several ways to show text messages.

``` python
from magicclass.widgets import Logger

log = Logger()  # create a logger widget.

log.print("message")  # print the message.
log.print_html("<b>bold</b><i>italic</i> <code>code</code>")  # print the message with HTML.
log.print_rst("**bold** *italic* ``code``")  # print the message with reStructuredText.
log
```

![](../_images/logging-0.png)

If you want to use the built-in `print` function but show the message in the logger
widget, you can use the `set_stdout` context manager.

``` python
with log.set_stdout():
    print("message")  # print the message.
```

`set_logger` context manager works similarly.

``` python
import logging

with log.set_logger():
    logging.info("message")
```

## Print images

You can show 2D arrays as images with `print_image` method.

``` python
log.print_image(np.random.rand(100, 100))  # show the image.
```

## Print tables

Any `pandas.DataFrame`-like objects can be shown as a table with `print_table` method.

``` python
log = Logger()
log.print_table({"a": [1, 2, 3], "b": [True, False, False]})
log.print_table([[0, 1], [2, 3]])
log
```

![](../_images/logging-1.png)

## Plotting

The `set_plt` context manager can be used to show the `matplotlib` plots in the logger
widget.

``` python
import matplotlib.pyplot as plt

log = Logger()

with log.set_plt():
    plt.plot([1, 2, 3], [4, 5, 6])
    plt.show()
log
```

![](../_images/logging-2.png)

# Use `logging` Submodule

`magicclass` provides a submodule `logging` to use the logger widget easily. Most of
the methods are the same as the standard `logging` module.

``` python
from magicclass import logging

logger = logging.getLogger("your-app-name")
logger.widget.show()  # show the logger widget.

logger.print("message")  # print the message.
with logger.set_plt():
    plt.plot([1, 2, 3], [4, 5, 6])  # plot
```
