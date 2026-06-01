"""Global hotkey listener: modifier combos + long-press, across 4 trigger modes.

Spec format (config.hotkey): optional modifiers + one main key, "+"-joined.
  "f9"  ·  "ctrl+alt+space"  ·  "cmd_r"  ·  "shift+f12"
Modifiers: ctrl, alt, shift, cmd. Main: letter / space / f1..f12 / side key
(alt_r, cmd_r, ...).

Trigger modes:
  push_to_talk — press (mods held) starts, release stops
  long_press   — hold past long_press_ms to start, release stops; quick tap ignored
  toggle       — press flips recording on/off
  auto_silence — press starts; VAD stops (handled by the app)
"""

from __future__ import annotations

import threading
from typing import Callable

from pynput import keyboard

_MOD_OF = {
    keyboard.Key.ctrl: "ctrl", keyboard.Key.ctrl_l: "ctrl", keyboard.Key.ctrl_r: "ctrl",
    keyboard.Key.alt: "alt", keyboard.Key.alt_l: "alt", keyboard.Key.alt_r: "alt",
    keyboard.Key.shift: "shift", keyboard.Key.shift_l: "shift", keyboard.Key.shift_r: "shift",
    keyboard.Key.cmd: "cmd", keyboard.Key.cmd_l: "cmd", keyboard.Key.cmd_r: "cmd",
}
_MOD_NAMES = {"ctrl", "alt", "shift", "cmd"}


def parse_key(name: str):
    name = name.strip().lower()
    special = getattr(keyboard.Key, name, None)
    if special is not None:
        return special
    return keyboard.KeyCode.from_char(name)


def parse_spec(spec: str):
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    mods = {p for p in parts if p in _MOD_NAMES}
    mains = [p for p in parts if p not in _MOD_NAMES]
    main = mains[-1] if mains else (parts[-1] if parts else "f9")
    return mods, parse_key(main)


def _matches(key, target) -> bool:
    if key == target:
        return True
    kc = getattr(key, "char", None)
    tc = getattr(target, "char", None)
    return kc is not None and kc == tc


def format_spec(mods, main_name: str) -> str:
    order = ["ctrl", "alt", "shift", "cmd"]
    parts = [m for m in order if m in mods] + [main_name]
    return "+".join(parts)


class HotkeyListener:
    def __init__(
        self,
        hotkey: str,
        mode: str,
        long_press_ms: int,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        is_recording: Callable[[], bool],
    ) -> None:
        self._req_mods, self._main = parse_spec(hotkey)
        self._mode = mode
        self._long_s = max(0.0, long_press_ms / 1000.0)
        self._on_start = on_start
        self._on_stop = on_stop
        self._is_recording = is_recording

        self._held_mods: set[str] = set()
        self._active = False   # main key engaged (debounces auto-repeat)
        self._started = False  # recording actually began (long_press)
        self._timer: threading.Timer | None = None
        self._listener: keyboard.Listener | None = None

    def _mods_ok(self) -> bool:
        return self._req_mods.issubset(self._held_mods)

    def _on_press(self, key) -> None:
        mod = _MOD_OF.get(key)
        if mod:
            self._held_mods.add(mod)
        if not _matches(key, self._main) or self._active:
            return
        if not self._mods_ok():
            return
        self._active = True
        if self._mode == "toggle":
            (self._on_stop if self._is_recording() else self._on_start)()
        elif self._mode == "long_press":
            self._started = False
            self._timer = threading.Timer(self._long_s, self._long_fire)
            self._timer.start()
        else:  # push_to_talk, auto_silence
            self._on_start()

    def _long_fire(self) -> None:
        if self._active:
            self._started = True
            self._on_start()

    def _on_release(self, key) -> None:
        mod = _MOD_OF.get(key)
        if mod:
            self._held_mods.discard(mod)
        if not _matches(key, self._main):
            return
        was_active = self._active
        self._active = False
        if self._mode == "long_press":
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if self._started:
                self._started = False
                self._on_stop()
        elif self._mode == "push_to_talk":
            if was_active:
                self._on_stop()

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
