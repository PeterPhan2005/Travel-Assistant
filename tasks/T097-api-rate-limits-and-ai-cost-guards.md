---
id: T097
title: Add API rate limits and AI cost guards
status: todo
depends_on: [T049, T061, T062]
area: backend
---

# Goal

Protect expensive model and provider operations before live credentials are
used.

# Read first

- `AGENTS.md`
- `backend/AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T049-agent-tracing-and-usage.md`
- `tasks/T061-voice-query-integration.md`
- `tasks/T062-structured-itinerary-generation-transport.md`

# Scope

- Add bounded assistant and itinerary-generation rate limits.
- Define request budgets for external POI providers and fresh-web research.
- Bound concurrent expensive work and preserve cancellation.
- Return one typed sanitized HTTP 429 behavior.
- Use privacy-safe limiter keys and safe aggregate usage budgets.
- Keep raw queries, prompts, content, coordinates and identity out of limiter
  logs and retained usage records.

# Out of scope

- Implementing Google Places, fresh-web retrieval or a production billing
  system.
- Persisting raw request/model/provider content.

# Acceptance criteria

- [ ] Assistant and itinerary-generation operations have bounded rate limits.
- [ ] Provider/research calls have explicit per-request budgets.
- [ ] Expensive work has an explicit concurrency bound.
- [ ] Limit exhaustion maps to the approved typed 429 response.
- [ ] Cancellation releases capacity and propagates unchanged.
- [ ] Limiter keys and aggregate usage records are privacy safe.
- [ ] Deterministic no-network tests cover limits, concurrency and recovery.
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

- Exact rate, concurrency and request-budget policy.
- Typed 429/cancellation/privacy test results.
- Exact files changed and known limitations.

