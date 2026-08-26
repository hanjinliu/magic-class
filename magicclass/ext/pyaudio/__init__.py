from .widget import AudioRecorder
from typing import NewType
import numpy as np
from numpy.typing import NDArray
from magicgui import register_type

__all__ = ["AudioRecorder", "AudioData"]

AudioData = NewType("AudioData", NDArray[np.int16])

register_type(AudioData, widget_type=AudioRecorder)

__doc__ = """
An extension submodule for audio input.

Examples
--------

>>> from magicgui import magicgui
>>> from magicclass.ext.pyaudio import AudioData
>>> @magicgui
>>> def foo(audio: AudioData):
...     print(audio.shape)
"""
