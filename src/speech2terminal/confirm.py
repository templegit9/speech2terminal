"""Confirmation modes: voice 'yes', paste-only, review overlay.

Each returns a decision string: "run" | "insert" | "discard".
  run     -> inject text and press Enter
  insert  -> inject text only (you press Enter)
  discard -> drop it
"""

from __future__ import annotations

import subprocess
from typing import Callable

YES = {"yes", "yeah", "yep", "yup", "yer", "run", "go", "send", "sure", "ok", "okay", "do it"}
NO = {"no", "nope", "cancel", "stop", "discard", "nah"}


def _normalize(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum() or c.isspace()).strip()


def confirm_voice(
    text: str,
    record_clip: Callable[[], bytes],
    transcribe_fn: Callable[[bytes], str],
) -> str:
    """Listen for a spoken yes/no. Timeout or unclear -> discard (safe)."""
    pcm = record_clip()
    said = _normalize(transcribe_fn(pcm))
    words = set(said.split())
    if words & YES or said in YES:
        return "run"
    return "discard"


def confirm_overlay(text: str) -> str:
    """Modal AppleScript dialog — safe from any thread. Run / Insert / Cancel."""
    script = (
        'display dialog {q} with title "speech2terminal" '
        'buttons {{"Cancel", "Insert", "Run"}} default button "Run"'
    ).format(q=_applescript_quote(text))
    proc = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True
    )
    if proc.returncode != 0:  # Cancel / closed
        return "discard"
    out = proc.stdout
    if "Insert" in out:
        return "insert"
    if "Run" in out:
        return "run"
    return "discard"


def _applescript_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
