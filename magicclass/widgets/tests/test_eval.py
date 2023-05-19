from magicclass.widgets import ColorEdit, ColormapEdit
from magicclass.widgets.eval import _get_last_group
import pytest

@pytest.mark.parametrize(
    "text, expected",
    [
        ("a.bb.ccc", "a.bb.ccc"),
        ("a.b2.c3.", "a.b2.c3."),
        ("f(3) + a.b", "a.b"),
        # ("2 + x['x+3  &'].re", "x['x+3  &'].re"),
        ("(pl.col('a') == 2) & (pl.col('b').", "pl.col('b')."),
    ]
)
def test_get_last(text: str, expected: str):
    assert _get_last_group(text) == expected

@pytest.mark.parametrize(
    "color",
    ["red", "#FF0000", "#FF0000AF", "#ff00ad", [0, 0.3, 0.2], [0.1, 0.2, 0.3, 0.4]]
)
def test_color(color):
    edit = ColorEdit(value=color)
    edit.value = color

@pytest.mark.parametrize(
    "cmap",
    [
        {0: [1, 1, 1], 1: [0, 1, 1]},
        {0: [1, 1, 1, 1], 1: [0, 1, 1, 1]},
        {0: [1, 1, 1], 0.4: [0, 1, 1], 1: [1, 0, 0]},
        {0: "red", 1: [0, 1, 1]}
    ]
)
def test_cmap(cmap):
    edit = ColormapEdit(value=cmap)
    edit.value = cmap
