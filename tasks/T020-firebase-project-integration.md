---
id: T020
title: Integrate Firebase configuration
status: done
depends_on: [T010]
area: android
---

# Goal

Connect the Android app to a Firebase project using a non-secret development configuration process.

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

- [x] Firebase initializes in debug.
- [x] Config-file handling is documented.
- [x] CI does not require committed production secrets.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew assembleDebug
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
