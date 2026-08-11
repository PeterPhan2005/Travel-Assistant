---
id: T103
title: Add production operations monitoring
status: todo
depends_on: [T049, T099, T100]
area: quality
---

# Goal

Add privacy-safe operational health and error monitoring.

# Release policy

T103 is nonblocking for the thesis/demo release unless later accepted
requirements explicitly make it mandatory.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md` files.
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/11-evaluation-plan.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T049-agent-tracing-and-usage.md`
- `tasks/T099-staging-and-release-environment.md`
- `tasks/T100-live-openai-multi-agent-validation.md`

# Scope

- Define bounded operational health, availability, latency and safe error
  signals for the release-like environment.
- Preserve existing request correlation and aggregate-only agent usage.
- Define alerting/runbook ownership without storing user content.
- Document retention and access controls before enabling persistent monitoring.

# Out of scope

- Product analytics expansion.
- Raw query, prompt, response, coordinate, identity or provider-payload storage.
- Blocking T095 unless a later accepted requirement changes the task graph.

# Acceptance criteria

- [ ] Operational signals and retention/access policy are documented and bounded.
- [ ] Health, error and latency monitoring excludes user content and secrets.
- [ ] Request/trace correlation remains privacy safe.
- [ ] Failure of monitoring cannot change product behavior.
- [ ] Alert/runbook behavior is verified in the release-like environment.
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

- Signal, retention, access and alert/runbook inventory.
- Privacy/failure-isolation results.
- Exact files changed and known limitations.

