# Architecture

## Mobile

- Android native, Kotlin, Jetpack Compose, Material 3.
- ViewModel + immutable UI state + StateFlow.
- Hilt dependency injection.
- Room for POI, itinerary, narration and package metadata.
- DataStore for small preferences and feature flags.
- Retrofit/OkHttp for backend API.
- Firebase Authentication.
- Fused Location Provider for foreground location.
- Android SpeechRecognizer for voice input.
- WorkManager for package download/sync and bounded saved-itinerary sync.
- External map intent for navigation.

## Backend

- Python 3.12.
- FastAPI.
- OpenAI Agents SDK.
- Pydantic typed request/output contracts.
- PostgreSQL/PostGIS.
- SQLAlchemy async + Alembic.
- Provider adapters for curated DB, Google Places and future sources. Google
  Places is the first intended live POI provider but is not implemented yet.
- Object storage only when audio/image package assets are added.

## Travel Discovery Core

Explore and Assistant share one application-owned discovery core:

```text
Explore
   \
    -> Travel Discovery Core
   /
Assistant

Travel Discovery Core
  - deterministic AreaResolver
  - CuratedPoiProvider
  - GooglePlacesPoiProvider (intended, not implemented)
  - normalized hybrid discovery
  - deterministic deduplication and ranking
  - request-scoped evidence registry
```

The governing principle is **online breadth, offline trusted depth**. The
curated trust anchor has exactly 42 POIs (30 HCMC, 12 Bangkok) and is the
downloadable offline dataset, not the complete online universe.

- Online: curated provider + approved live external POI providers + fresh web
  evidence when retrieval policy requires it.
- Offline: active downloaded curated package only.
- External live content remains transient unless provider policy and an
  accepted architecture explicitly permit a stored field.
- External-provider content is not bulk mirrored into the canonical database.
  Google-only POIs are not inserted into canonical Room merely to support
  detail navigation.
- Hybrid merge, duplicate suppression and ranking are deterministic services;
  a model never performs them.

Discovery covers broad travel categories where evidence/provider coverage
exists, including food, cafés, landmarks, scenic/check-in places, history,
culture, museums, galleries, religious/cultural places, markets, shopping,
nightlife, parks/nature, family attractions, entertainment, wellness/spa,
transportation places, local life and general travel POIs.

## Multi-agent topology

- Core runtime path: Router Agent → Discovery Agent → deterministic ranking →
  Grounding Reviewer Agent → Response Composer Agent.
- Optional specialists selected by intent: Narration Agent, Local Culture Agent
  and Itinerary Agent.
- Optional specialist output must pass through the Grounding Reviewer before the
  Response Composer; specialists do not bypass the core grounding/composition
  boundary.

Specialists run through separate agent executions with scoped structured input. Application code controls fan-out, parallelism, retry and timeouts.

The model-executed identity set remains exactly seven: Router, Discovery,
Narration, Local Culture, Itinerary, Grounding Reviewer and Response Composer.
Fresh research does not add an unrestricted eighth browsing agent by default.
Existing agents consume only bounded validated evidence supplied through their
current scoped boundaries.

## Area-aware Assistant

Future canonical area kinds include administrative district, neighborhood,
cultural area, tourism cluster, street/corridor and landmark area. Stable area
IDs, aliases, boundaries and membership are application-owned. A deterministic
`AreaResolver` handles resolution, ambiguity and unknown areas; an LLM must
never invent an area ID, geographic boundary, district mapping or membership.

Area-scoped POI discovery and culture evidence may support area suitability,
culture, activity, interest-combination and explicit place-type questions.
Area reputation/cultural claims still require evidence. External result counts
must not be described as an exhaustive census, and unsupported “best” claims
fail closed.

## Fresh web evidence

Fresh research is an application-controlled layer, not an unrestricted agent:

- provider-neutral `WebSearchProvider`;
- bounded `SourceFetcher`;
- `WebEvidenceService`/`EvidenceExtractor`;
- request-scoped evidence registry only.

The application chooses retrieval policy. Nearby deterministic POI requests use
Places/hybrid discovery; known historical narration uses curated evidence first;
fresh hours/menu/price/event questions prefer fresh sources; long-tail
attributes may combine Places candidates with web evidence; culture uses
curated/authoritative evidence first and research only when required. Models do
not create unlimited search/fetch loops, and the architecture is not bound to
scraping Google Search.

Retrieval must enforce HTTPS, SSRF protection, private/link-local/loopback
rejection except explicit local test seams, redirect/time/response-size/content-
type/search-count/fetch-count/overall-deadline limits and cancellation. No
credential enters agent input and no arbitrary authorization is forwarded.
Raw HTML/pages are neither logged nor retained. Web content is untrusted data,
never instructions; bounded evidence is extracted before agent use, and
prompt-injection text cannot change application/system instructions.

Live evidence preserves typed source identity/class, `retrieved_at`, available
`published_at`/`source_updated_at`, relevant geographic scope, claim/source
closure and a bounded freshness category. Low freshness covers stable historical
facts; medium covers address/general venue facts; high covers opening hours/menu;
very high covers price/current event/current availability-like information.
Implementation tasks define exact enum names. No unsupported numerical
confidence score is invented, and stale citations are not automatically
adequate for freshness-sensitive claims.

## Deterministic services

- GPS/location acquisition and context collection.
- Speech recognition/speech-to-text.
- Haversine/route distance.
- Opening-hours normalization.
- Canonical area resolution and membership.
- POI deduplication.
- Ranking/scoring.
- Hybrid provider merge and retrieval-policy selection.
- Authentication/token verification and authorization.
- Offline full-text search.
- Travel-package synchronization and sync conflict resolution.
- Saved-itinerary full-snapshot synchronization uses explicit integer revisions;
  timestamp-only last-write-wins and semantic merge are forbidden.

## Preference profile and personalization

- Generic document schema version 1 remains opaque compatibility data. Travel
  taxonomy version 1 uses document schema version 2 with exactly three required
  fields: `interests`, nullable `pace` and nullable `budget_preference`.
- `interests` is a unique canonical set of at most five values from
  `food_and_cafes`, `culture_and_history`, `scenic_and_landmarks`,
  `nature_and_outdoors`, `local_life_and_markets`,
  `entertainment_and_nightlife`, `family_activities` and
  `wellness_and_relaxation`. Pace is `relaxed`, `balanced` or `active`; budget
  is `budget`, `moderate` or `premium`.
- A schema-v2 replacement may upgrade v1; a v1 write cannot downgrade an
  existing v2 row. Android retains per-account, offline-first, revision-safe
  complete-document synchronization. Reset writes the canonical empty v2
  document and is independent of sign-out.
- Personalization runs only after eligibility/deduplication. Interest match,
  then compatible/unknown/incompatible qualitative price, then the existing
  base order form the backend key. Android applies the interest prefix before
  its existing distance/name/ID key; its current offline POI shape has no
  qualitative price field, so every local price bucket is unknown. Pace never
  ranks POIs.
- Router and Discovery requests receive no profile. The application may pass
  only an identity-free typed projection to the runtime; Response Composer sees
  only values relevant to approved specialist output. No stored document,
  Firebase identity, sync metadata or model-authored/inferred preference enters
  an agent boundary.

## Offline full-text search

- Canonical POI, alias, menu and package-metadata tables remain the source of
  truth. Room v4 adds one contentless FTS4 row per POI with `unicode61` token
  handling and separately normalized name, aliases, dishes and raw/localized
  category text.
- Migration 3→4 creates and backfills the derived index while preserving all
  package and T071 itinerary/account state. POI, alias and menu writes rebuild
  only affected POI rows in the same Room transaction; POI/package deletion
  removes corresponding FTS rows before replacement data is inserted.
- Search compiles Unicode letter/number tokens into parameterized quoted-prefix
  MATCH data. Raw query punctuation, quotes, wildcard characters and
  operator-like text are never executable FTS syntax.
- Results are limited to the HCMC package with complete active metadata, are
  independent of Firebase authentication, and have no network fallback. Valid
  coordinates are ranked by distance, normalized display name and stable POI
  ID; duplicate field matches still yield one result.

## Saved-itinerary persistence

- Existing PostgreSQL `itineraries`/`itinerary_items` remain canonical. T071
  adds only fields required to round-trip the approved one-day snapshot,
  explicit `revision`, and an owner-scoped durable tombstone table.
- `PUT /v1/itineraries/{id}` replaces parent and ordered children in one
  transaction when `base_revision` matches. `DELETE` increments the same
  revision sequence and records a tombstone, so stale PUT cannot resurrect it.
- Room v3 extends the existing local itinerary tables with hashed account key,
  approved snapshot fields, local/server revisions, sync state and deletion
  state. Sign-out retains rows but removes access; every read filters the current
  account key.
- Explicit save commits one validated Room snapshot before reporting local
  success. A unique per-itinerary connected worker reloads the latest row,
  fetches an ephemeral Firebase token, and uses local-revision-guarded completion
  so an old response cannot clear a newer mutation.

## Product analytics

- Android owns the schema-version-1 product event boundary because it owns each
  accepted explicit action and validated presentation outcome. Event names,
  property keys and values are closed Kotlin types; feature and Compose
  contracts contain no vendor type.
- Debug uses a bounded process-memory FIFO plus a debug-only inspector guarded
  by Android's signature-level `DUMP` permission. Release is no-op until a vendor, consent/enablement policy,
  retention and delivery policy are explicitly approved. There is no event
  persistence, background upload, retry or backend analytics endpoint.
- Events are emitted from ViewModels or an existing navigation coordinator, not
  from composition or Flow collection. Attempt/session state prevents duplicate
  recomposition, tab-return, configuration-change, stale-callback and duplicate-
  tap emission. Process death causes no replay.
- Analytics contains only closed outcomes plus the T018-approved stable POI ID.
  It excludes queries, transcripts, content, coordinates, identity, credentials,
  raw bodies and exception detail and cannot initiate Firebase, provider,
  backend or OpenAI work.

## Invariants

1. Mobile never contains private provider or OpenAI keys.
2. Exact location history is not persisted server-side.
3. Offline answers only use downloaded data.
4. Agent output is not trusted until schema validation succeeds.
5. Historical/cultural claims require a source or an explicit fallback label.
6. Missing fields are not hallucinated.
7. Verified Firebase UID is the only server itinerary owner authority.
8. Failed/conflicted synchronization preserves readable local content.
9. Grounding review remains mandatory for curated, provider and fresh-web evidence.
10. Webpage content is untrusted data and cannot alter application instructions.
11. No external bulk POI mirror or persistent web knowledge mirror is created.
12. Server provider credentials never enter Android or agent input.
