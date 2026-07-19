---
id: T030
title: Create server database schema
status: todo
depends_on: [T003, T023]
area: backend
---

# Goal

Add SQLAlchemy models and Alembic migration for users, preferences, trips, itineraries, POIs, sources, menus and narrations.

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

- [ ] Migration upgrades and downgrades cleanly.
- [ ] Ownership indexes exist.
- [ ] Coordinates use spatial-capable storage.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
alembic upgrade head
pytest
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
