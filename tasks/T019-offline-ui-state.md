---
id: T019
title: Add explicit offline UI state
status: done
depends_on: [T016]
area: android
---

# Goal

Detect connectivity and display downloaded-data timestamps and unsupported-action explanations.

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

- [x] Offline search remains usable.
- [x] Online-only actions are disabled safely.
- [x] UI tests cover offline state.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test
./gradlew connectedDebugAndroidTest
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
