#!/usr/bin/env bash
# scripts/release.sh — cut a notarized, Homebrew-installable release of speech2terminal.
# Mirrors the MeetingIntro recipe; only the build step differs (PyInstaller, not xcodebuild).
#
# What it does, in order:
#   1. Bumps version in pyproject.toml + packaging/speech2terminal.spec, commits, pushes
#   2. Builds dist/speech2terminal.app with PyInstaller
#   3. Deep-signs with Developer ID + hardened runtime + entitlements
#   4. Zips and submits to Apple for notarization, then staples the ticket
#   5. Computes SHA-256, creates a GitHub release with the zip attached
#   6. Updates Casks/speech2terminal.rb in templegit9/homebrew-tap and pushes
#
# Required environment (load from .env.release; see RELEASING.md):
#   SPEECH2TERMINAL_SIGN_IDENTITY   e.g. "Developer ID Application: Your Name (TEAMID)"
#   SPEECH2TERMINAL_TEAM_ID         your 10-char Apple Team ID
#   APPLE_ID                        Apple ID email used for notarization
#   APPLE_APP_PASSWORD              app-specific password (appleid.apple.com → Sign-In and Security)
#   TAP_REPO_PATH                   local path to a clone of templegit9/homebrew-tap
#
# Required tools: python venv (.venv), pyinstaller, codesign, ditto, xcrun notarytool, gh, shasum.
#
# Usage:
#   scripts/release.sh 0.1.0

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <version>   (e.g. $0 0.1.0)" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Load secrets if .env.release exists (gitignored).
if [[ -f .env.release ]]; then
  set -a; source .env.release; set +a
fi

: "${SPEECH2TERMINAL_SIGN_IDENTITY:?set in .env.release}"
: "${SPEECH2TERMINAL_TEAM_ID:?set in .env.release}"
: "${APPLE_ID:?set in .env.release}"
: "${APPLE_APP_PASSWORD:?set in .env.release}"
: "${TAP_REPO_PATH:?set in .env.release}"

APP_PATH="$REPO_ROOT/dist/speech2terminal.app"
ZIP_NAME="speech2terminal-${VERSION}.zip"
ZIP_PATH="$REPO_ROOT/dist/$ZIP_NAME"

echo "▶ Bumping version to $VERSION (pyproject.toml + spec)"
/usr/bin/sed -i '' "s|^version = \".*\"|version = \"$VERSION\"|" "$REPO_ROOT/pyproject.toml"
/usr/bin/sed -i '' "s|^VERSION = \".*\"|VERSION = \"$VERSION\"|" "$REPO_ROOT/packaging/speech2terminal.spec"
git add pyproject.toml packaging/speech2terminal.spec
if ! git diff --cached --quiet; then
  git commit -m "chore: bump version to $VERSION"
  git push origin main
fi

echo "▶ Activating venv + building app bundle (PyInstaller)"
# shellcheck disable=SC1091
source "$REPO_ROOT/.venv/bin/activate"
rm -rf "$REPO_ROOT/dist" "$REPO_ROOT/packaging/build"
( cd "$REPO_ROOT/packaging" && \
    pyinstaller --noconfirm --distpath ../dist --workpath ./build speech2terminal.spec )
[[ -d "$APP_PATH" ]] || { echo "✗ Build did not produce $APP_PATH" >&2; exit 1; }

echo "▶ Signing (Developer ID + hardened runtime + entitlements)"
SIGN_IDENTITY="$SPEECH2TERMINAL_SIGN_IDENTITY" bash "$REPO_ROOT/packaging/sign.sh" "$APP_PATH"

echo "▶ Zipping app for notarization"
rm -f "$ZIP_PATH"
ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"

echo "▶ Submitting to Apple notary service (this can take a few minutes)"
NOTARY_OUT="$(xcrun notarytool submit "$ZIP_PATH" \
  --apple-id "$APPLE_ID" \
  --team-id "$SPEECH2TERMINAL_TEAM_ID" \
  --password "$APPLE_APP_PASSWORD" \
  --wait 2>&1)"
echo "$NOTARY_OUT"

if ! echo "$NOTARY_OUT" | grep -qE "status: Accepted"; then
  SUBMISSION_ID="$(echo "$NOTARY_OUT" | awk '/id: [a-f0-9-]{36}/ {print $2; exit}')"
  echo "✗ Notarization did not succeed. Fetching detailed log:" >&2
  xcrun notarytool log "$SUBMISSION_ID" \
    --apple-id "$APPLE_ID" \
    --team-id "$SPEECH2TERMINAL_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD" >&2 || true
  exit 1
fi

echo "▶ Stapling ticket to .app"
xcrun stapler staple "$APP_PATH"
xcrun stapler validate "$APP_PATH"

echo "▶ Re-zipping stapled app"
rm -f "$ZIP_PATH"
ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"

SHA256="$(shasum -a 256 "$ZIP_PATH" | awk '{print $1}')"
echo "▶ Artifact SHA-256: $SHA256"

echo "▶ Creating GitHub release v$VERSION"
TAG="v$VERSION"
RELEASE_NOTES="## Install

\`\`\`sh
brew install --cask templegit9/tap/speech2terminal
\`\`\`

### Updating

\`\`\`sh
brew upgrade --cask templegit9/tap/speech2terminal
\`\`\`

Signed with Developer ID and notarized by Apple — opens without Gatekeeper warnings.
First launch downloads the Whisper model (~1.5 GB); grant Microphone, Accessibility,
and Input Monitoring in System Settings → Privacy & Security."
git tag -a "$TAG" -m "Release $TAG" 2>/dev/null || true
git push origin "$TAG" 2>/dev/null || true
gh release create "$TAG" "$ZIP_PATH" \
  --title "speech2terminal $VERSION" \
  --notes "$RELEASE_NOTES" \
  || gh release upload "$TAG" "$ZIP_PATH" --clobber

echo "▶ Updating cask in $TAP_REPO_PATH"
CASK_FILE="$TAP_REPO_PATH/Casks/speech2terminal.rb"
mkdir -p "$(dirname "$CASK_FILE")"
cp "$REPO_ROOT/Casks/speech2terminal.rb" "$CASK_FILE"
/usr/bin/sed -i '' \
  -e "s|version \"0.0.0\"|version \"$VERSION\"|" \
  -e "s|sha256 \"0000000000000000000000000000000000000000000000000000000000000000\"|sha256 \"$SHA256\"|" \
  "$CASK_FILE"

( cd "$TAP_REPO_PATH" && \
    git add Casks/speech2terminal.rb && \
    git commit -m "speech2terminal $VERSION" && \
    git push )

echo "✅ Done. Test with: brew install --cask templegit9/tap/speech2terminal"
