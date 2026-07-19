---
id: T016
title: Implement nearby local search
status: todo
depends_on: [T014, T015]
area: android
---

# Goal

Search Room POIs by alias/category and sort by deterministic straight-line distance.

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

- [ ] Works without network.
- [ ] Displays distance in km.
- [ ] Vietnamese diacritic normalization is tested.
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
