from __future__ import annotations
from functools import partial, wraps
import time
import threading
from typing import Callable, Iterable, TypeVar
from .utils import FreeWidget
from ..utils import get_signature

from magicgui.widgets import Label, ProgressBar

T = TypeVar("T")

# BUG: function wrapped by @progress does not show the contents of progress bar after the second run.
# TODO: generator functions

class ProgressWidget(FreeWidget):
    def __init__(self, text: str = None, visible: bool = False):
        if text is None:
            text = "Running ..."
        self._description = Label(value=text)
        self._pbar = ProgressBar()
        super().__init__(visible=visible)
        self.set_widget(self._description.native)
        self.set_widget(self._pbar.native)
    
    def __call__(self, iterable: Iterable[T]) -> Iterable[T]:
        if hasattr(iterable, "__len__"):
            dt = self._pbar.max/len(iterable)
        else:
            dt = 0
            
        with self.run() as p:
            for it in iterable:
                yield it
                p._pbar.increment(dt)
    
    def range(self, n: int):
        return self(range(n))
    
    def run(self) -> progress:
        """
        Build a context that progress bar will be displayed.

        Returns
        -------
        progress
            Context manager for progress bar.
        """        
        return progress(progress=self)
    
    def show_progress(self, f: Callable = None) -> Callable:
        return progress(f, progress=self)
            
    @property
    def text(self) -> str:
        return self._description.value
    
    @text.setter
    def text(self, value: str):
        self._description.value = value
    
    @property
    def value(self) -> int:
        return self._pbar.value
    
    @value.setter
    def value(self, v: int):
        self._pbar.value = min(v, self._pbar.max)

_progress_widget = ProgressWidget()

class progress:
    def __init__(self, obj: Callable = None, *, progress: ProgressWidget = None):
        if progress is None:
            progress = _progress_widget
        
        self.progress = progress
        self.thread = None
        self.running = False
        
        self.function = None
        if isinstance(obj, Callable):
            self.function = self._wrap_function(obj)
        
    
    @property
    def function(self):
        return self._function
    
    @function.setter
    def function(self, f: Callable):
        self._function = f
        if callable(f):
            self.__name__ = f.__name__
            self.__qualname__ = f.__qualname__
        
    @property
    def __signature__(self):
        return get_signature(self._function)
        
    def __call__(self, *args, **kwargs):
        if self.function is None:
            if len(args) != 1 or not callable(args[0]):
                raise TypeError("Cannot call progress before setting a function.")
            self.function = self._wrap_function(args[0])
            return self.function
        else:
            return self.function(*args, **kwargs)
    
    def __get__(self, obj, objtype=None):
        """
        This method enables wrapping class method.
        """        
        f = partial(self.function, obj)
        f.__name__ = self.function.__name__
        f.__qualname__ = self.function.__qualname__
        return self.__class__(f, progress=self.progress)
        
    def _wrap_function(self, function: Callable):
        @wraps(function)
        def _func(*args, **kwargs):
            with self:
                out = function(*args, **kwargs)
            return out
        return _func
    
    def _run(self):
        self.running = True
        while self.running:
            time.sleep(0.01)
        
        # Show 100%
        self.progress.value = self.progress._pbar.max
        time.sleep(0.1)
    
    def __enter__(self) -> ProgressWidget:
        self.pbar_was_visible = self.progress.visible
        self.progress.visible = True
        self.progress.value = 0
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
        return self.progress

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.running = False
        self.thread.join()
        
        self.progress._pbar.min = 0
        self.progress._pbar.max = 1000
        self.progress._pbar.value = 1000
        self.progress.visible = self.pbar_was_visible