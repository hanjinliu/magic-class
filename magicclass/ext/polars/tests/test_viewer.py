from magicclass.ext.polars import DataFrameView
import polars as pl
from datetime import date, timedelta

def test_build():
    df = pl.DataFrame(
        [
            pl.Series([-1234566789, -10, -1, 0, 1, 123456789], dtype=pl.Int32),
            pl.Series([-123456678.9, -1, -1e-5, 0, 1.4e-5, 3.5e6], dtype=pl.Float64),
            pl.Series([True, False, True, False, True, False], dtype=pl.Boolean),
            pl.Series(["english", "Ελληνικά", "\n", "漢字", "😀", ""], dtype=pl.Utf8),
            pl.date_range(date(2021, 1, 1), date(2021, 1, 6), timedelta(1)),
        ]
    )
    view = DataFrameView(value=df)
    view.show()
    view.close()
