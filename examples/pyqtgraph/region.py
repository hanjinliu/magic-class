import numpy as np
from magicclass import magicclass, field
from magicclass.ext.pyqtgraph import QtPlotCanvas

@magicclass
class A:
    """
    Move the Region object in the upper canvas.
    The histogram is updated accordingly.
    """
    canvas = field(QtPlotCanvas)
    hist = field(QtPlotCanvas)

    def __post_init__(self):
        # prepare sample data
        data = np.concatenate([
            np.random.normal(loc=0, size=200),
            np.random.normal(loc=5, size=400),
            np.random.normal(loc=2.5, size=300)
        ])
        layer = self.canvas.add_curve(data)
        self.canvas.region.value = (0, 100)
        self.canvas.region.visible = True

        # connect the region changing signal to the histogram
        @self.canvas.region.changed.connect
        def _f(v: tuple[float, float]):
            x0, x1 = v
            ydata = layer.ydata
            x0 = max(int(x0), 0)
            x1 = min(int(x1) + 1, ydata.size)
            self.hist.layers.clear()
            self.hist.add_hist(ydata[x0:x1], bins=16)

if __name__ == '__main__':
    ui = A()
    ui.show()
