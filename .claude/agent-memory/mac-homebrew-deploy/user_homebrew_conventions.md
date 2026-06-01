---
name: user-homebrew-conventions
description: templegit9's macOS Homebrew distribution conventions — identity, tap, bundle-id scheme, signing/notarization facts derived from the MeetingIntro reference app
metadata:
  type: reference
---

User's verified macOS Homebrew distribution facts (from MeetingIntro reference repo, inspected 2026-05-31):

- **GitHub user:** `templegit9`
- **Apple Team ID:** `PVRL9W627Q`
- **Developer ID:** "Developer ID Application: Oluyinka Oginni (PVRL9W627Q)"
- **Tap repo:** `templegit9/homebrew-tap` cloned at `~/code/homebrew-tap`. SHARED across apps (README says "MeetingIntro and other apps"); each app = one `Casks/<app>.rb`. Tap lives OUTSIDE any app repo.
- **Install form:** `brew install --cask templegit9/tap/<app-lowercase>` (cask, not formula).
- **Bundle-id scheme:** `com.oluyinka.<AppName>` (note: `oluyinka`, not the GitHub handle). bundleIdPrefix `com.oluyinka` in project.yml.
- **Secrets file:** `.env.release` at app repo root, gitignored. Keys: `<APP>_SIGN_IDENTITY`, `<APP>_TEAM_ID`, `APPLE_ID`, `APPLE_APP_PASSWORD`, `TAP_REPO_PATH`. Env-var names are app-prefixed (e.g. `MEETINGINTRO_SIGN_IDENTITY`).
- **Notary auth:** uses `--apple-id / --team-id / --password` (app-specific password) directly in notarytool, NOT a stored `--keychain-profile`.

IMPORTANT correction to the orchestrator's baseline assumption: MeetingIntro **DOES notarize + staple** (full Developer ID + hardened runtime + notary + stapler pipeline). It does NOT skip notarization. The shipped cask has no postflight/quarantine/livecheck stanzas — clean install works because the artifact is genuinely notarized & stapled. See [[meetingintro-pipeline-shape]].

Gotchas observed in the live MeetingIntro repo:
- `scripts/release.sh` actually DOES edit+commit+push `project.yml` MARKETING_VERSION on each release (lines 49-56), contradicting RELEASING.md's claim that project.yml is never edited. Both the flag and the file get set.
- Stale/leftover artifacts (`MeetingIntro.dmg`, `MeetingIntro_Release*.zip`, `MeetingIntro_Release/` dir) sit in the repo root from earlier manual experiments; `.gitignore` covers them.
