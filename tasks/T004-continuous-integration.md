---
id: T004
title: Add CI checks
status: done
depends_on: [T000]
area: quality
---

# Goal

Add CI jobs for Android build/tests and backend lint/type/tests using placeholder projects where necessary.

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

- [x] CI configuration is valid.
- [x] Jobs fail on lint/test errors.
- [x] Dependency caching is configured.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
# Documentation-only task; inspect repository state.
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
