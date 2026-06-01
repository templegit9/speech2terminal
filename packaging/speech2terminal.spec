# PyInstaller spec for speech2terminal.app (menu-bar, hardened-runtime ready).
# Build:  pyinstaller --noconfirm packaging/speech2terminal.spec
# Output: dist/speech2terminal.app
#
# torch/sympy/networkx/mpmath are excluded — verified unused on the MLX
# inference path, and the heaviest native code to sign/notarize.

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

VERSION = "0.1.0"

datas, binaries, hiddenimports = [], [], []

# Whole-package collection: grabs dylibs, the Metal lib, and data files.
for pkg in [
    "mlx", "mlx_whisper", "sounddevice", "rumps", "pynput",
    "huggingface_hub", "tiktoken", "certifi",
]:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# sounddevice's bundled libportaudio.dylib lives in this data-only dir.
datas += collect_data_files("_sounddevice_data")

# Heavy native pkgs have official hooks; pull their submodules explicitly too.
for pkg in ["numba", "llvmlite", "scipy"]:
    hiddenimports += collect_submodules(pkg)

hiddenimports += ["webrtcvad", "pyperclip", "speech2terminal", "speech2terminal.app"]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "torch", "sympy", "networkx", "mpmath",
        "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
        "matplotlib", "pandas", "IPython", "pytest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="speech2terminal",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # windowed; LSUIElement keeps it menu-bar-only
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="speech2terminal",
)

app = BUNDLE(
    coll,
    name="speech2terminal.app",
    icon=None,
    bundle_identifier="com.oluyinka.speech2terminal",
    version=VERSION,
    info_plist={
        "LSUIElement": True,
        "LSMinimumSystemVersion": "13.0",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSMicrophoneUsageDescription":
            "speech2terminal transcribes your voice into terminal commands.",
        "NSHumanReadableCopyright": "© 2026 Oluyinka Oginni",
    },
)
