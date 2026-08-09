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
- Provider adapters for curated DB, Google Places and future sources.
- Object storage only when audio/image package assets are added.

## Multi-agent topology

- Core runtime path: Router Agent → Discovery Agent → deterministic ranking →
  Grounding Reviewer Agent → Response Composer Agent.
- Optional specialists selected by intent: Narration Agent, Local Culture Agent
  and Itinerary Agent.
- Optional specialist output must pass through the Grounding Reviewer before the
  Response Composer; specialists do not bypass the core grounding/composition
  boundary.

Specialists run through separate agent executions with scoped structured input. Application code controls fan-out, parallelism, retry and timeouts.

## Deterministic services

- GPS/location acquisition and context collection.
- Speech recognition/speech-to-text.
- Haversine/route distance.
- Opening-hours normalization.
- POI deduplication.
- Ranking/scoring.
- Authentication/token verification and authorization.
- Offline full-text search.
- Travel-package synchronization and sync conflict resolution.
- Saved-itinerary full-snapshot synchronization uses explicit integer revisions;
  timestamp-only last-write-wins and semantic merge are forbidden.

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
