# ADR 0005: Hybrid Travel Discovery and Bounded Live Evidence

## Status

Accepted.

## Decision

TravelAssistant follows **online breadth, offline trusted depth**.

The curated trust anchor and downloadable offline dataset contains exactly 42
POIs: 30 in Ho Chi Minh City and 12 in Bangkok. These POIs are the
high-confidence evidence set, not the complete universe of places the product
may know while online. Travel discovery is broad rather than food-only and may
cover restaurants, cafés, landmarks, scenic/check-in places, history, culture,
museums, galleries, religious/cultural places, markets, shopping, nightlife,
parks/nature, family attractions, entertainment, wellness/spa, transportation
places, local life and general travel POIs where evidence/provider coverage
exists.

Explore and Assistant share an application-owned Travel Discovery Core:

```text
Explore
   \
    -> Travel Discovery Core
   /
Assistant

Travel Discovery Core
  - deterministic AreaResolver
  - CuratedPoiProvider
  - GooglePlacesPoiProvider (intended first live provider; not implemented)
  - normalized hybrid discovery
  - deterministic deduplication and ranking
  - request-scoped evidence registry
```

Online discovery may combine curated data, approved live external POI providers
and fresh web evidence when required. Offline discovery uses only the active
downloaded curated package. External provider content remains transient unless
provider policy and an accepted architecture explicitly permit a stored field;
there is no external bulk POI mirror, persistent web knowledge mirror or
Google-only canonical Room insertion merely to support detail navigation.

Area IDs, aliases, boundaries and membership are application-owned. A
deterministic `AreaResolver` handles future canonical administrative districts,
neighborhoods, cultural areas, tourism clusters, streets/corridors and landmark
areas. A model may not invent area IDs, boundaries, district mappings or area
membership.

Fresh web research is application-controlled and provider-neutral. The default
service boundaries are `WebSearchProvider`, `SourceFetcher` and
`WebEvidenceService`/`EvidenceExtractor`. The existing model-executed agent
identity set remains exactly Router, Discovery, Narration, Local Culture,
Itinerary, Grounding Reviewer and Response Composer. No unrestricted eighth
browsing agent is added by default. Existing agent boundaries consume only
bounded, extracted, validated evidence.

Application code decides when research is required. Deterministic nearby POI
requests use Places/hybrid discovery; known curated narration uses curated
evidence first; freshness-sensitive hours/menu/price/event questions prefer
fresh sources; long-tail attributes may combine Places candidates with web
evidence; culture uses curated/authoritative evidence first. Models cannot
create unlimited search/fetch loops.

Web content is untrusted data, never instructions. Retrieval must enforce HTTPS,
SSRF protection, private/link-local/loopback rejection except explicit local
test seams, redirect/time/response-size/content-type/search-count/fetch-count/
overall-deadline limits, cancellation, no credential or arbitrary authorization
forwarding, prompt-injection resistance and no raw HTML/page retention or
logging. Evidence preserves typed source identity/class, retrieval time,
available publication/source-update time, geographic scope, claim/source closure
and a bounded freshness category. Grounding review remains mandatory. No
unsupported numerical confidence score is introduced.

## Source policy

- Price and menu facts prefer direct venue, restaurant or operator sources and
  require source freshness metadata.
- Historical/cultural claims prefer official venue, museum,
  government/tourism authority, then university/institutional sources; reputable
  editorial sources may supplement them.
- POI identity/address prefer official venue, government or tourism sources.
- User reviews or social-media posts are never the sole source for price,
  historical/cultural claims or important opening-hours facts.
- Missing facts remain missing. An LLM is never a factual source.

## Consequences

- Google Places is the first intended source of online breadth, but this ADR
  does not claim that it or live-web retrieval is implemented.
- External-provider counts cannot be described as an exhaustive area census.
- Area reputation and cultural claims require evidence; unsupported “best”
  claims fail closed.
- Provider credentials remain server-side; Android contains no server Places
  credential.
- Booking, payment and self-built turn-by-turn navigation remain unsupported.
- T092/T093 complete the 42-POI trusted dataset; T102/T104–T107 implement the
  live discovery, area and research layers in later tasks.

