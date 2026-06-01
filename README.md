# speech2terminal

Talk to your terminal. Hit a hotkey, speak a command, watch it transcribe,
confirm it, and it lands in the focused terminal — ready to run. Runs fully
local on Apple Silicon (MLX Whisper); no audio leaves your Mac.

## How it works

1. **Trigger** a dictation with your hotkey (default `F9`). Three modes:
   - `push_to_talk` — hold the key while speaking, release when done.
   - `auto_silence` — tap once; it stops when you go quiet (VAD).
   - `toggle` — tap to start, tap to stop.
2. **Transcribe** locally with MLX Whisper (~1–2 s on M-series).
3. **Confirm**. Three modes:
   - `voice` — it listens for a spoken *"yes"* → runs; silence/"no" → discards.
   - `paste_only` — pastes the text without Enter; you review and run it.
   - `overlay` — a dialog: Run / Insert / Cancel.
4. **Inject** into the focused terminal via clipboard paste (works in Ghostty,
   iTerm, Terminal, and *inside* a remote SSH/tmux session), or via local
   `tmux send-keys` when `target = "tmux"`.

## Install

```sh
brew install portaudio python@3.12 tmux        # tmux only needed for tmux target
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```sh
speech2terminal        # menu-bar app; the 🎙︎ icon shows status
```

First run downloads the Whisper model (~1.5 GB) once.

## macOS permissions (one-time)

Grant these to the app launching it (your terminal, or `python3.12`) in
**System Settings → Privacy & Security**:

- **Microphone** — audio capture.
- **Input Monitoring** — global hotkey capture.
- **Accessibility** — sending Cmd+V / Enter to other apps.

If the hotkey or paste does nothing, it's almost always a missing permission
here — toggle it off/on and restart the app.

## Config

Edit `~/.config/speech2terminal/config.toml` (auto-created; see
`config.example.toml`). Trigger / Confirm / Target are also switchable live
from the menu-bar menu.

## Scope notes

- Transcript appears right after each clip (chunked), not as live streaming words.
- `tmux` target is **local** tmux only; remote tmux over SSH is handled by paste.
