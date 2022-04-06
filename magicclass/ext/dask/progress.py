from __future__ import annotations
from dask.callbacks import Callback
from ...utils.qthreading import _SupportProgress


class MyCallback(Callback):
    def _posttask(self, key, result, dsk, state, id):
        print("posttask", key)
