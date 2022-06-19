from __future__ import annotations
import pandas as pd
from functools import wraps
from ._dataframe import WidgetDataFrame


@wraps(pd.read_csv)
def read_csv(*args, **kwargs):
    df = pd.read_csv(*args, **kwargs)
    return WidgetDataFrame(data=df)


@wraps(pd.read_excel)
def read_excel(*args, **kwargs) -> WidgetDataFrame:
    df = pd.read_excel(*args, **kwargs)
    return WidgetDataFrame(data=df)
