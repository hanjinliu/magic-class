import numpy as np
from scipy.signal import medfilt
from magicclass import magicclass, field
from magicclass.utils import click
from magicclass.widgets import Figure

# `click` is useful when functions should be called in certain order.
# In following example, random data must be generated before applying filter.

@magicclass
class A:
    def __init__(self):
        self._data = None
        self._filtered = None

    @click(enables="apply_filter")
    def generate_data(self, size: int = 200):
        """Generate random data."""
        self._data = np.random.normal(size=size)

    @click(enables="plot_data", disables="apply_filter", enabled=False)
    def apply_filter(self, width: int = 3):
        """Apply median filter."""
        self._filtered = medfilt(self._data, kernel_size=width)

    @click(enabled=False)
    def plot_data(self):
        """Plot the results."""
        self.plt.cla()
        self.plt.plot(self._data, label="original data")
        self.plt.plot(self._filtered, label="filtered data")
        self.plt.legend()

    plt = field(Figure)

if __name__ == "__main__":
    ui = A()
    ui.show(run=True)
