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
