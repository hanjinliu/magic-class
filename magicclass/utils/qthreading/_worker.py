from __future__ import annotations

from typing import TypeVar
import time
from superqt.utils import GeneratorWorker
from magicclass._exceptions import Aborted

_Y = TypeVar("_Y")
_S = TypeVar("_S")
_R = TypeVar("_R")


class GeneratorWorker2(GeneratorWorker[_Y, _S, _R]):
    def work(self) -> _R | Exception:
        """Almost the same as GeneratorWorker.work, but raise error on aborted."""
        while True:
            if self.abort_requested:
                Aborted.raise_(func=self._gen)
            if self._paused:
                if self._resume_requested:
                    self._paused = False
                    self._resume_requested = False
                    self.resumed.emit()
                else:
                    time.sleep(self._pause_interval)
                    continue
            elif self._pause_requested:
                self._paused = True
                self._pause_requested = False
                self.paused.emit()
                continue
            try:
                _input = self._next_value()
                output = self._gen.send(_input)
                self.yielded.emit(output)
            except StopIteration as exc:
                return exc.value
            except RuntimeError as exc:
                # The worker has probably been deleted.  warning will be
                # emitted in `WorkerBase.run`
                return exc
