"""Mic capture via sounddevice into a thread-safe queue of int16 frames."""

from __future__ import annotations

import queue

import numpy as np
import sounddevice as sd

from .config import FRAME_MS, SAMPLE_RATE

FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000  # samples per VAD frame


class Recorder:
    """Streams the mic in FRAME_MS chunks. Call start(), pull frames(), stop()."""

    def __init__(self) -> None:
        self._q: queue.Queue[bytes] = queue.Queue()
        self._stream: sd.InputStream | None = None

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        # indata is int16 mono; ship raw bytes so webrtcvad can read PCM directly.
        self._q.put(bytes(indata))

    def start(self) -> None:
        if self._stream is not None:
            return
        self._q = queue.Queue()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            callback=self._callback,
        )
        self._stream.start()

    def frames(self, timeout: float = 0.5) -> bytes | None:
        """Block up to `timeout` for the next frame; None if none arrived."""
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


def pcm_to_float32(pcm: bytes) -> np.ndarray:
    """int16 PCM bytes -> float32 [-1, 1] for Whisper."""
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    return audio / 32768.0
