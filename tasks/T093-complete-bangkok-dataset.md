---
id: T093
title: Complete Bangkok demo dataset
status: todo
depends_on: [T031, T043, T044]
area: data
---

# Goal

Produce the international demo package with exactly 12 curated Bangkok POIs
and Vietnamese-facing content.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/12-progress-tracker.md`

# Scope

Implement only the goal and acceptance criteria in this file.

The 12 Bangkok records complete the fixed 42-POI curated trust anchor and
downloadable offline dataset. They are not a claim that TravelAssistant knows
only 12 Bangkok places when online. The package must provide reviewable category
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

- [ ] The canonical Bangkok package contains exactly 12 curated POIs.
- [ ] Category and area coverage is documented and the package is not food dominated.
- [ ] Vietnamese-facing locale behavior and Bangkok local currency are handled without conversion guesses.
- [ ] Every price/menu fact follows the accepted direct-source and freshness policy.
- [ ] Historical, cultural, identity, address and opening-hours facts follow the accepted source hierarchy.
- [ ] User reviews/social posts are never the sole source for restricted fact classes.
- [ ] Missing facts remain absent and no LLM output is used as a factual source.
- [ ] Sources and freshness metadata are recorded through the existing strict contract.
- [ ] The core Bangkok demo flow works.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
pytest
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
