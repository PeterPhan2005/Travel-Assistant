---
id: T022
title: Implement Google authentication
status: done
depends_on: [T020, T021]
area: android
---

# Goal

Implement Google sign-in through Credential Manager and Firebase Authentication.

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

- [x] Successful login creates/restores session.
- [x] Cancellation is handled.
- [x] Sign out clears credential state.
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
