from magicclass import magicclass, field, magiccontext, MagicTemplate, nogui, abstractapi
from magicclass.ext.pyqtgraph import QtPlotCanvas
from magicclass.ext.qtconsole import QtConsole

@magicclass(labels=False, layout="horizontal")
class Layer(MagicTemplate):
    @magiccontext
    class ContextMenu(MagicTemplate):
        Delete_item = abstractapi()

    def __init__(self, linked_item=None):
        self.item = linked_item

    @property
    def viewer(self):
        return self.find_ancestor(Viewer)

    @ContextMenu.wraps
    def Delete_item(self):
        self.viewer.canvas.layers.remove(self.item)
        self.viewer.layerlist.remove(self)

    check = field(True)
    layer_name = field(str)

@magicclass(layout="horizontal")
class Viewer(MagicTemplate):
    @magicclass(widget_type="list")
    class layerlist(MagicTemplate):
        """List of plot items"""
        def __post_init__(self):
            self.min_width = 200

    @magicclass
    class SidePanel(MagicTemplate):
        canvas = abstractapi()
        console = abstractapi()

    canvas = SidePanel.field(QtPlotCanvas)
    console = SidePanel.field(QtConsole)

    def __post_init__(self):
        self.layerlist.max_width = 250
        self.layerlist.width = 250
        import numpy
        self.console.update_console({"np": numpy})

    @nogui
    def add_curve(self, x, y=None, name=None, **kwargs):
        self._add_plot_item(self.canvas.add_curve, x, y, name, **kwargs)

    @nogui
    def add_scatter(self, x, y=None, name=None, **kwargs):
        self._add_plot_item(self.canvas.add_scatter, x, y, name, **kwargs)

    def _add_plot_item(self, f, x, y, name, **kwargs):
        f(x, y, **kwargs)
        name = name or "Data"
        layer = Layer(self.canvas.layers[-1])
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
