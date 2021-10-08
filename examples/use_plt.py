import numpy as np
import matplotlib.pyplot as plt
from magicclass import magicclass
from magicclass.widgets import Figure

@magicclass
class RandomPlot:
    """
    Plot random data or clear it.
    """    
    def __post_init__(self):
        self.fig, self.ax = plt.subplots()
        self.append(Figure(self.fig))
        
    def plot(self):
        """
        Plot random data.
        """        
        self.ax.plot(np.random.random(100))
        self.fig.canvas.draw()
    
    def clear_plot(self):
        """
        Clear current data.
        """        
        self.ax.cla()
        self.fig.canvas.draw()
        
if __name__ == "__main__":
    ui = RandomPlot()
    ui.show()