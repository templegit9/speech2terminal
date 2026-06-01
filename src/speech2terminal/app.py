"""Menu-bar app + dictation state machine.

Threading model:
  - rumps owns the AppKit main loop.
  - The pynput hotkey listener runs on its own thread; its callbacks only
    flip flags / spawn the worker — they never touch AppKit.
  - One worker thread runs the whole record -> transcribe -> confirm -> inject
    pipeline so neither the listener nor the main loop blocks.
  - A main-thread rumps.Timer mirrors shared status into the menu (UI updates
    must happen on the main thread).
"""

from __future__ import annotations

import threading

import rumps

from . import confirm, inject, stt
from .audio import Recorder
from .config import Config, SAMPLE_RATE, load
from .hotkey import HotkeyListener
from .vad import EndOfSpeech

TRIGGER_MODES = ["push_to_talk", "auto_silence", "toggle"]
CONFIRM_MODES = ["voice", "paste_only", "overlay"]
TARGETS = ["paste", "tmux"]


class App(rumps.App):
    def __init__(self, cfg: Config) -> None:
        super().__init__("🎙︎", quit_button=None)
        self.cfg = cfg
        self.recorder = Recorder()

        self._status = "idle"
        self._transcript = ""
        self._lock = threading.Lock()
        self._stop_flag = threading.Event()
        self._worker: threading.Thread | None = None

        self.status_item = rumps.MenuItem("Idle")
        self.transcript_item = rumps.MenuItem("—")
        self.menu = [
            self.status_item,
            self.transcript_item,
            None,
            self._mode_submenu("Trigger", TRIGGER_MODES, "trigger_mode"),
            self._mode_submenu("Confirm", CONFIRM_MODES, "confirm_mode"),
            self._mode_submenu("Target", TARGETS, "target"),
            None,
            rumps.MenuItem("Quit", callback=self._quit),
        ]

        self._hk: HotkeyListener | None = None
        self._start_hotkey()

        self._timer = rumps.Timer(self._tick, 0.2)
        self._timer.start()

    # ---- UI -------------------------------------------------------------
    def _mode_submenu(self, label: str, options: list[str], attr: str) -> rumps.MenuItem:
        parent = rumps.MenuItem(label)
        for opt in options:
            item = rumps.MenuItem(opt, callback=self._make_setter(attr, opt))
            item.state = 1 if getattr(self.cfg, attr) == opt else 0
            parent.add(item)
        return parent

    def _make_setter(self, attr: str, value: str):
        def cb(sender: rumps.MenuItem) -> None:
            setattr(self.cfg, attr, value)
            self.cfg.save()
            for sib in sender.parent.values():
                sib.state = 1 if sib.title == value else 0
            if attr == "trigger_mode":
                self._start_hotkey()  # mode is captured in the listener
        return cb

    def _tick(self, _) -> None:
        with self._lock:
            status, transcript = self._status, self._transcript
        self.title = {"idle": "🎙︎", "recording": "🔴", "transcribing": "✍︎",
                      "confirming": "❓", "sending": "⏎"}.get(status, "🎙︎")
        self.status_item.title = f"Status: {status}"
        self.transcript_item.title = transcript[:60] or "—"

    def _set(self, status: str | None = None, transcript: str | None = None) -> None:
        with self._lock:
            if status is not None:
                self._status = status
            if transcript is not None:
                self._transcript = transcript

    # ---- hotkey ---------------------------------------------------------
    def _start_hotkey(self) -> None:
        if self._hk is not None:
            self._hk.stop()
        self._hk = HotkeyListener(
            self.cfg.hotkey,
            self.cfg.trigger_mode,
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
        """Capture frames until stop. Returns raw int16 PCM bytes."""
        eos = EndOfSpeech(self.cfg.vad_level, self.cfg.silence_ms)
        buf = bytearray()
        max_bytes = max_s * SAMPLE_RATE * 2  # int16 = 2 bytes/sample
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
        except Exception as exc:  # keep the daemon alive on any failure
            self._set(transcript=f"error: {exc}")
        finally:
            self._set(status="idle")

    def _confirm(self, text: str) -> str:
        mode = self.cfg.confirm_mode
        if mode == "paste_only":
            return "insert"
        if mode == "overlay":
            return confirm.confirm_overlay(text)
        # voice: short listen window, ends early on silence
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
