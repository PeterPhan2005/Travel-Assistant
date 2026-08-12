---
id: T092
title: Complete HCMC curated dataset
status: done
depends_on: [T031, T043, T044]
area: data
---

# Goal

Produce the approved primary demo dataset with exactly 30 curated HCMC POIs,
including the supported menus, narrations and local-culture records for those
POIs.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/12-progress-tracker.md`

# Scope

Implement only the goal and acceptance criteria in this file.

The 30 HCMC records are part of the fixed 42-POI curated trust anchor and
downloadable offline dataset. They are not a claim that TravelAssistant knows
only 30 HCMC places when online. The package must provide reviewable category
and area diversity across the broad travel scope where reliable evidence is
available; it must not be dominated by restaurants or food.

# Source policy

- Price and menu facts prefer direct venue, restaurant or operator sources and
  require both source provenance and `source_updated_at`/`retrieved_at`
  freshness metadata as supported by the canonical schema.
- Historical and cultural claims prefer, in order: the official venue, a
  museum, a government/tourism authority, then a university or other
  institutional source. A reputable editorial source may supplement these
  sources.
- POI identity and address prefer official venue, government or tourism
  sources.
- A user review or social-media post must never be the sole source for a price,
  historical claim, cultural claim or important opening-hours fact.
- Missing facts remain missing. An LLM is never a factual source.
- If the current source taxonomy cannot encode a proposed source class, record
  the gap instead of inventing a contract migration inside this data task.

# Out of scope

- Future tasks.
- Unrequested refactors.
- New product behavior not present in context files.
- Live Google Places or fresh-web retrieval.
- Treating the curated package as an exhaustive online POI universe.

# Acceptance criteria

- [x] The canonical HCMC package contains exactly 30 curated POIs.
- [x] Category and area coverage is documented and the package is not food dominated.
- [x] Every price/menu fact follows the accepted direct-source and freshness policy.
- [x] Historical, cultural, identity, address and opening-hours facts follow the accepted source hierarchy.
- [x] User reviews/social posts are never the sole source for restricted fact classes.
- [x] Missing facts remain absent and no LLM output is used as a factual source.
- [x] Every narration has approved sources or an explicit fallback label allowed by the existing contract.
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
