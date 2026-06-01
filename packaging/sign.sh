#!/usr/bin/env bash
# Deep-sign speech2terminal.app for hardened-runtime notarization.
# Signs inside-out: nested Mach-O first, then frameworks, then main exe + bundle.
set -euo pipefail

APP="${1:-dist/speech2terminal.app}"
IDENTITY="${SIGN_IDENTITY:-Developer ID Application: Oluyinka Oginni (PVRL9W627Q)}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENT="$HERE/entitlements.plist"

[ -d "$APP" ] || { echo "no app at $APP"; exit 1; }

echo "==> signing nested dylibs / .so with $IDENTITY"
# .metallib is data (not Mach-O); the bundle resource seal covers it.
find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 \
  | while IFS= read -r -d '' f; do
      codesign --force --timestamp --options runtime -s "$IDENTITY" "$f"
    done

echo "==> signing nested frameworks"
find "$APP/Contents" -type d -name "*.framework" -print0 \
  | while IFS= read -r -d '' fw; do
      codesign --force --timestamp --options runtime -s "$IDENTITY" "$fw"
    done

# Any remaining Mach-O executables under Frameworks (e.g. Python.framework/.../Python)
echo "==> signing remaining mach-o executables"
find "$APP/Contents/Frameworks" -type f -perm +111 -print0 2>/dev/null \
  | while IFS= read -r -d '' f; do
      if file "$f" | grep -q "Mach-O"; then
        codesign --force --timestamp --options runtime -s "$IDENTITY" "$f" || true
      fi
    done

echo "==> signing main executable (with entitlements)"
codesign --force --timestamp --options runtime --entitlements "$ENT" \
  -s "$IDENTITY" "$APP/Contents/MacOS/speech2terminal"

echo "==> signing app bundle (with entitlements)"
codesign --force --timestamp --options runtime --entitlements "$ENT" \
  -s "$IDENTITY" "$APP"

echo "==> verifying"
codesign --verify --strict --deep --verbose=2 "$APP"
echo "OK: signed and verified (notarization still required for distribution)"
