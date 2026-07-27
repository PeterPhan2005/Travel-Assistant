---
id: T034
title: Build travel package artifact
status: done
depends_on: [T031]
area: backend
---

# Goal

Generate a versioned package manifest and downloadable data file for one city.

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

- [x] Checksum is generated.
- [x] Package contains only approved fields.
- [x] Repeated build is deterministic for unchanged data.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
pytest
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
