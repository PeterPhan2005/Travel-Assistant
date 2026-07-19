---
id: T095
title: Produce release candidate
status: todo
depends_on: [T091, T094]
area: quality
---

# Goal

Freeze scope, run all checks, produce signed/testable APK and demo runbook.

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

- [ ] Release APK installs on target device.
- [ ] No debug secrets/features leak.
- [ ] Known limitations and recovery plan are documented.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew clean test lint assembleRelease
ruff check backend
mypy backend/app
pytest backend
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
