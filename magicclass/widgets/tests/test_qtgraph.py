from magicclass import field, magicclass
from magicclass.widgets import QtPlotCanvas
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
    item.visible = False
    item.face_color = "yellow"
    item.edge_color = "yellow"
    item.lw = 1
    for ls in ["-", "--", ":", "-."]:
        item.ls = ls
    item.xdata = item.xdata + 1
    item.ydata = item.ydata + 1
    assert item.ndata == ndata
    
    assert len(ui.plot.layers) == 3
    ui.plot.layers.clear()
    
    # test scatter
    ui.plot.add_scatter(data)
    ui.plot.add_scatter(np.arange(ndata)*2, data)
    item = ui.plot.add_scatter(data, face_color="green", edge_color="green", name="test", lw=2, ls=":", size=6, symbol="*")
    item.visible = False
    item.face_color = "yellow"
    item.edge_color = "yellow"
    item.lw = 1
    for ls in ["-", "--", ":", "-."]:
        item.ls = "-"
    for sym in ["o", "s", "D", "^", "<", "v", ">", "*"]:
        item.symbol = sym
    item.xdata = item.xdata + 1
    item.ydata = item.ydata + 1
    assert item.ndata == ndata
    
    assert len(ui.plot.layers) == 3
    ui.plot.layers.clear()
    
    # test curve scatter
    ui.plot.add_curve_scatter(data)
    ui.plot.add_curve_scatter(np.arange(ndata)*2, data)
    item = ui.plot.add_curve_scatter(data, face_color="green", edge_color="green", name="test", lw=2, ls=":", size=6, symbol="*")
    item.visible = False
    item.face_color = "yellow"
    item.edge_color = "yellow"
    item.lw = 1
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
    item.visible = False
    item.face_color = "yellow"
    item.edge_color = "yellow"
    item.lw = 1
    for ls in ["-", "--", ":", "-."]:
        item.ls = ls
    item.xdata = item.xdata + 1
    item.ydata = item.ydata + 1
    assert item.ndata == ndata
    
    assert len(ui.plot.layers) == 3
    ui.plot.layers.clear()
    
    ui.plot.add_hist(data)
    item = ui.plot.add_hist(data, bins=14, range=[-0.5, 1.5], density=True)
    item.visible = False
    item.face_color = "yellow"
    item.edge_color = "yellow"
    item.lw = 1
    for ls in ["-", "--", ":", "-."]:
        item.ls = ls
        
    assert len(ui.plot.layers) == 2