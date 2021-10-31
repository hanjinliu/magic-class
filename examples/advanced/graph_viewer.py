from magicclass import magicclass, field, click, magicmenu
from magicclass.qtgraph import Canvas
from magicclass.console import Console

@magicclass(labels=False, layout="horizontal")
class Layer:
    def __init__(self, linked_item=None):
        self.item = linked_item
        
    check = field(True)
    layer_name = field(str)

@magicclass(widget_type="list")
class LayerList:
    """List of plot items"""

@magicclass(layout="horizontal")
class Viewer:
    layerlist = LayerList()
    canvas = Canvas()
    
    @click(visible=False)
    def add_curve(self, x, y=None, name=None, **kwargs):
        self._add_plot_item(self.canvas.add_curve, x, y, name, **kwargs)
    
    @click(visible=False)
    def add_scatter(self, x, y=None, name=None, **kwargs):
        self._add_plot_item(self.canvas.add_scatter, x, y, name, **kwargs)
    
    def _add_plot_item(self, f, x, y, name, **kwargs):
        f(x, y, **kwargs)
        name = name or "Data"
        layer = Layer(self.canvas._items[-1])
        layer.check.text = ""
        layer.layer_name.value = name
        layer.layer_name.max_width = 32
        layer.layer_name.width = 32
        self.layerlist.append(layer)
        
        @layer.check.changed.connect
        def _(v: bool):
            layer.item.visible = v
    
if __name__ == "__main__":
    ui = Viewer()
    ui.show()