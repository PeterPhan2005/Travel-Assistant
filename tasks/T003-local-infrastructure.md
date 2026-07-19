---
id: T003
title: Create local backend infrastructure
status: todo
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

- [ ] Database becomes healthy locally.
- [ ] No real credentials are committed.
- [ ] Connection settings are documented.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

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
