"""Voice-activity detection: per-frame speech test + end-of-speech tracking."""

from __future__ import annotations

import webrtcvad

from .config import FRAME_MS, SAMPLE_RATE


class EndOfSpeech:
    """Tracks trailing silence; signals when a clip has ended.

    Speech must start before silence can end a clip — this prevents an
    immediate stop when the user hasn't begun speaking yet.
    """

    def __init__(self, level: int, silence_ms: int) -> None:
        self._vad = webrtcvad.Vad(level)
        self._silence_frames_needed = max(1, silence_ms // FRAME_MS)
        self._trailing_silence = 0
        self.heard_speech = False

    def is_speech(self, frame: bytes) -> bool:
        return self._vad.is_speech(frame, SAMPLE_RATE)

    def update(self, frame: bytes) -> bool:
        """Feed one frame. Returns True once end-of-speech is detected."""
        if self.is_speech(frame):
            self.heard_speech = True
            self._trailing_silence = 0
            return False
        self._trailing_silence += 1
        return self.heard_speech and self._trailing_silence >= self._silence_frames_needed
