from __future__ import annotations
from qtpy.QtGui import QFont, QTextOption
from qtpy.QtCore import Qt
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from .utils import FrozenContainer
from magicgui.widgets import PushButton, TextEdit

class Figure(FrozenContainer):
    """
    A matplotlib figure canvas.
    """    
    def __init__(self, 
                 nrows: int = 1,
                 ncols: int = 1,
                 figsize: tuple[int, int] = (4, 3),
                 style = None,
                 layout: str = "vertical", 
                 **kwargs):
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
        
        super().__init__(layout=layout, labels=False, **kwargs)
        canvas = FigureCanvas(fig)
        self.set_widget(canvas)
        self.figure = fig
        self.min_height = 40
        
    def draw(self):
        self.figure.tight_layout()
        self.figure.canvas.draw()
    
    @property
    def axes(self):
        return self.figure.axes
    
    @property
    def ax(self):
        try:
            _ax = self.axes[0]
        except IndexError:
            _ax = self.figure.add_subplot(111)
        return _ax
        

class ConsoleTextEdit(TextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.native.setFont(QFont("Consolas"))
        self.native.setWordWrapMode(QTextOption.NoWrap)
        # TODO: copy, save, run actions
    

class CheckButton(PushButton):
    def __init__(self, text:str|None=None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native.setCheckable(True)
