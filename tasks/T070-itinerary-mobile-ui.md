---
id: T070
title: Implement itinerary generation UI
status: done
depends_on: [T012, T045, T048]
area: android
---

# Goal

Create input form and timeline result UI for one-day itinerary.

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

- [x] Required constraints are validated.
- [x] Warnings are visible.
- [x] User must explicitly save.
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

# Completion record

- The Android form, strict local validation, typed state machine, timeline UI,
  warning rendering, lifecycle cancellation and explicit-save boundary are
  complete.
- Production generation was deliberately not fabricated. Real structured
  generation is not claimed as part of T070 and its transport is assigned to
  T062.
- Persistence, CRUD and synchronization remain assigned to T071.
- T070 completed as an Android UI and boundary task.
