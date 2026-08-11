---
id: T106
title: Add area-aware Assistant and neighborhood intelligence
status: todo
depends_on: [T044, T048, T092, T093, T104]
area: fullstack
---

# Goal

Allow Assistant to understand canonical districts, neighborhoods and cultural
areas, combine area-culture evidence with curated/live POI discovery, and answer
area-level travel questions safely.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md` files.
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/11-evaluation-plan.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T044-local-culture-agent.md`
- `tasks/T048-code-orchestrator.md`
- `tasks/T104-hybrid-online-poi-discovery.md`

# Scope

- Define typed canonical `GeoArea` values with stable application-owned IDs,
  area kind, aliases and approved geographic membership/boundary data.
- Support future area kinds including administrative district, neighborhood,
  cultural area, tourism cluster, street/corridor and landmark area.
- Implement deterministic resolution, ambiguity and unknown-area behavior.
- Combine area-scoped culture evidence and POI discovery for HCMC and Bangkok.
- Support area comparison, cuisine suitability, evidenced area culture,
  activity discovery, combined culture + café/check-in interests and explicit
  place-type discovery inside a named canonical area.

# Invariants

- An LLM never authors an area ID, boundary, district mapping or membership.
- Do not add an unrestricted Area Agent. Prefer deterministic `AreaResolver`
  plus existing Discovery, Local Culture, Grounding Reviewer and Response
  Composer boundaries.
- External provider counts are not an exhaustive census.
- Area reputation/cultural claims need evidence; unsupported “best” claims are
  rejected.

# Acceptance criteria

- [ ] Typed canonical areas, kinds, stable IDs, aliases and application-owned geography are defined.
- [ ] Area resolution is deterministic and handles ambiguity/unknown input.
- [ ] Area-scoped culture evidence and curated/live POI discovery work together.
- [ ] Area comparison and broad cuisine/culture/check-in queries are supported safely.
- [ ] HCMC and Bangkok deterministic scenarios pass.
- [ ] No model-authored geography, census claim, unsupported “best” claim or Area Agent is introduced.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
ruff check .
mypy --strict app tests
pytest
python -m app.agent_evals check
./gradlew test
```

# Expected evidence

- Canonical area contract and deterministic resolver policy.
- HCMC/Bangkok ambiguity, unknown, culture and discovery results.
- Exact files changed and known limitations.
