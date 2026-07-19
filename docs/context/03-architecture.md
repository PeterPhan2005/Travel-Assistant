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

- Router Agent.
- Discovery Agent.
- Narration Agent.
- Local Culture Agent.
- Itinerary Agent.
- Grounding Reviewer Agent.
- Response Composer Agent.

Specialists run through separate agent executions with scoped structured input. Application code controls fan-out, parallelism, retry and timeouts.

## Deterministic services

- GPS/context collection.
- Speech-to-text.
- Haversine/route distance.
- Opening-hours normalization.
- POI deduplication.
- Ranking/scoring.
- Authorization.
- Offline full-text search.
- Sync and conflict resolution.

## Invariants

1. Mobile never contains private provider or OpenAI keys.
2. Exact location history is not persisted server-side.
3. Offline answers only use downloaded data.
4. Agent output is not trusted until schema validation succeeds.
5. Historical/cultural claims require a source or an explicit fallback label.
6. Missing fields are not hallucinated.
