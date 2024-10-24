import sys
import numpy as np
from numpy.testing import assert_allclose
from magicclass.ext.vispy import VispyPlotCanvas
import pytest

@pytest.mark.skipif(not (sys.version_info < (3, 13)), reason="requires python<3.13")
def test_add_and_delete_data():
    canvas = VispyPlotCanvas()
    curve = canvas.add_curve(np.random.random(100), color="blue")
    assert len(canvas.layers) == 1
    scatter = canvas.add_scatter(np.random.random(100), color="red")
    assert len(canvas.layers) == 2
    del canvas.layers[0]
    assert len(canvas.layers) == 1

# TODO: face_color is not a valid name
# def test_property():
#     canvas = VispyPlotCanvas()
#     curve = canvas.add_curve(np.random.random(100), color="blue")
#     scatter = canvas.add_scatter(np.random.random(100), color="blue")
#     for layer in (curve, scatter):
#         assert_allclose(layer.face_color, [0, 0, 1, 1])
#         assert_allclose(layer.edge_color, [0, 0, 1, 1])
#         layer.color = "red"
#         assert_allclose(layer.face_color, [1, 0, 0, 1])
#         assert_allclose(layer.edge_color, [1, 0, 0, 1])
#         layer.name = "new name"
#         assert layer.visible
#         layer.visible = False
#         assert not layer.visible
