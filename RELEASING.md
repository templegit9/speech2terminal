# Releasing speech2terminal

Ships a **signed + notarized** `speech2terminal.app` via a Homebrew **cask**.

Install target for users:
```sh
brew install --cask templegit9/speech2terminal/speech2terminal
```

## One-time setup

1. **Developer ID Application cert** — already present in this keychain:
   `Developer ID Application: Oluyinka Oginni (PVRL9W627Q)` (Team `PVRL9W627Q`).
   Override via `SIGN_IDENTITY=...` if it changes.

2. **Notary credential** — create an app-specific password at
   <https://appleid.apple.com> (Sign-In & Security → App-Specific Passwords),
   then store it once (run this yourself; it holds a secret):
   ```sh
   xcrun notarytool store-credentials s2t-notary \
       --apple-id "oluyinkaoginni@gmail.com" \
       --team-id PVRL9W627Q \
       --password "<app-specific-password>"
   ```
   Override the profile name via `NOTARY_PROFILE=...`.

3. **Tap repo** — `templegit9/homebrew-speech2terminal` must exist (empty is
   fine). `release.sh` writes `Casks/speech2terminal.rb` into it.

## Cut a release

```sh
# bump version in pyproject.toml + packaging/speech2terminal.spec, then:
packaging/release.sh            # uses version from pyproject.toml
# or: packaging/release.sh 0.2.0
```

`release.sh` runs: build → sign → notarize (waits) → staple → re-zip →
GitHub release on `templegit9/speech2terminal` → rewrite + push the cask.

## Build / validate without releasing

```sh
# build only
( cd packaging && pyinstaller --noconfirm --distpath ../dist --workpath ./build speech2terminal.spec )
# sign only
packaging/sign.sh dist/speech2terminal.app
# verify the frozen native stack runs (mlx Metal / scipy / numba):
dist/speech2terminal.app/Contents/MacOS/speech2terminal --selftest /tmp/s2t.raw
# check signature + notarization
codesign --verify --strict --deep --verbose=2 dist/speech2terminal.app
xcrun stapler validate dist/speech2terminal.app   # only after notarize+staple
spctl -a -vvv -t install dist/speech2terminal.app # Gatekeeper assessment
```

## Notes / gotchas

- **torch is intentionally excluded** from the bundle (verified unused on the
  MLX inference path). Do not "fix" the pip warning by adding it back — it adds
  ~hundreds of MB of native code that must be signed for nothing.
- **numba is required** (imported at `mlx_whisper/timing.py` load time) and uses
  an LLVM JIT — hence `allow-jit` + `allow-unsigned-executable-memory` in
  `entitlements.plist`. Removing those entitlements will crash the signed app.
- **Mic / Accessibility / Input Monitoring** are TCC runtime grants, not
  entitlements. Because the app is stably signed, grants persist across updates.
- First launch downloads the Whisper model (~1.5 GB) to `~/.cache/huggingface`.
