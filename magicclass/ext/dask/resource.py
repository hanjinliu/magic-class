from __future__ import annotations
from dask.diagnostics import ResourceProfiler
from dask.diagnostics.profile import _Tracker, import_required, current_process
from timeit import default_timer
from time import sleep
from psygnal import Signal
from magicgui.widgets import Container, LineEdit
import datetime


class DaskResourceProfiler(ResourceProfiler, Container):
    def __init__(self, dt: float = 1.0, **kwargs):
        ResourceProfiler.__init__(self, dt=dt)
        self._tic = LineEdit(value="0:00:00")
        self._mem = LineEdit(value="--- MB")
        self._cpu = LineEdit(value="--- %")
        Container.__init__(self, widgets=[self._tic, self._mem, self._cpu], **kwargs)

    def clear(self):
        ResourceProfiler.clear(self)

    def _start_collect(self):
        if not self._is_running():
            self._tracker = EventedTracker(self._dt)

            def _c(a):
                self._update_display(a)

            self._tracker.callback = _c
            self._tracker.start()
        self._tracker.parent_conn.send("collect")

    # def _stop_collect(self):
    #     super()._stop_collect()
    #     self._tracker.changed.disconnect(self._update_display)

    def _update_display(self, tp: tuple[float, float, float]):
        tic, mem, cpu = tp
        t = datetime.timedelta(seconds=int(tic))
        self._tic.value = str(t)
        self._mem.value = f"{mem} MB"
        self._cpu.value = f"{cpu} %"


class EventedTracker(_Tracker):
    def run(self):

        psutil = import_required(
            "psutil", "Tracking resource usage requires `psutil` to be installed"
        )
        self.parent = psutil.Process(self.parent_pid)

        pid = current_process()
        data = []
        while True:
            try:
                msg = self.child_conn.recv()
            except KeyboardInterrupt:
                continue
            if msg == "shutdown":
                break
            elif msg == "collect":
                ps = self._update_pids(pid)
                while not data or not self.child_conn.poll():
                    tic = default_timer()
                    mem = cpu = 0
                    for p in ps:
                        try:
                            mem2 = p.memory_info().rss
                            cpu2 = p.cpu_percent()
                        except Exception:  # could be a few different exceptions
                            pass
                        else:
                            # Only increment if both were successful
                            mem += mem2
                            cpu += cpu2
                    _new_data = (tic, mem / 1e6, cpu)
                    data.append(_new_data)
                    self.callback(_new_data)
                    sleep(self.dt)
            elif msg == "send_data":
                self.child_conn.send(data)
                data = []
        self.child_conn.close()
