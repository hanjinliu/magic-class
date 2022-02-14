import matplotlib.pyplot as plt
import numpy as np
from magicclass import magicclass
from pathlib import Path

@magicclass
class PlotData:
    """Load 1D data and plot it."""
    def __init__(self, title=None):
        self.title = title
        self.data = None
        self.path = None

    def random_data(self, loc=0.0, scale=1.0, size=100):
        """Generate random data."""
        self.data = np.random.normal(loc=loc, scale=scale, size=size)

    def load(self, path:Path):
        """Load file."""
        self.path = str(path)
        self.data = np.loadtxt(path)

    def plot(self):
        """Plot data."""
        if self.title:
            plt.title(self.title)
        plt.plot(self.data)
        plt.show()

if __name__ == "__main__":
    ui = PlotData()
    ui.show()
