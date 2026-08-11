---
id: T100
title: Validate live OpenAI multi-agent integration
status: todo
depends_on: [T050, T061, T062, T099, T106, T107]
area: ai
---

# Goal

Prove the real configured OpenAI Agents SDK path works end to end and does not
silently rely on deterministic fallback.

# Read first

- `AGENTS.md`
- `backend/AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/03-architecture.md`
- `docs/context/07-ai-system.md`
- `docs/context/08-privacy-security.md`
- `docs/context/11-evaluation-plan.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T041-router-agent.md` through `tasks/T050-agent-eval-runner.md`
- `tasks/T061-voice-query-integration.md`
- `tasks/T062-structured-itinerary-generation-transport.md`

# Scope

- Exercise real configured execution for every current model-capable T041–T047
  stage when an eligible scenario reaches it, plus T048 orchestration and T049
  safe aggregate usage evidence.
- Cover HCMC, Bangkok, itinerary, culture, broad non-food discovery,
  area-aware questions and fresh-web evidence.
- Cover insufficient-evidence safe failure, timeouts and cancellation.
- Verify authenticated Android rendering against the release-like environment.
- Keep API keys and model configuration outside Git.

# Invariants

- Preserve the existing seven model-executed agent identities.
- Do not print or persist secrets, raw prompts or raw model responses.
- Ordinary CI remains deterministic, keyless and independent of this explicit
  live validation.

# Acceptance criteria

- [ ] Eligible scenarios prove real model execution for all seven current agent identities.
- [ ] T048 orchestration and T049 safe aggregate usage evidence are observed.
- [ ] HCMC/Bangkok, itinerary, culture, non-food, area and fresh-evidence scenarios pass safely.
- [ ] Insufficient evidence, timeout and cancellation behavior is verified.
- [ ] Authenticated Android renders the validated live result.
- [ ] Evidence distinguishes live execution from deterministic fallback.
- [ ] No secret, raw prompt or raw model response is printed or persisted.
- [ ] Deterministic keyless CI remains green.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
ruff check .
mypy --strict app tests
pytest
python -m app.agent_evals check
```

Run the separately documented credentialed live matrix outside ordinary CI.

# Expected evidence

- Sanitized proof of real stage execution and aggregate usage.
- Scenario, timeout, cancellation and Android-rendering results.
- Exact files changed and known limitations.

