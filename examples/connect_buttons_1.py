from magicclass import magicclass, click, field
from magicclass.widgets import Figure
import numpy as np
from scipy.optimize import curve_fit

# If magic-class is nested, you must change the namespace.
# Use "." to get access to methods in other classes.

def gaussian(x, mean, sd):
    z = (x-mean)/sd
    a = 1 / np.sqrt(2*np.pi) / sd
    return a * np.exp(-z**2 / 2)

x = np.linspace(-5, 5, 300)

@magicclass(layout="horizontal")
class Main:
    @magicclass
    class random:
        """
        Random sampling
        """        
        mean = field(float)
        sd = field(float, options={"min": 1, "step": 0.5})
        noise = field(float, options={"min": 0.1, "step": 0.05, "max": 1.0})
        
        # Here namespace is "random"
        @click(enabled=True, enables=".fitter.fit", disables="sampling")
        def sampling(self):
            y = gaussian(x, self.mean.value, self.sd.value) + \
                np.random.normal(scale=self.noise.value, size=x.size)
            self.canvas.ax.cla()
            self.canvas.ax.plot(x, y)
            self.canvas.draw()
            self.y = y
        
        canvas = Figure()
    
    @magicclass
    class fitter:
        """
        Curve fitting
        """        
        mean = field(float)
        sd = field(float, options={"min": 1, "step": 0.5})
        def fit(self): ... # pre-definition
        canvas = Figure()
    
    # Here namespace is "Main" (although button widget will appear in "fitter"!!)
    @fitter.wraps
    @click(enabled=False, enables="random.sampling", disables="fitter.fit")
    def fit(self):
        ft = self.fitter
        ydata = self.random.y
        p0 = [ft.mean.value, ft.sd.value]
        params, _ = curve_fit(gaussian, x, ydata, p0=p0)
        self.yfit = gaussian(x, *params)
        ft.canvas.ax.cla()
        ft.canvas.ax.scatter(x, ydata, color="gray", marker="+")
        ft.canvas.ax.plot(x, self.yfit, color="red")
        ft.canvas.draw()
        
    
        
if __name__ == "__main__":
    ui = Main()
    ui.show()