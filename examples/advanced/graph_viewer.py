from magicclass import magicclass, field, click, magiccontext
from magicclass.ext.pyqtgraph import QtPlotCanvas
from magicclass.ext.qtconsole import QtConsole

@magicclass(labels=False, layout="horizontal")
class Layer:
    @magiccontext
    class ContextMenu:
        def Delete_item(self): ...

    def __init__(self, linked_item=None, viewer=None):
        self.item = linked_item
        self.viewer = viewer

    @ContextMenu.wraps
    def Delete_item(self):
        self.viewer.canvas.remove_item(self.item)
        self.viewer.layerlist.remove(self)

    check = field(True)
    layer_name = field(str)

@magicclass(widget_type="list")
class LayerList:
    """List of plot items"""

@magicclass(layout="horizontal")
class Viewer:
    layerlist = LayerList()
    canvas = QtPlotCanvas()
    console = QtConsole()

    def __post_init__(self):
        self.layerlist.max_width = 250
        self.layerlist.width = 250

    @click(visible=False)
    def add_curve(self, x, y=None, name=None, **kwargs):
        self._add_plot_item(self.canvas.add_curve, x, y, name, **kwargs)

    @click(visible=False)
    def add_scatter(self, x, y=None, name=None, **kwargs):
        self._add_plot_item(self.canvas.add_scatter, x, y, name, **kwargs)

    def _add_plot_item(self, f, x, y, name, **kwargs):
        f(x, y, **kwargs)
        name = name or "Data"
        layer = Layer(self.canvas._items[-1], viewer=self)
        layer.check.text = ""
        layer.layer_name.value = name
        layer.layer_name.max_width = 64
        layer.layer_name.width = 64
        self.layerlist.append(layer)

        @layer.check.changed.connect
        def _(v: bool):
            layer.item.visible = v

if __name__ == "__main__":
    ui = Viewer()
    ui.show()
