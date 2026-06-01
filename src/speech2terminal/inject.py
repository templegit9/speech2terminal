"""Inject text into the terminal: paste-into-focused, or local tmux send-keys."""

from __future__ import annotations

import subprocess
import time

import pyperclip
from pynput.keyboard import Controller, Key

_kbd = Controller()


def paste(text: str, run: bool) -> None:
    """Set clipboard, send Cmd+V into the focused window, optional Enter."""
    pyperclip.copy(text)
    time.sleep(0.05)  # let the pasteboard settle before Cmd+V
    with _kbd.pressed(Key.cmd):
        _kbd.press("v")
        _kbd.release("v")
    if run:
        time.sleep(0.05)
        _kbd.press(Key.enter)
        _kbd.release(Key.enter)


def tmux_available() -> bool:
    try:
        subprocess.run(
            ["tmux", "list-sessions"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def tmux_send(text: str, run: bool, target: str) -> None:
    """Send literal text to a local tmux pane, optional Enter."""
    cmd = ["tmux", "send-keys"]
    if target:
        cmd += ["-t", target]
    cmd += ["-l", text]  # -l = literal, no key-name interpretation
    subprocess.run(cmd, check=True)
    if run:
        enter = ["tmux", "send-keys"]
        if target:
            enter += ["-t", target]
        enter += ["Enter"]
        subprocess.run(enter, check=True)


def send(text: str, run: bool, cfg) -> None:  # noqa: ANN001
    """Dispatch to the configured target, falling back to paste."""
    if cfg.target == "tmux" and tmux_available():
        tmux_send(text, run, cfg.tmux_target)
    else:
        paste(text, run)
