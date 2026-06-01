"""Menu-bar app + dictation state machine.

Threading model:
  - rumps owns the AppKit main loop.
  - The pynput hotkey listener runs on its own thread; its callbacks only flip
    flags / spawn the worker — they never touch AppKit.
  - One worker thread runs the whole record -> transcribe -> confirm -> inject
    pipeline so neither the listener nor the main loop blocks.
  - A main-thread rumps.Timer mirrors shared status into the menu-bar icon.
  - The Settings window is opened from a menu callback (main thread).
"""

from __future__ import annotations

import threading
from pathlib import Path

import rumps

from . import confirm, inject, stt
from .audio import Recorder
from .config import Config, SAMPLE_RATE, load
from .hotkey import HotkeyListener
from .vad import EndOfSpeech

_ICON_DIR = Path(__file__).parent / "resources" / "icons"
_STATE_ICON = {
    "idle": "idle.png",
    "recording": "recording.png",
    "transcribing": "busy.png",
    "confirming": "confirming.png",
    "sending": "busy.png",
}
# Fallback glyphs if the icon files aren't bundled.
_STATE_EMOJI = {
    "idle": "🎙︎", "recording": "🔴", "transcribing": "✍︎",
    "confirming": "❓", "sending": "⏎",
}


def _icon_path(state: str) -> str | None:
    p = _ICON_DIR / _STATE_ICON.get(state, "idle.png")
    return str(p) if p.exists() else None


class App(rumps.App):
    def __init__(self, cfg: Config) -> None:
        first = _icon_path("idle")
        super().__init__("speech2terminal", icon=first, template=True, quit_button=None)
        if first is None:
            self.title = _STATE_EMOJI["idle"]
        self.cfg = cfg
        self.recorder = Recorder()

        self._status = "idle"
        self._rendered = None
        self._transcript = ""
        self._lock = threading.Lock()
        self._stop_flag = threading.Event()
        self._worker: threading.Thread | None = None
        self._settings = None  # retained SettingsController

        self.status_item = rumps.MenuItem("Idle")
        self.transcript_item = rumps.MenuItem("—")
        self.menu = [
            self.status_item,
            self.transcript_item,
            None,
            rumps.MenuItem("Settings…", callback=self._open_settings),
            None,
            rumps.MenuItem("Quit", callback=self._quit),
        ]

        self._hk: HotkeyListener | None = None
        self._start_hotkey()

        self._timer = rumps.Timer(self._tick, 0.15)
        self._timer.start()

    # ---- UI -------------------------------------------------------------
    def _tick(self, _) -> None:
        with self._lock:
            status, transcript = self._status, self._transcript
        if status != self._rendered:
            self._rendered = status
            path = _icon_path(status)
            if path is not None:
                self.icon = path
            else:
                self.title = _STATE_EMOJI.get(status, "🎙︎")
        self.status_item.title = f"Status: {status}"
        self.transcript_item.title = transcript[:60] or "—"

    def _set(self, status: str | None = None, transcript: str | None = None) -> None:
        with self._lock:
            if status is not None:
                self._status = status
            if transcript is not None:
                self._transcript = transcript

    def _open_settings(self, _) -> None:
        from .settings_window import SettingsController
        if self._settings is None:
            self._settings = SettingsController.alloc().initWithConfig_onApply_(
                self.cfg, self._apply_settings)
        self._settings.show()

    def _apply_settings(self) -> None:
        # Config object was mutated + saved in place; just re-arm the hotkey.
        self._start_hotkey()

    # ---- hotkey ---------------------------------------------------------
    def _start_hotkey(self) -> None:
        if self._hk is not None:
            self._hk.stop()
        self._hk = HotkeyListener(
            self.cfg.hotkey,
            self.cfg.trigger_mode,
            self.cfg.long_press_ms,
            self.on_start,
            self.on_stop,
            self.is_recording,
        )
        self._hk.start()

    def is_recording(self) -> bool:
        with self._lock:
            return self._status == "recording"

    def on_start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_flag.clear()
        self._worker = threading.Thread(target=self._pipeline, daemon=True)
        self._worker.start()

    def on_stop(self) -> None:
        self._stop_flag.set()

    # ---- pipeline -------------------------------------------------------
    def _record(self, end_on_silence: bool, max_s: int) -> bytes:
        eos = EndOfSpeech(self.cfg.vad_level, self.cfg.silence_ms)
        buf = bytearray()
        max_bytes = max_s * SAMPLE_RATE * 2
        self.recorder.start()
        try:
            while not self._stop_flag.is_set() and len(buf) < max_bytes:
                frame = self.recorder.frames()
                if frame is None:
                    continue
                buf.extend(frame)
                if end_on_silence and eos.update(frame):
                    break
        finally:
            self.recorder.stop()
        return bytes(buf)

    def _transcribe(self, pcm: bytes) -> str:
        return stt.transcribe(pcm, self.cfg.model)

    def _pipeline(self) -> None:
        try:
            self._set(status="recording", transcript="")
            end_on_silence = self.cfg.trigger_mode == "auto_silence"
            pcm = self._record(end_on_silence, self.cfg.max_record_s)

            self._set(status="transcribing")
            text = self._transcribe(pcm)
            if not text:
                self._set(status="idle", transcript="(nothing heard)")
                return
            self._set(transcript=text)

            self._set(status="confirming")
            decision = self._confirm(text)
            if decision == "discard":
                self._set(status="idle")
                return

            self._set(status="sending")
            run = decision == "run" and self.cfg.press_enter_on_run
            inject.send(text, run, self.cfg)
        except Exception as exc:
            self._set(transcript=f"error: {exc}")
        finally:
            self._set(status="idle")

    def _confirm(self, text: str) -> str:
        mode = self.cfg.confirm_mode
        if mode == "paste_only":
            return "insert"
        if mode == "overlay":
            return confirm.confirm_overlay(text)
        self._stop_flag.clear()
        record_clip = lambda: self._record(True, self.cfg.confirm_listen_s)
        return confirm.confirm_voice(text, record_clip, self._transcribe)

    def _quit(self, _) -> None:
        if self._hk is not None:
            self._hk.stop()
        rumps.quit_application()


def main() -> None:
    App(load()).run()


if __name__ == "__main__":
    main()
