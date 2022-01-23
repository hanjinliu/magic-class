from napari import Viewer, current_viewer
from napari.layers import Layer
from macrokit import register_type, symbol, Expr

# TODO: cannot execute macro including viewer. Should update on the macro-kit side.
register_type(Viewer, lambda e: "viewer")

@register_type(Layer)
def _get_layer(layer: Layer):
    vw = symbol(current_viewer())
    expr = Expr("getitem", 
                [Expr("getattr", 
                      [vw,
                       "layer"]), 
                 layer.name])
    return expr
