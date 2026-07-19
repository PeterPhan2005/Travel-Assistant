---
id: T011
title: Add Android architecture shell
status: todo
depends_on: [T010]
area: android
---

# Goal

Add feature-oriented packages, ViewModel pattern, Hilt and base repository interfaces.

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

- [ ] Hilt app starts.
- [ ] A sample ViewModel exposes immutable StateFlow.
- [ ] No business logic is in composables.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test
./gradlew lint
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
