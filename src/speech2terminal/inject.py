"""Inject text into the terminal: paste-into-focused, or local tmux send-keys.

Keystrokes are posted via Quartz CGEvent (HID level) rather than pynput. pynput
synthesizes keys through Carbon/HIToolbox Text Services, which on macOS
Sonoma+ assert main-thread-only and SIGTRAP when called from our worker thread.
CGEvent uses fixed virtual keycodes (no keyboard-layout lookup) and is
thread-safe.
"""

from __future__ import annotations

import subprocess
import time

import pyperclip
from Quartz import (
    CGEventCreateKeyboardEvent, CGEventPost, CGEventSetFlags,
    kCGEventFlagMaskCommand, kCGHIDEventTap,
)

_KC_V = 9       # virtual keycode for "v"
_KC_RETURN = 36


def _post_key(keycode: int, cmd: bool = False) -> None:
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    if cmd:
        CGEventSetFlags(down, kCGEventFlagMaskCommand)
        CGEventSetFlags(up, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def paste(text: str, run: bool) -> None:
    """Clipboard + Cmd+V into the focused window, optional Enter."""
    pyperclip.copy(text)
    time.sleep(0.05)  # let the pasteboard settle before Cmd+V
    _post_key(_KC_V, cmd=True)
    if run:
        time.sleep(0.05)
        _post_key(_KC_RETURN)


def tmux_available() -> bool:
    try:
        subprocess.run(["tmux", "list-sessions"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def tmux_send(text: str, run: bool, target: str) -> None:
    """Send literal text to a local tmux pane, optional Enter."""
    cmd = ["tmux", "send-keys"]
    if target:
        cmd += ["-t", target]
    cmd += ["-l", text]  # -l = literal
    subprocess.run(cmd, check=True)
    if run:
        enter = ["tmux", "send-keys"]
        if target:
            enter += ["-t", target]
        enter += ["Enter"]
        subprocess.run(enter, check=True)


def send(text: str, run: bool, cfg) -> None:  # noqa: ANN001
    if cfg.target == "tmux" and tmux_available():
        tmux_send(text, run, cfg.tmux_target)
    else:
        paste(text, run)
