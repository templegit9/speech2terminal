"""Config load/save. TOML at ~/.config/speech2terminal/config.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

CONFIG_DIR = Path(os.path.expanduser("~/.config/speech2terminal"))
CONFIG_PATH = CONFIG_DIR / "config.toml"

# Audio constants — 16 kHz mono int16 satisfies both Whisper and webrtcvad.
SAMPLE_RATE = 16000
FRAME_MS = 30  # webrtcvad accepts 10/20/30 ms frames


@dataclass
class Config:
    # trigger: "push_to_talk" | "long_press" | "auto_silence" | "toggle"
    trigger_mode: str = "push_to_talk"
    # confirm: "voice" | "paste_only" | "overlay"
    confirm_mode: str = "voice"
    # target: "paste" | "tmux"
    target: str = "paste"

    # Hotkey spec: optional modifiers + one main key, "+"-joined, lowercase.
    # Modifiers: ctrl, alt (Option), shift, cmd. Main key: a letter, "space",
    # "f1".."f12", or a side key like "alt_r"/"cmd_r". E.g. "ctrl+alt+space".
    hotkey: str = "f9"
    # For trigger_mode == "long_press": hold this long (ms) before it activates.
    long_press_ms: int = 400

    model: str = "mlx-community/whisper-large-v3-turbo"

    # End-of-speech: this many ms of non-speech ends a clip (auto_silence + voice).
    silence_ms: int = 1500
    # VAD aggressiveness 0..3 (3 = most aggressive at filtering non-speech).
    vad_level: int = 2
    # Max clip length guard (seconds).
    max_record_s: int = 60
    # Voice-confirm listen window (seconds).
    confirm_listen_s: int = 4

    # Local tmux target ("session", "session:window.pane"). Used when target=tmux.
    tmux_target: str = ""

    # Append Enter after injecting (only when the command is confirmed to run).
    press_enter_on_run: bool = True

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(_to_toml(self))


def _to_toml(cfg: Config) -> str:
    lines = []
    for k, v in asdict(cfg).items():
        if isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        else:
            lines.append(f"{k} = {v}")
    return "\n".join(lines) + "\n"


def load() -> Config:
    if not CONFIG_PATH.exists():
        cfg = Config()
        cfg.save()
        return cfg
    data = tomllib.loads(CONFIG_PATH.read_text())
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in data.items() if k in known})
