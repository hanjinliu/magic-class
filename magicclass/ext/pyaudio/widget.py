from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal
import numpy as np
from numpy.typing import NDArray
import pyaudio
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicgui.application import use_app
from magicclass._magicgui_compat import _mpl_image, ValueWidget
from magicclass.widgets.utils import merge_super_sigs


class QAudioImage(QtW.QLabel):
    """The (auto-updating) image of the audio data."""

    resized = Signal()

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._audio_data = np.zeros(0, dtype=np.int16)
        self.resized.connect(self.update)
        self._chunksize = 441

    def update(self) -> None:
        image = self._image_array()

        img = _mpl_image.Image()

        img.set_data(image)

        val = img.make_image()
        h, w, _ = val.shape
        qimage = QtGui.QImage(val, w, h, QtGui.QImage.Format.Format_RGBA8888)
        _pixmap = QtGui.QPixmap.fromImage(qimage).scaled(
            self.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(_pixmap)
        self.setMinimumSize(108, 28)
        super().update()

    def _image_array(self) -> NDArray[np.uint8]:
        w, h = self.width(), self.height()
        audio = _max_binning(self._audio_data, self._chunksize, w * 2)
        nh = h // 2
        sigmax = 2**16
        half_array = np.stack(
            [np.linspace(sigmax / nh, sigmax, nh, endpoint=False)] * audio.size,
            axis=1,
        )
        array = np.concatenate([half_array[::-1], half_array], axis=0)
        binary = array < audio
        image = np.full(array.shape + (4,), 240, dtype=np.uint8)
        image[binary] = np.array([0, 0, 255, 255], dtype=np.uint8)[np.newaxis]
        return image


def _max_binning(arr: NDArray[np.int16], n: int, width: int) -> NDArray[np.int16]:
    """Bin the input 1D data, clipped by the given width."""
    nchunks, res = divmod(arr.size, n)
    if nchunks < width:
        out_left = np.abs(arr[:-res]).reshape(-1, n).max(axis=1)
        out = np.concatenate([out_left, np.zeros(width - nchunks, dtype=np.int16)])
    else:
        out = np.abs(arr[:-res]).reshape(-1, n)[-width:].max(axis=1)
    return out


class QAudioRecorder(QtW.QWidget):
    valueChanged = Signal(object)

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._chunk = 1024
        self._rate = 44100
        self._format = pyaudio.paInt16
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            format=self._format,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
        )

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._update_data)

        self._setup_ui()
        self._recoding = False

    def _setup_ui(self):
        self._btn_rec = QtW.QPushButton("Rec")
        self._btn_rec.setFixedSize(28, 24)
        self._btn_clear = QtW.QPushButton("Clear")
        self._btn_clear.setFixedSize(34, 24)
        self._label = QAudioImage()
        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        layout.addWidget(self._label)
        layout.addWidget(self._btn_rec)
        layout.addWidget(self._btn_clear)

        self._btn_rec.clicked.connect(lambda: self.setRecording(not self.recording()))
        self._btn_clear.clicked.connect(
            lambda: self.setValue(np.zeros(0, dtype=np.int16))
        )

    def _update_data(self):
        _incoming = self._read_input()
        self.setValue(np.concatenate([self._label._audio_data, _incoming]))

    def _read_input(self):
        ret_bytes = self._stream.read(self._chunk)
        ret = np.frombuffer(ret_bytes, dtype=np.int16)
        return ret

    def recording(self) -> bool:
        return self._recoding

    def setRecording(self, value: bool) -> None:
        was_recording = self._recoding
        self._recoding = value
        if self._recoding and not was_recording:
            self._timer.start(10)
            self._btn_rec.setText("Stop")
        elif not self._recoding and was_recording:
            self._timer.stop()
            self._btn_rec.setText("Rec")

    def value(self) -> NDArray[np.int16]:
        return self._label._audio_data

    def setValue(self, value: NDArray[np.int16]) -> None:
        if not isinstance(value, np.ndarray):
            raise TypeError("value must be a numpy array")
        self._label._audio_data = value
        self._label.update()
        self.valueChanged.emit(value)

    def rate(self) -> int:
        return self._rate

    def setRate(self, value: int) -> None:
        if self._recoding:
            raise RuntimeError("Cannot change rate while recording")
        self._rate = value
        self._label._chunksize = self._rate // 100

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self._label.resized.emit()
        return super().resizeEvent(a0)


class _AudioRecorder(QBaseValueWidget):
    _qwidget: QAudioRecorder

    def __init__(self, **kwargs):
        super().__init__(QAudioRecorder, "value", "setValue", "valueChanged", **kwargs)


@merge_super_sigs
class AudioRecorder(ValueWidget):
    """
    A widget for recording microphone input.

    Parameters
    ----------
    value : array
        1D array of audio data.
    """

    def __init__(self, **kwargs):
        app = use_app()
        assert app.native
        kwargs["widget_type"] = _AudioRecorder
        super().__init__(**kwargs)
