from magicclass import field, magicclass
from magicclass.ext.pyqtgraph import QtPlotCanvas
import numpy as np

def test_plot_canvas():
    @magicclass
    class A:
        plot = field(QtPlotCanvas)

    ui = A()
    ndata = 100
    data = np.random.random(ndata)

    # test curve
    ui.plot.add_curve(data)
    ui.plot.add_curve(np.arange(ndata)*2, data)
    item = ui.plot.add_curve(data, face_color="green", edge_color="green", name="test", lw=2, ls=":")
    item.visible
    item.visible = False
    item.face_color
    item.face_color = "yellow"
    item.edge_color
    item.edge_color = "yellow"
    item.lw
    item.lw = 1
    item.ls
    for ls in ["-", "--", ":", "-."]:
        item.ls = ls
    item.symbol
    for sym in ["o", "s", "D", "^", "<", "v", ">", "*"]:
        item.symbol = sym
    item.xdata = item.xdata + 1
    item.ydata = item.ydata + 1
    assert item.ndata == ndata

    assert len(ui.plot.layers) == 3
    ui.plot.layers.clear()

    # test scatter
    ui.plot.add_scatter(data)
    ui.plot.add_scatter(np.arange(ndata)*2, data)
    item = ui.plot.add_scatter(data, face_color="green", edge_color="green", name="test", lw=2, ls=":", size=6, symbol="*")
    item.visible
    item.visible = False
    item.face_color
    item.face_color = "yellow"
    item.edge_color
    item.edge_color = "yellow"
    item.lw
    item.lw = 1
    item.ls
    for ls in ["-", "--", ":", "-."]:
        item.ls = "-"
    for sym in ["o", "s", "D", "^", "<", "v", ">", "*"]:
        item.symbol = sym
    item.xdata = item.xdata + 1
    item.ydata = item.ydata + 1
    assert item.ndata == ndata

    assert len(ui.plot.layers) == 3
    ui.plot.layers.clear()

    # test bar
    ui.plot.add_bar(data)
    ui.plot.add_bar(np.arange(ndata)*2, data)
    item = ui.plot.add_bar(data, face_color="green", edge_color="green", name="test", lw=2, ls=":")
    item.visible
    item.visible = False
    item.face_color
    item.face_color = "yellow"
    item.edge_color
    item.edge_color = "yellow"
    item.lw
    item.lw = 1
    item.ls
    for ls in ["-", "--", ":", "-."]:
        item.ls = ls
    item.xdata = item.xdata + 1
    item.ydata = item.ydata + 1
    assert item.ndata == ndata

    assert len(ui.plot.layers) == 3
    ui.plot.layers.clear()

    ui.plot.add_hist(data)
    item = ui.plot.add_hist(data, bins=14, range=[-0.5, 1.5], density=True)
    item.visible
    item.visible = False
    item.face_color
    item.face_color = "yellow"
    item.edge_color
    item.edge_color = "yellow"
    item.lw
    item.lw = 1
    item.ls
    for ls in ["-", "--", ":", "-."]:
        item.ls = ls

    assert len(ui.plot.layers) == 2

    # test region
    ui.plot.region.visible
    ui.plot.region.visible = True
    ui.plot.region.value
    ui.plot.region.value = [-1, 2]
    ui.plot.region.enabled
    ui.plot.region.enabled = True
    ui.plot.region.color
    ui.plot.region.color = "blue"

    # test legend
    ui.plot.legend.visible
    ui.plot.legend.visible = True
    ui.plot.legend.color
    ui.plot.legend.color = "black"
    ui.plot.legend.size
    ui.plot.legend.size = 10
    ui.plot.legend.background_color
    ui.plot.legend.background_color = [1, 1, 1, 0.2]
    ui.plot.legend.border
    ui.plot.legend.border = "red"
