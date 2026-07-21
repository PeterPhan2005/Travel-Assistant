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
- WorkManager for package download/sync that can resume.
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

## Invariants

1. Mobile never contains private provider or OpenAI keys.
2. Exact location history is not persisted server-side.
3. Offline answers only use downloaded data.
4. Agent output is not trusted until schema validation succeeds.
5. Historical/cultural claims require a source or an explicit fallback label.
6. Missing fields are not hallucinated.
