from napari import Viewer
from napari.layers import Layer
from macrokit import register_type, Symbol, Expr

VIEWER_SYMBOL = Symbol.var("viewer")

# NOTE: To support macro recording when multiple viewer exists, calling
# napari.current_viewer() is not safe if a new viewer is created during a function
# call. Since standard Python script does not distinguish different viewers, here
# we simply let "viewer" to represent any viewer.
register_type(Viewer, lambda viewer: VIEWER_SYMBOL)


@register_type(Layer)
def _get_layer(layer: Layer):
    """Record layer object as ``viewer.layers["layer-name"]``"""

    expr = Expr("getitem", [Expr("getattr", [VIEWER_SYMBOL, "layers"]), layer.name])
    return expr
