from magicclass.ext.pandas import DataFrameView
import pandas as pd

def test_build():
    df = pd.DataFrame(
        [
            pd.Series([-1234566789, -10, -1, 0, 1, 123456789], dtype="int"),
            pd.Series([-123456678.9, -1, -1e-5, 0, 1.4e-5, 3.5e6], dtype="float"),
            pd.Series([True, False, True, False, True, False], dtype="bool"),
            pd.Series(["english", "Ελληνικά", "\n", "漢字", "😀", ""], dtype="string"),
            pd.date_range("2021-01-01", periods=6, freq="D"),
            pd.timedelta_range("1 days", periods=6, freq="D"),
            pd.Series([1 + 2j, 1 - 2j, 0, 1, 2, 3], dtype="complex"),
        ]
    )
    view = DataFrameView(value=df)
    view.show()
    view.close()
