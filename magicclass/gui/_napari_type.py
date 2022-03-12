from napari import Viewer
from napari.layers import Layer
from macrokit import register_type, Symbol, Expr

VIEWER_SYMBOL = Symbol.var("viewer")

register_type(Viewer, lambda viewer: VIEWER_SYMBOL)


@register_type(Layer)
def _get_layer(layer: Layer):
    expr = Expr("getitem", [Expr("getattr", [VIEWER_SYMBOL, "layers"]), layer.name])
    return expr
