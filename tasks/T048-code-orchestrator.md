---
id: T048
title: Implement strict multi-agent orchestrator
status: done
depends_on: [T041, T042, T043, T044, T045, T046, T047]
area: ai
---

# Goal

Coordinate separate Runner executions with scoped context, timeouts, retries and parallel fan-out where independent.

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

- [x] Each specialist has a separate trace/run.
- [x] No shared full transcript by default.
- [x] A single failure can yield safe partial output.
- [x] Latency budget is enforced.
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
