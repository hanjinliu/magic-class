import numpy as np
import matplotlib.pyplot as plt
from magicclass import magicclass, field
from magicclass.widgets import Figure

@magicclass
class RandomPlot:
    """
    Plot random data or clear it.
    """    
    figure = field(Figure)
        
    def plot(self):
        """
        Plot random data.
        """        
        self.figure.ax.plot(np.random.random(100))
        self.figure.draw()
    
    def clear_plot(self):
        """
        Clear current data.
        """        
        self.figure.ax.cla()
        self.figure.draw()
        
if __name__ == "__main__":
    ui = RandomPlot()
    ui.show()