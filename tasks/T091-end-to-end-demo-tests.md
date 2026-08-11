---
id: T091
title: Add end-to-end demo tests
status: done
depends_on: [T061, T071, T080, T090]
area: quality
---

# Goal

Automate the key HCMC online flow and offline package flow; document manual GPS/microphone checks.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/12-progress-tracker.md`

# Scope

Implement only the goal and acceptance criteria in this file.

# Out of scope

- Future tasks.
- Unrequested refactors.
- New product behavior not present in context files.

# Acceptance criteria

- [x] Food query reaches navigation.
- [x] Narration displays source.
- [x] Offline search works after network disable.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew connectedDebugAndroidTest
pytest
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.

# Implementation and completion record (2026-08-11)

The deterministic Android harness uses the existing production path from an
Explore food query through HomeViewModel, active-package Room v4 FTS, Compose
navigation, the Room POI-detail repository, sourced narration UI and the
external-navigation boundary. It imports the real bundled HCMC package into an
isolated in-memory database and adds only synthetic food/narration fixture rows.
It also observes an Online-to-Offline app-state transition before repeating the
local query without diacritics. No Firebase, backend, provider or model call is
part of either instrumentation scenario.

Focused T091 instrumentation passed 2/2. The full connected suite passed
143/143 with zero failures or skips; the Android JVM aggregate and
`lintDebug testDebugUnitTest assembleDebug` passed. Backend `pytest` passed
816/816 against the healthy local PostGIS service. The first literal `pytest`
attempt failed because the executable was absent from shell `PATH`; rerunning
the same command with the repository virtualenv on `PATH` and local environment
loaded passed. The first full connected attempt selected an incomplete VS Code
JRE without `jlink`; after stopping the stale Gradle daemon, the required
Android Studio JDK 21 run passed.

`docs/testing/T091-demo-validation.md` contains the accepted coverage matrix and
the foreground-GPS, microphone, actual-network-isolation and external-map
runbook. User-supplied physical-device validation completed that runbook:
foreground GPS passed, microphone behavior passed, actual physical network
isolation passed, offline cold relaunch passed, the external-map boundary
passed, and connectivity cleanup/network restoration passed. The repository
was unchanged during the manual validation.

Final evidence is focused E2E 2/2, connected Android 143/143, Android JVM 270,
and backend pytest 816/816. With the device-owned evidence recorded without
private values, every acceptance criterion is complete and T091 is `done`.
