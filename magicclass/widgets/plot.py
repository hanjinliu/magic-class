from __future__ import annotations
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Callable,
    TypeVar,
    overload,
)
from typing_extensions import ParamSpec

from .utils import FreeWidget

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    from matplotlib.axes import Axes
    from matplotlib.lines import Line2D
    from matplotlib.collections import PathCollection
    from matplotlib.text import Text
    from matplotlib.quiver import Quiver
    from matplotlib.legend import Legend
    from numpy.typing import ArrayLike

    _P = ParamSpec("_P")
    _R = TypeVar("_R")

    def _inject_mpl_docs(f: Callable[_P, _R]) -> Callable[_P, _R]:
        plt_func = getattr(plt, f.__name__)
        plt_doc = getattr(plt_func, "__doc__", "")
        if plt_doc:
            f.__doc__ = (
                f"Copy of ``plt.{f.__name__}()``. Original docstring "
                f"is ...\n\n{plt_doc}"
            )
        return f

    import seaborn as sns
    from seaborn.axisgrid import Grid

    def _inject_sns_docs(f: Callable[_P, _R]) -> Callable[_P, _R]:
        sns_func = getattr(sns, f.__name__)
        sns_doc = getattr(sns_func, "__doc__", "")
        if sns_doc:
            f.__doc__ = (
                f"Copy of ``sns.{f.__name__}()``. Original docstring "
                f"is ...\n\n{sns_doc}"
            )
        return f

else:

    def _inject_mpl_docs(f: Callable[_P, _R]) -> Callable[_P, _R]:
        return f

    def _inject_sns_docs(f: Callable[_P, _R]) -> Callable[_P, _R]:
        return f


class Figure(FreeWidget):
    """A matplotlib figure canvas."""

    _docstring_initialized = False

    @overload
    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] = (4.0, 3.0),
        style=None,
        **kwargs,
    ):
        ...

    @overload
    def __init__(
        self,
        fig: Figure,
        **kwargs,
    ):
        ...

    def __init__(
        self,
        nrows=1,
        ncols=1,
        figsize=(4.0, 3.0),
        style=None,
        **kwargs,
    ):

        if isinstance(nrows, int):
            import matplotlib as mpl
            import matplotlib.pyplot as plt

            backend = mpl.get_backend()
            try:
                mpl.use("Agg")
                if style is None:
                    fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
                else:
                    with plt.style.context(style):
                        fig, _ = plt.subplots(nrows, ncols, figsize=figsize)
            finally:
                mpl.use(backend)
        else:
            fig = nrows

        from ._mpl_canvas import InteractiveFigureCanvas

        canvas = InteractiveFigureCanvas(fig)
        self.canvas = canvas
        super().__init__(**kwargs)
        self.set_widget(canvas)
        self.figure = fig
        self.min_height = 40
        self.min_width = 40
        self._inject_docs()

    def _reset_canvas(self, fig: Figure, draw: bool = True):
        """Create an interactive figure canvas and add it to the widget."""
        from ._mpl_canvas import InteractiveFigureCanvas

        canvas = InteractiveFigureCanvas(fig)
        if self.central_widget is not None:
            self.remove_widget(self.canvas)
        self.canvas = canvas
        self.set_widget(canvas)
        if draw:
            self.draw()

    def _inject_docs(self):
        if Figure._docstring_initialized:
            return

        import matplotlib.pyplot as plt

        for k, f in Figure.__dict__.items():
            if k.startswith("_") or isinstance(f, property):
                continue
            plt_func = getattr(plt, k, None)
            if plt_func is None:
                continue
            plt_doc = getattr(plt_func, "__doc__", "")
            if plt_doc:
                f.__doc__ = (
                    f"Copy of ``plt.{k}()``. Original docstring " f"is ...\n\n{plt_doc}"
                )

        Figure._docstring_initialized = True

    @_inject_mpl_docs
    def draw(self):
        self.figure.tight_layout()
        self.canvas.draw()

    @property
    def enabled(self) -> bool:
        """toggle interactivity of the figure canvas."""
        return self.canvas._interactive

    @enabled.setter
    def enabled(self, v: bool):
        self.canvas._interactive = bool(v)

    @property
    def mouse_click_callbacks(self) -> list[Callable]:
        return self.canvas._mouse_click_callbacks

    interactive = enabled  # alias

    @_inject_mpl_docs
    def clf(self) -> None:
        self.figure.clf()
        self.draw()

    @_inject_mpl_docs
    def cla(self) -> None:
        self.ax.cla()
        self.draw()

    @property
    def axes(self) -> list[Axes]:
        """List of matplotlib axes."""
        return self.figure.axes

    @property
    def ax(self) -> Axes:
        """The first matplotlib axis."""
        try:
            _ax = self.axes[0]
        except IndexError:
            _ax = self.figure.add_subplot(111)
        return _ax

    @_inject_mpl_docs
    def subplots(
        self, *args, **kwargs
    ) -> tuple[Figure, Axes] | tuple[Figure, list[Axes]]:
        self.clf()
        fig = self.figure
        axs = fig.subplots(*args, **kwargs)
        self.draw()
        return fig, axs

    @_inject_mpl_docs
    def savefig(self, *args, **kwargs) -> None:
        return self.figure.savefig(*args, **kwargs)

    @_inject_mpl_docs
    def plot(self, *args, **kwargs) -> list[Line2D]:
        lines = self.ax.plot(*args, **kwargs)
        self.draw()
        return lines

    @_inject_mpl_docs
    def scatter(self, *args, **kwargs) -> PathCollection:
        paths = self.ax.scatter(*args, **kwargs)
        self.draw()
        return paths

    @_inject_mpl_docs
    def hist(
        self, *args, **kwargs
    ) -> tuple[ArrayLike | list[ArrayLike], ArrayLike, list | list[list]]:
        out = self.ax.hist(*args, **kwargs)
        self.draw()
        return out

    @_inject_mpl_docs
    def text(self, *args, **kwargs) -> Text:
        text = self.ax.text(*args, **kwargs)
        self.draw()
        return text

    @_inject_mpl_docs
    def quiver(self, *args, data=None, **kwargs) -> Quiver:
        quiver = self.ax.quiver(*args, data=data, **kwargs)
        self.draw()
        return quiver

    @_inject_mpl_docs
    def axline(self, xy1, xy2=None, *, slope=None, **kwargs) -> Line2D:
        lines = self.ax.axline(xy1, xy2=xy2, slope=slope, **kwargs)
        self.draw()
        return lines

    @_inject_mpl_docs
    def axhline(self, y=0, xmin=0, xmax=1, **kwargs) -> Line2D:
        lines = self.ax.axhline(y, xmin, xmax, **kwargs)
        self.draw()
        return lines

    @_inject_mpl_docs
    def axvline(self, x=0, ymin=0, ymax=1, **kwargs) -> Line2D:
        lines = self.ax.axvline(x, ymin, ymax, **kwargs)
        self.draw()
        return lines

    @_inject_mpl_docs
    def xlim(self, *args, **kwargs) -> tuple[float, float]:
        ax = self.ax
        if not args and not kwargs:
            return ax.get_xlim()
        ret = ax.set_xlim(*args, **kwargs)
        self.draw()
        return ret

    @_inject_mpl_docs
    def ylim(self, *args, **kwargs) -> tuple[float, float]:
        ax = self.ax
        if not args and not kwargs:
            return ax.get_ylim()
        ret = ax.set_ylim(*args, **kwargs)
        self.draw()
        return ret

    @_inject_mpl_docs
    def imshow(self, *args, **kwargs) -> Axes:
        self.ax.imshow(*args, **kwargs)
        self.draw()
        return self.ax

    @_inject_mpl_docs
    def legend(self, *args, **kwargs) -> Legend:
        leg = self.ax.legend(*args, **kwargs)
        self.draw()
        return leg

    @_inject_mpl_docs
    def title(self, *args, **kwargs) -> Text:
        title = self.ax.set_title(*args, **kwargs)
        self.draw()
        return title

    @_inject_mpl_docs
    def xlabel(self, *args, **kwargs) -> None:
        self.ax.set_xlabel(*args, **kwargs)
        self.draw()
        return None

    @_inject_mpl_docs
    def ylabel(self, *args, **kwargs) -> None:
        self.ax.set_ylabel(*args, **kwargs)
        self.draw()
        return None

    @_inject_mpl_docs
    def xticks(self, ticks=None, labels=None, **kwargs) -> tuple[ArrayLike, list[Text]]:
        if ticks is None:
            locs = self.ax.get_xticks()
            if labels is not None:
                raise TypeError(
                    "xticks(): Parameter 'labels' can't be set "
                    "without setting 'ticks'"
                )
        else:
            locs = self.ax.set_xticks(ticks)

        if labels is None:
            labels = self.ax.get_xticklabels()
        else:
            labels = self.ax.set_xticklabels(labels, **kwargs)
        for l in labels:
            l.update(kwargs)
        self.draw()
        return locs, labels

    @_inject_mpl_docs
    def yticks(self, ticks=None, labels=None, **kwargs) -> tuple[ArrayLike, list[Text]]:
        if ticks is None:
            locs = self.ax.get_yticks()
            if labels is not None:
                raise TypeError(
                    "xticks(): Parameter 'labels' can't be set "
                    "without setting 'ticks'"
                )
        else:
            locs = self.ax.set_yticks(ticks)

        if labels is None:
            labels = self.ax.get_yticklabels()
        else:
            labels = self.ax.set_yticklabels(labels, **kwargs)
        for l in labels:
            l.update(kwargs)
        self.draw()
        return locs, labels

    @_inject_mpl_docs
    def twinx(self) -> Axes:
        return self.ax.twinx()

    @_inject_mpl_docs
    def twiny(self) -> Axes:
        return self.ax.twiny()

    @_inject_mpl_docs
    def box(self, on=None) -> None:
        if on is None:
            on = not self.ax.get_frame_on()
        self.ax.set_frame_on(on)
        return None

    @_inject_mpl_docs
    def xscale(self, scale=None) -> None:
        self.ax.set_xscale(scale)
        self.draw()
        return None

    @_inject_mpl_docs
    def yscale(self, scale=None) -> None:
        self.ax.set_yscale(scale)
        self.draw()
        return None

    @_inject_mpl_docs
    def autoscale(self, enable=True, axis="both", tight=None) -> None:
        self.ax.autoscale(enable=enable, axis=axis, tight=tight)
        self.draw()
        return None


def _use_seaborn_grid(f):
    """
    Some seaborn plot functions will create a new figure.
    This decorator provides a common way to update figure canvas in the widget.
    """

    @wraps(f)
    def func(self: SeabornFigure, *args, **kwargs):
        import matplotlib as mpl

        backend = mpl.get_backend()
        try:
            mpl.use("Agg")
            grid: Grid = f(self, *args, **kwargs)
        finally:
            mpl.use(backend)

        self._reset_canvas(grid.figure)
        return grid

    return func


class SeabornFigure(Figure):
    """
    A matplotlib figure canvas implemented with seaborn plot functions.

    Not all the seaborn plot functions are supported since some of them are
    figure-level functions and incompatible with specifying axes.
    """

    _docstring_initialized = False

    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] = (4.0, 3.0),
        style=None,
        **kwargs,
    ):
        super().__init__(
            nrows=nrows, ncols=ncols, figsize=figsize, style=style, **kwargs
        )
        import seaborn as sns

        self._seaborn = sns

    def _inject_docs(self):
        super()._inject_docs()

        if SeabornFigure._docstring_initialized:
            return

        import seaborn as sns

        for k, f in SeabornFigure.__dict__.items():
            if k.startswith("_") or isinstance(f, property):
                continue
            sns_func = getattr(sns, k, None)
            if sns_func is None:
                continue
            sns_doc = getattr(sns_func, "__doc__", "")
            if sns_doc:
                f.__doc__ = (
                    f"Copy of ``sns.{k}()``. Original docstring " f"is ...\n\n{sns_doc}"
                )

        SeabornFigure._docstring_initialized = True

    @_inject_sns_docs
    def swarmplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.swarmplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def barplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.barplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def boxplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.boxplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def boxenplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.boxenplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def violinplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.violinplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def pointplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.pointplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def histplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.histplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def kdeplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.kdeplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def rugplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.rugplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    def regplot(self, *args, **kwargs) -> Axes:
        out = self._seaborn.regplot(ax=self.ax, *args, **kwargs)
        self.draw()
        return out

    @_inject_sns_docs
    @_use_seaborn_grid
    def jointplot(self, *args, **kwargs) -> sns.JointGrid:
        return self._seaborn.jointplot(*args, **kwargs)

    @_inject_sns_docs
    @_use_seaborn_grid
    def lmplot(self, *args, **kwargs) -> sns.FacetGrid:
        return self._seaborn.lmplot(*args, **kwargs)

    @_inject_sns_docs
    @_use_seaborn_grid
    def pairplot(self, *args, **kwargs) -> sns.PairGrid:
        return self._seaborn.pairplot(*args, **kwargs)
