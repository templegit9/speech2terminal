"""Global hotkey listener implementing all 3 trigger modes.

Single key only (e.g. "f9", "f12", "space", "a"). Push-to-talk needs raw
press/release, so we use a low-level Listener and match the configured key
rather than pynput's combo-only GlobalHotKeys.
"""

from __future__ import annotations

from typing import Callable

from pynput import keyboard


def _parse(name: str):
    name = name.strip().lower()
    special = getattr(keyboard.Key, name, None)
    if special is not None:
        return special
    return keyboard.KeyCode.from_char(name)


def _matches(key, target) -> bool:
    if key == target:
        return True
    # KeyCode equality can differ by vk; compare char when available.
    kc = getattr(key, "char", None)
    tc = getattr(target, "char", None)
    return kc is not None and kc == tc


class HotkeyListener:
    """Fires on_start / on_stop callbacks per trigger mode.

    - push_to_talk: press -> on_start, release -> on_stop
    - toggle:       press -> on_start if idle else on_stop (uses is_recording)
    - auto_silence: press -> on_start (stop is VAD-driven, not key-driven)
    """

    def __init__(
        self,
        hotkey: str,
        mode: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        is_recording: Callable[[], bool],
    ) -> None:
        self._target = _parse(hotkey)
        self._mode = mode
        self._on_start = on_start
        self._on_stop = on_stop
        self._is_recording = is_recording
        self._held = False  # debounce auto-repeat on press-hold
        self._listener: keyboard.Listener | None = None

    def _on_press(self, key) -> None:
        if not _matches(key, self._target) or self._held:
            return
        self._held = True
        if self._mode == "toggle":
            (self._on_stop if self._is_recording() else self._on_start)()
        else:  # push_to_talk, auto_silence
            self._on_start()

    def _on_release(self, key) -> None:
        if not _matches(key, self._target):
            return
        self._held = False
        if self._mode == "push_to_talk":
            self._on_stop()

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
