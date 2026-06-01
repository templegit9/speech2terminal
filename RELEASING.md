# Releasing speech2terminal

Ships a **signed + notarized** `speech2terminal.app` via a Homebrew **cask** —
same recipe as MeetingIntro, shared tap, only the build step differs (PyInstaller
instead of xcodebuild).

Install target for users:
```sh
brew install --cask templegit9/tap/speech2terminal
```

## One-time setup

1. **Developer ID Application cert** — present in this keychain:
   `Developer ID Application: Oluyinka Oginni (PVRL9W627Q)` (Team `PVRL9W627Q`).

2. **App-specific password** — create one at <https://appleid.apple.com>
   (Sign-In and Security → App-Specific Passwords).

3. **`.env.release`** — copy `.env.release.example` to `.env.release` (gitignored)
   and fill in:
   ```sh
   SPEECH2TERMINAL_SIGN_IDENTITY="Developer ID Application: Oluyinka Oginni (PVRL9W627Q)"
   SPEECH2TERMINAL_TEAM_ID="PVRL9W627Q"
   APPLE_ID="oluyinkaoginni@gmail.com"
   APPLE_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
   TAP_REPO_PATH="/Users/oluyinkaoginni/code/homebrew-tap"
   ```

4. **Shared tap** — `templegit9/homebrew-tap`, cloned locally at the
   `TAP_REPO_PATH` above (it already holds the MeetingIntro cask). `release.sh`
   writes `Casks/speech2terminal.rb` into it.

## Cut a release

```sh
scripts/release.sh 0.1.0
```

Runs: bump version → build (PyInstaller) → deep-sign → notarize (waits) →
staple → re-zip → GitHub release on `templegit9/speech2terminal` → rewrite +
push the cask in the shared tap.

## Build / validate without releasing

```sh
source .venv/bin/activate
( cd packaging && pyinstaller --noconfirm --distpath ../dist --workpath ./build speech2terminal.spec )
packaging/sign.sh dist/speech2terminal.app
# verify the frozen native stack runs (mlx Metal / scipy / numba):
dist/speech2terminal.app/Contents/MacOS/speech2terminal --selftest /tmp/s2t.raw
codesign --verify --strict --deep --verbose=2 dist/speech2terminal.app
xcrun stapler validate dist/speech2terminal.app   # only after notarize+staple
spctl -a -vvv -t install dist/speech2terminal.app # Gatekeeper assessment
```

## Notes / gotchas

- **torch is intentionally excluded** from the bundle (verified unused on the
  MLX inference path). Don't "fix" the pip warning by re-adding it — it's
  hundreds of MB of native code that must be signed for nothing.
- **numba is required** (imported at `mlx_whisper/timing.py` load time) and uses
  an LLVM JIT — hence `allow-jit` + `allow-unsigned-executable-memory` in
  `packaging/entitlements.plist`. Removing them crashes the signed app.
- **Mic / Accessibility / Input Monitoring** are TCC runtime grants, not
  entitlements. Stable signing makes grants persist across updates.
- First launch downloads the Whisper model (~1.5 GB) to `~/.cache/huggingface`.
