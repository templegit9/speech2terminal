"""Speech-to-text via local MLX Whisper (Apple Silicon)."""

from __future__ import annotations

import mlx_whisper

from .audio import pcm_to_float32


def transcribe(pcm: bytes, model: str) -> str:
    """int16 PCM bytes -> transcribed text. Empty string if nothing heard."""
    if not pcm:
        return ""
    audio = pcm_to_float32(pcm)
    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=model,
        fp16=True,
    )
    return (result.get("text") or "").strip()
