---
id: T003
title: Create local backend infrastructure
status: done
depends_on: [T000, T002]
area: backend
---

# Goal

Add Docker Compose for PostgreSQL/PostGIS and a sample environment file.

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

- [x] Database becomes healthy locally.
- [x] No real credentials are committed.
- [x] Connection settings are documented.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
docker compose config
docker compose up -d
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
