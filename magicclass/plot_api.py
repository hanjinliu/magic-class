"""
Provide a matplotlib-like interface to plot data in a Qt widget.
Import this submodule

>>> import magicclass.plot_api as plt

and it's ready to use like matplotlib.

>>> plt.plot(...)
>>> plt.title(...)
>>> plt.show()

"""

from __future__ import annotations

from functools import wraps
import matplotlib.pyplot as plt
from .widgets import Figure

CURRENT_WIDGET: Figure = None


@wraps(plt.figure)
def figure(*args, **kwargs):
    global CURRENT_WIDGET
    CURRENT_WIDGET = Figure()
    return CURRENT_WIDGET.figure


@wraps(plt.subplot)
def subplot(*args):
    return figure().subplot(*args)


@wraps(plt.subplots)
def subplots(
    nrows=1,
    ncols=1,
    *,
    sharex=False,
    sharey=False,
    squeeze=True,
    subplot_kw=None,
    gridspec_kw=None,
    **fig_kw,
):
    fig = figure(**fig_kw)
    fig.clf()
    axs = fig.subplots(
        nrows=nrows,
        ncols=ncols,
        sharex=sharex,
        sharey=sharey,
        squeeze=squeeze,
        subplot_kw=subplot_kw,
        gridspec_kw=gridspec_kw,
    )
    return fig, axs


@wraps(plt.gcf)
def gcf():
    """Get current figure."""
    return CURRENT_WIDGET.figure


@wraps(plt.gca)
def gca():
    """Get current axis."""
    return CURRENT_WIDGET.axes[-1]


def gcw() -> Figure:
    """Get current widget."""
    global CURRENT_WIDGET
    if CURRENT_WIDGET is None:
        CURRENT_WIDGET = Figure()
    return CURRENT_WIDGET


@wraps(plt.cla)
def cla():
    return gcw().cla()


@wraps(plt.plot)
def plot(*args, **kwargs):
    return gcw().plot(*args, **kwargs)


@wraps(plt.scatter)
def scatter(*args, **kwargs):
    return gcw().scatter(*args, **kwargs)


@wraps(plt.hist)
def hist(*args, **kwargs):
    return gcw().hist(*args, **kwargs)


@wraps(plt.bar)
def bar(*args, **kwargs):
    return gcw().bar(*args, **kwargs)


@wraps(plt.imshow)
def imshow(*args, **kwargs):
    return gcw().imshow(*args, **kwargs)


def show():
    """Show current figure widget."""
    return gcw().show()


def close():
    """Close current figure widget"""
    return gcw().close()


@wraps(plt.quiver)
def quiver(*args, **kwargs):
    return gcw().quiver(*args, **kwargs)


@wraps(plt.text)
def text(*args, **kwargs):
    return gcw().text(*args, **kwargs)


@wraps(plt.axhline)
def axhline(*args, **kwargs):
    return gcw().axhline(*args, **kwargs)


@wraps(plt.axvline)
def axvline(*args, **kwargs):
    return gcw().axvline(*args, **kwargs)


@wraps(plt.axline)
def axline(*args, **kwargs):
    return gcw().axline(*args, **kwargs)


@wraps(plt.xlim)
def xlim(*args, **kwargs):
    return gcw().xlim(*args, **kwargs)


@wraps(plt.ylim)
def ylim(*args, **kwargs):
    return gcw().ylim(*args, **kwargs)


@wraps(plt.title)
def title(*args, **kwargs):
    return gcw().title(*args, **kwargs)


@wraps(plt.xlabel)
def xlabel(*args, **kwargs):
    return gcw().xlabel(*args, **kwargs)


@wraps(plt.ylabel)
def ylabel(*args, **kwargs):
    return gcw().ylabel(*args, **kwargs)


@wraps(plt.xticks)
def xticks(*args, **kwargs):
    return gcw().xticks(*args, **kwargs)


@wraps(plt.yticks)
def yticks(*args, **kwargs):
    return gcw().yticks(*args, **kwargs)


@wraps(plt.legend)
def legend(*args, **kwargs):
    return gcw().legend(*args, **kwargs)


@wraps(plt.twinx)
def twinx(*args, **kwargs):
    return gcw().twinx(*args, **kwargs)


@wraps(plt.twiny)
def twiny(*args, **kwargs):
    return gcw().twiny(*args, **kwargs)


@wraps(plt.box)
def box(*args, **kwargs):
    return gcw().box(*args, **kwargs)


@wraps(plt.xscale)
def xscale(*args, **kwargs):
    return gcw().xscale(*args, **kwargs)


@wraps(plt.yscale)
def yscale(*args, **kwargs):
    return gcw().yscale(*args, **kwargs)


@wraps(plt.autoscale)
def autoscale(*args, **kwargs):
    return gcw().autoscale(*args, **kwargs)


@wraps(plt.grid)
def grid(*args, **kwargs):
    return gcw().grid(*args, **kwargs)


def draw():
    """Draw current figure widget."""
    return gcw().draw()
