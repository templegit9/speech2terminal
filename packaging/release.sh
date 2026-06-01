#!/usr/bin/env bash
# One-command release: build -> sign -> notarize -> staple -> zip -> GitHub
# release -> bump the Homebrew cask in the tap repo.
#
# Prereqs (one-time):
#   xcrun notarytool store-credentials s2t-notary \
#       --apple-id <you@example.com> --team-id PVRL9W627Q \
#       --password <app-specific-password>
#
# Usage: packaging/release.sh [VERSION]   (defaults to version in pyproject.toml)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2)}"
APP="dist/speech2terminal.app"
ZIP="dist/speech2terminal-$VERSION.zip"
REPO="templegit9/speech2terminal"
TAP_REPO="templegit9/homebrew-speech2terminal"
NOTARY_PROFILE="${NOTARY_PROFILE:-s2t-notary}"
CASK_PATH="Casks/speech2terminal.rb"

echo "==> [1/7] build"
( cd packaging && rm -rf build && pyinstaller --noconfirm \
    --distpath ../dist --workpath ./build speech2terminal.spec >/tmp/pyi_release.log 2>&1 ) \
  || { echo "build failed, see /tmp/pyi_release.log"; exit 1; }

echo "==> [2/7] sign"
bash packaging/sign.sh "$APP" >/dev/null

echo "==> [3/7] zip for notarization"
rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"

echo "==> [4/7] notarize (waits for Apple)"
xcrun notarytool submit "$ZIP" --keychain-profile "$NOTARY_PROFILE" --wait

echo "==> [5/7] staple + re-zip"
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"
SHA="$(shasum -a 256 "$ZIP" | awk '{print $1}')"
echo "    sha256=$SHA"

echo "==> [6/7] GitHub release v$VERSION"
if gh release view "v$VERSION" -R "$REPO" >/dev/null 2>&1; then
  gh release upload "v$VERSION" "$ZIP" -R "$REPO" --clobber
else
  gh release create "v$VERSION" "$ZIP" -R "$REPO" \
    --title "v$VERSION" --notes "speech2terminal $VERSION (signed + notarized)"
fi

echo "==> [7/7] bump cask in $TAP_REPO"
TAP_DIR="$(mktemp -d)"
gh repo clone "$TAP_REPO" "$TAP_DIR" -- -q
mkdir -p "$TAP_DIR/Casks"
cat > "$TAP_DIR/$CASK_PATH" <<EOF
cask "speech2terminal" do
  version "$VERSION"
  sha256 "$SHA"

  url "https://github.com/$REPO/releases/download/v#{version}/speech2terminal-#{version}.zip"
  name "speech2terminal"
  desc "Voice-driven terminal dictation (local MLX Whisper)"
  homepage "https://github.com/$REPO"

  depends_on macos: ">= :ventura"

  app "speech2terminal.app"

  zap trash: [
    "~/.config/speech2terminal",
    "~/Library/Caches/com.oginni.speech2terminal",
  ]
end
EOF
git -C "$TAP_DIR" add "$CASK_PATH"
git -C "$TAP_DIR" commit -q -m "speech2terminal $VERSION" || echo "  (no cask change)"
git -C "$TAP_DIR" push -q
rm -rf "$TAP_DIR"

echo "DONE. Install: brew install --cask templegit9/speech2terminal/speech2terminal"
