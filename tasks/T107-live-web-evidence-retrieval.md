---
id: T107
title: Add live web evidence retrieval
status: todo
depends_on: [T046, T047, T049, T097, T106]
area: ai
---

# Goal

Allow online Assistant requests to obtain current long-tail web evidence safely
without creating a persistent Internet knowledge mirror.

# Read first

- `AGENTS.md`
- `backend/AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/11-evaluation-plan.md`
- `docs/context/12-progress-tracker.md`
- `docs/adr/0005-hybrid-travel-discovery-and-live-evidence.md`
- `tasks/T046-grounding-reviewer-agent.md`
- `tasks/T047-response-composer-agent.md`
- `tasks/T049-agent-tracing-and-usage.md`
- `tasks/T097-api-rate-limits-and-ai-cost-guards.md`
- `tasks/T106-area-aware-assistant-neighborhood-intelligence.md`

# Architecture

Implement application-controlled services with these default boundaries:

- provider-neutral `WebSearchProvider`;
- bounded `SourceFetcher`;
- `WebEvidenceService`/`EvidenceExtractor`;
- request-scoped evidence registry consumed by the existing seven-agent
  topology.

Do not add an unrestricted eighth browsing agent by default and do not bind the
architecture to scraping Google Search.

# Retrieval policy

- Curated/authoritative evidence remains first when sufficient.
- Nearby deterministic POI requests use Places/hybrid discovery only.
- Fresh hours, menu, price and event questions prefer fresh sources.
- Long-tail attributes may combine Places candidates with web evidence.
- Culture uses curated/authoritative evidence first and fresh research only
  where required.
- Application code controls routing; a model cannot create unlimited
  search/fetch loops.

# Security and provenance

- Enforce HTTPS, SSRF protection and rejection of private/link-local/loopback
  targets except explicit local test seams.
- Bound redirects, timeouts, response size, accepted content types, search
  count, source-fetch count and the overall research deadline; preserve
  cancellation.
- Forward no credential or arbitrary authorization to model-selected targets.
- Treat webpage content as untrusted data, never instructions. Extract bounded
  evidence before any agent sees it and resist prompt injection.
- Do not retain or log raw HTML/page content.
- Preserve typed source identity/class, `retrieved_at`, available
  `published_at`/`source_updated_at`, geographic scope, claim/source closure and
  a bounded freshness category.
- Define exact enum names in this implementation task; do not invent an
  unsupported numerical confidence score.

# Required product scenarios

- Unusual POI attribute.
- Freshness-sensitive opening information.
- Current event.
- Culture question.
- Area recommendation.
- Live venue examples.

Do not hard-code factual answers to those scenario types.

# Acceptance criteria

- [ ] Provider-neutral search, bounded fetch and extraction services are implemented.
- [ ] Evidence is request-scoped and no persistent web knowledge mirror exists.
- [ ] Retrieval routing is application-controlled and curated-first when sufficient.
- [ ] Search/fetch/deadline budgets, HTTPS/SSRF/redirect/type/body controls and cancellation work.
- [ ] Web content is treated as untrusted data and prompt injection cannot alter instructions.
- [ ] Credentials, arbitrary authorization and raw pages never enter agent input/log retention.
- [ ] Typed provenance, freshness and Grounding Reviewer claim/source closure are preserved.
- [ ] Deterministic fake search/fetch tests cover all required scenario types.
- [ ] A separately run live research smoke test is documented safely.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
ruff check .
mypy --strict app tests
pytest
python -m app.agent_evals check
```

# Expected evidence

- Retrieval-routing, security-budget and freshness policy.
- Deterministic prompt-injection/SSRF/limit/cancellation test results.
- Sanitized live-research smoke result, exact files changed and limitations.

