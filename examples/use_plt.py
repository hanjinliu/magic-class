import numpy as np
from magicclass import magicclass, field
from magicclass.widgets import Figure

@magicclass
class RandomPlot:
    """Plot random data or clear it."""
    plt = field(Figure)

    def plot(self):
        """Plot random data."""
        self.plt.plot(np.random.random(100))

    def clear_plot(self):
        """Clear current data."""
        self.plt.cla()

if __name__ == "__main__":
    ui = RandomPlot()
    ui.show()
