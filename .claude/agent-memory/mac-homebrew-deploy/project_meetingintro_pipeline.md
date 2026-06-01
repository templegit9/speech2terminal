---
name: meetingintro-pipeline-shape
description: Concrete shape of the MeetingIntro release pipeline used as the canonical template for the user's other Homebrew apps
metadata:
  type: project
---

MeetingIntro is the canonical reference for replicating Homebrew distribution to the user's other apps.

**Why:** User (templegit9) wants to copy this exact recipe to a different app.
**How to apply:** When setting up a new app, mirror these artifacts, swapping `MeetingIntro`→new app name, `meetingintro`→lowercase cask, and `com.oluyinka.MeetingIntro`→new bundle id.

Locations:
- App repo: `~/Documents/SelfProjects/MeetingIntro` (remote `github.com/templegit9/MeetingIntro`)
- Release script: `~/Documents/SelfProjects/MeetingIntro/scripts/release.sh` (~5.6KB, takes `<version>` arg)
- Runbook: `~/Documents/SelfProjects/MeetingIntro/RELEASING.md`
- Cask template (placeholders): `~/Documents/SelfProjects/MeetingIntro/Casks/meetingintro.rb` (version "0.0.0", sha all-zeros)
- Live cask: `~/code/homebrew-tap/Casks/meetingintro.rb` (currently v2.1.1)

Pipeline = sign (Developer ID) → ditto-zip → notarytool submit --wait (checks `status: Accepted`, dumps log on failure) → stapler staple+validate → RE-zip stapled app → shasum → gh release create (fallback upload --clobber) → cp template cask into tap, sed version+sha, commit+push tap. Hardened runtime on; `CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO`; `OTHER_CODE_SIGN_FLAGS=--timestamp --options runtime`.

No DMG in the cask path (a stray .dmg in repo root is leftover, unused). No postflight/quarantine/livecheck in the cask.
