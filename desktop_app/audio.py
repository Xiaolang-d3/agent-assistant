from __future__ import annotations

import tempfile
import wave
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices


class Recorder:
    """Capture microphone PCM and write a WAV file for Whisper."""

    def __init__(self) -> None:
        self.sample_rate = 16000
        self._source: QAudioSource | None = None
        self._buffer: QBuffer | None = None
        self._bytes = QByteArray()

    def start(self) -> None:
        fmt = QAudioFormat()
        fmt.setSampleRate(self.sample_rate)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            raise RuntimeError("没有找到麦克风")
        if not device.isFormatSupported(fmt):
            raise RuntimeError("麦克风不支持 16kHz 单声道录音")

        self._bytes = QByteArray()
        self._buffer = QBuffer(self._bytes)
        self._buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self._source = QAudioSource(device, fmt)
        self._source.start(self._buffer)

    def stop(self) -> Path | None:
        if self._source is None:
            return None
        self._source.stop()
        self._source = None
        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None

        raw = bytes(self._bytes)
        if len(raw) < 3200:
            return None

        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        path = Path(handle.name)
        handle.close()
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(raw)
        return path
