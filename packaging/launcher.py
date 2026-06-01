"""py/PyInstaller entry point. Tiny so the frozen graph starts from a clean root.

`--selftest [raw_pcm_path]` exercises the full native stack (mlx Metal lib,
scipy, numba, sounddevice import) inside the frozen bundle without needing the
GUI/mic — used to validate a built .app before signing/release.
"""

import multiprocessing
import sys

# Frozen apps using spawn-based multiprocessing (numba/scipy) must call this
# before anything else, or child processes relaunch the whole menu-bar app.
multiprocessing.freeze_support()


def _selftest(args) -> int:
    import sounddevice  # noqa: F401  (forces portaudio dylib load)
    from speech2terminal import inject  # noqa: F401  (forces Quartz load)
    from speech2terminal import stt

    path = args[0] if args else None
    if path:
        pcm = open(path, "rb").read()
    else:
        pcm = b"\x00\x00" * 16000  # 1s silence — still loads model + Metal
    text = stt.transcribe(pcm, "mlx-community/whisper-large-v3-turbo")
    print(f"SELFTEST OK transcript={text!r}")
    return 0


def main() -> None:
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        sys.exit(_selftest(sys.argv[i + 1:]))
    from speech2terminal.app import main as app_main
    app_main()


if __name__ == "__main__":
    main()
