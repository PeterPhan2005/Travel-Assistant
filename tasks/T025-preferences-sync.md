---
id: T025
title: Synchronize user preferences
status: done
depends_on: [T021, T024, T031]
area: fullstack
---

# Goal

Implement authenticated GET/PUT preference endpoints and Android repository sync.

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

- [x] Preferences persist by UID.
- [x] Offline edits queue safely.
- [x] Conflicts use documented last-write policy.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
ruff check .
mypy app
pytest
./gradlew test
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
