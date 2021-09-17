from magicclass import magicclass, field
from magicclass.widgets import Figure
import numpy as np

options = {"widget_type": "FloatSlider", "min": 0.2, "max": 10}

@magicclass
class Plot:
    a:int = field(options=options)
    b:int = field(options=options)
    canvas = field(Figure)
    
    @a.connect
    @b.connect
    def _plot(self, event=None):
        t = np.linspace(0, 4*np.pi, 200)
        self.canvas.ax.cla()
        self.canvas.ax.plot(np.sin(self.a*t), np.sin(self.b*t))
        self.canvas.draw()

if __name__ == "__main__":
    m = Plot()
    m.show()