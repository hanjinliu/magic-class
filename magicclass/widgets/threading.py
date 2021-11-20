from __future__ import annotations
from functools import partial, wraps
import time
import threading
from typing import Callable, Iterable

from magicgui.widgets import Container, Label, ProgressBar


class ProgressWidget(Container):
    def __init__(self, text: str = None, visible: bool = False):
        if text is None:
            text = "Running ..."
        self._description = Label(value=text)
        self._pbar = ProgressBar()
        super().__init__(widgets=[self._description, self._pbar], 
                         labels=False, 
                         visible=visible)
    
    def __call__(self, iterable: Iterable):
        if hasattr(iterable, "__len__"):
            dt = self._pbar.max/len(iterable)
        else:
            dt = 0
            
        with self.run(infinite = dt==0) as p:
            for it in iterable:
                yield it
                if dt > 0:
                    p._pbar.increment(dt)
            if dt > 0:
                p._pbar.value = self._pbar.max
    
    def range(self, n: int):
        return self(range(n))
    
    def run(self, infinite: bool = True):
        return progress(infinite=infinite, progress=self)
    
    def show_progress(self, f: Callable = None):
        @wraps(f)
        def function_with_progressbar(*args, **kwargs):
            with self.run(infinite=True):
                out = f(*args, **kwargs)
            return out
        return function_with_progressbar
    
    def _as_infinite(self):
        self._pbar.value = 0
        self._pbar.min = 0
        self._pbar.max = 0
        
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

class progress:
    def __init__(self, function: Callable = None, *, infinite: bool = True, 
                 progress: ProgressWidget = None):
        if progress is None:
            progress = ProgressWidget()
            self.close_on_finish = True
        else:
            self.close_on_finish = False
        
        if function is not None:
            function = self._wrap_function(function)
        
        self.function = function
        self.progress = progress
        self.pbar_was_visible = progress.visible
        self.infinite = infinite
        self.stop_event = None
        self.thread = None
        self.running = False
    
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
        return self.function.__signature__
    
    def __call__(self, *args, **kwargs):
        if self.function is None:
            if len(args) != 1 or not callable(args[0]):
                raise TypeError("Cannot call progress before setting a function.")
            self.function = self._wrap_function(args[0])
            return self.function
        else:
            return self.function(*args, **kwargs)
    
    def __get__(self, obj, objtype=None):
        f = partial(self.function, obj)
        return self.__class__(f, infinite=self.infinite, progress=self.progress)
        
    def _wrap_function(self, function: Callable):
        @wraps(function)
        def _func(*args, **kwargs):
            with self:
                out = function(*args, **kwargs)
            return out
        return _func
    
    def _run(self):
        self.running = True
        
        if self.infinite:
            self.progress._as_infinite()
        while self.running:
            time.sleep(0.1)
    
    def __enter__(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
        self.pbar_was_visible = self.progress.visible
        self.progress.visible = True
        self.progress.show()
        self.progress.value = 0
        
        return self.progress

    def __exit__(self, exc_type, exc_value, traceback):
        self.running = False
        if self.thread is not None:
            self.thread.join()
        
        if self.close_on_finish:
            self.progress.close()
            del self.progress
        else:
            self.progress._pbar.min = 0
            self.progress._pbar.max = 1000
            self.progress._pbar.value = 1000
            self.progress.visible = self.pbar_was_visible