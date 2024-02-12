import numpy as np
from magicclass import magicclass, field
from magicclass.ext.vtk import VedoCanvas
import vedo

@magicclass
class VedoViewerUI:
    canvas = field(VedoCanvas)

ui = VedoViewerUI()

coords = np.random.randn(1000, 3)
data = np.cos(coords[:,1])

# create a points object and a set of axes
points = vedo.Points(coords)
points.cmap("viridis", data).add_scalarbar3d()
axes = vedo.Axes(points, c="white")

# create a histogram of data
histo = vedo.pyplot.histogram(
    data, 
    bins=10, 
    c="viridis",
    title="", xtitle="", ytitle="",
).clone2d("bottom-right", 0.25)

# add the points and axes to the plotter
ui.canvas.plotter.add([points, axes, histo]).reset_camera()

# start the UI
ui.show()