from napari import Viewer, current_viewer
from napari.layers import Layer
from macrokit import register_type, symbol, Symbol, Expr


register_type(Viewer, lambda viewer: Symbol("viewer", id(viewer)))


@register_type(Layer)
def _get_layer(layer: Layer):
    vw = symbol(current_viewer())
    expr = Expr("getitem", [Expr("getattr", [vw, "layers"]), layer.name])
    return expr
