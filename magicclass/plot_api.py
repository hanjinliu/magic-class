from .widgets import Figure

CURRENT_WIDGET: Figure = None


def figure():
    global CURRENT_WIDGET
    CURRENT_WIDGET = Figure()
    return CURRENT_WIDGET.figure


def subplot(*args):
    return figure().subplot(*args)


def gcf():
    """Get current figure."""
    return CURRENT_WIDGET.figure


def gca():
    """Get current axis."""
    return CURRENT_WIDGET.axes[-1]


def gcw():
    """Get current widget."""
    global CURRENT_WIDGET
    if CURRENT_WIDGET is None:
        CURRENT_WIDGET = Figure()
    return CURRENT_WIDGET


def plot(*args, **kwargs):
    return gcw().plot(*args, **kwargs)


def scatter(*args, **kwargs):
    return gcw().scatter(*args, **kwargs)


def hist(*args, **kwargs):
    return gcw().hist(*args, **kwargs)


def imshow(*args, **kwargs):
    return gcw().imshow(*args, **kwargs)


def show():
    CURRENT_WIDGET.show()


def close():
    CURRENT_WIDGET.close()


def quiver(*args, **kwargs):
    return gcw().quiver(*args, **kwargs)


def text(*args, **kwargs):
    return gcw().text(*args, **kwargs)


def axhline(*args, **kwargs):
    return gcw().axhline(*args, **kwargs)


def axvline(*args, **kwargs):
    return gcw().axvline(*args, **kwargs)


def axline(*args, **kwargs):
    return gcw().axline(*args, **kwargs)


def xlim(*args, **kwargs):
    return gcw().xlim(*args, **kwargs)


def ylim(*args, **kwargs):
    return gcw().ylim(*args, **kwargs)


def title(*args, **kwargs):
    return gcw().title(*args, **kwargs)


def xlabel(*args, **kwargs):
    return gcw().xlabel(*args, **kwargs)


def ylabel(*args, **kwargs):
    return gcw().ylabel(*args, **kwargs)


def xticks(*args, **kwargs):
    return gcw().xticks(*args, **kwargs)


def yticks(*args, **kwargs):
    return gcw().yticks(*args, **kwargs)
