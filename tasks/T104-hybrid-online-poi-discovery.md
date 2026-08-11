---
id: T104
title: Implement hybrid online POI discovery
status: todo
depends_on: [T042, T102, T097]
area: backend
---

# Goal

Combine curated and approved external POI providers for online discovery.

# Read first

- `AGENTS.md`
- `backend/AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T042-discovery-agent.md`
- `tasks/T102-google-places-live-provider.md`

# Scope

- Execute a bounded multi-provider request through normalized contracts.
- Merge, deduplicate and rank results deterministically in application code.
- Preserve curated usable partial results when an external provider fails.
- Keep the exact request location request-scoped.
- Produce T042-compatible evidence and provenance.
- Add privacy, rate-limit, cancellation and offline-zero-call coverage.

# Invariants

- No LLM performs deduplication or ranking.
- Offline mode makes no Google or other live-provider call.
- External content is not bulk mirrored into canonical storage.

# Acceptance criteria

- [ ] Curated and approved external results use one normalized hybrid result.
- [ ] Merge, deduplication and ranking are deterministic.
- [ ] Curated partial results survive external failure safely.
- [ ] Exact request location remains request-scoped and privacy safe.
- [ ] Evidence is compatible with T042 and preserves provenance.
- [ ] Offline, rate-limit, cancellation and privacy tests pass.
- [ ] No LLM ranking/deduplication or external bulk mirror is introduced.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
ruff check .
mypy --strict app tests
pytest
python -m app.agent_evals check
```

# Expected evidence

- Merge/dedup/ranking policy and deterministic fixtures.
- External-failure/offline/cancellation/privacy results.
- Exact files changed and known limitations.

