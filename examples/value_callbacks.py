from magicclass import magicclass, field
from magicclass.widgets import Figure
import numpy as np

options = {"widget_type": "FloatSlider", "min": 0.2, "max": 10}

@magicclass
class Plot:
    @magicclass(layout="horizontal")
    class parameters:
        a = field(int, options=options)
        b = field(int, options=options)

    plt = field(Figure)

    @parameters.a.connect
    @parameters.b.connect
    def _plot(self):
        a = self.parameters.a.value
        b = self.parameters.b.value
        t = np.linspace(0, 4*np.pi, 200)
        self.plt.cla()
        self.plt.plot(np.sin(a*t), np.sin(b*t))

if __name__ == "__main__":
    ui = Plot()
    ui.show()
