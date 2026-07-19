---
id: T013
title: Create Room offline schema
status: todo
depends_on: [T011]
area: android
---

# Goal

Implement initial Room entities/DAOs for POI, aliases, menu items, narration, culture, itinerary and package metadata.

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

- [ ] Schema matches data-model context.
- [ ] DAO tests cover core queries.
- [ ] Migration strategy starts at version 1.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
