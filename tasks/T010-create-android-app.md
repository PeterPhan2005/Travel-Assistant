---
id: T010
title: Create Android Compose app
status: todo
depends_on: [T000, T001, T002]
area: android
---

# Goal

Create the Kotlin Android application using Jetpack Compose and a single activity.

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

- [ ] Debug app builds.
- [ ] App launches on emulator/device.
- [ ] Package name is documented.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew assembleDebug
./gradlew test
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
