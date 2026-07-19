---
id: T094
title: Add safe demo mode
status: todo
depends_on: [T091, T092, T093]
area: android
---

# Goal

Add debug-only location presets for HCMC and Bangkok without affecting release behavior.

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

- [ ] Only debug builds expose presets.
- [ ] Real GPS remains default.
- [ ] Demo script is documented.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test
./gradlew assembleRelease
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
