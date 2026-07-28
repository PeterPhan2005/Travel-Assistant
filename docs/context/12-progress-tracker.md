# Progress Tracker

## Current phase

Phase 3 is in progress. The Android architecture shell is present, with Hilt,
ViewModel/StateFlow and repository boundaries established. The top-level
Navigation Compose shell and centralized Material 3 theme are complete;
the Room version-2 schema and core DAO layer are complete, and a bundled HCMC
demo seed imports safely and idempotently. Explore now has user-triggered,
one-shot foreground location context with explicit UI states plus offline Room
search by canonical name, alias and category. Vietnamese text normalization and
deterministic straight-line Haversine ranking run locally. Nearby rows open a
Room-backed local detail screen while preserving Explore state. Optional fields,
menus and sourced narration are omitted when absent; stored menu prices show
currency-safe formatting and an update date. The bundled seed still contains no
menu or narration records. There is no background tracking or exact-location
persistence. Loaded POI details now offer explicit external navigation through
any compatible `geo:` handler, with validated stored POI coordinates, localized
recoverable errors and a no-op analytics boundary that never receives
coordinates. The app shell now observes validated Internet connectivity without
making a network request and presents Checking, Online and Offline explicitly.
Offline Room search and POI detail remain usable. Local package version and
publication metadata are observed by the app-shell state owner and displayed
in Downloads. Assistant still explains its Internet requirement without
claiming unfinished AI behavior works. External navigation is not disabled
solely because the app is offline. Live Google Places, Android nearby
transport, production hosting and the end-to-end OpenAI Agents SDK runtime
remain incomplete. T041 now provides one independent Router execution with
strict `RouterOutput`, no tools/handoffs/sessions, explicit optional model
configuration and a deterministic six-intent fallback. T042 now provides one
independent Discovery execution over normalized POI/menu tools with deterministic
evidence closure and no final prose. Later agents and application orchestration
remain incomplete. The dedicated Firebase
development client configuration is integrated only for debug through the
Google Services plugin and Firebase Android BoM. Standard automatic
initialization provides the default Firebase app in the debug process. Profile
now implements Firebase email/password registration and sign-in. Unverified
users remain outside authenticated Profile content; explicit verification
refresh/resend and sign-out are available, and the session stream restores from
Firebase rather than app-managed credentials. JVM, lint, build and emulator UI
checks pass. Manual validation against the Firebase development project confirms
registration, verification-email delivery/resend, unverified restoration as
VerificationRequired, explicit refresh to Authenticated, verified restoration,
sign-out and verified email/password sign-in. Explore and local Room data remain
intact and independent of authentication. Profile also offers explicit Google
sign-in through Credential Manager's button flow. The generated web client
resource configures the request, Google ID credentials are exchanged only
ephemerally for Firebase credentials, cancellation is controlled, and Firebase
current-user state remains the single session source of truth. Explicit sign-out
clears Firebase and Credential Manager state; a clearing failure keeps the app
SignedOut with a recoverable warning. Production/release configuration remains
separate and absent. The backend now has an independent FastAPI application
factory, immutable validated environment settings, an unauthenticated liveness
endpoint, validated request correlation IDs and one sanitized JSON error
envelope. A replaceable Firebase verification boundary uses the official Admin
SDK with ADC, an explicit expected project, revocation checking and
off-event-loop execution. `GET /auth/me` accepts only Bearer ID tokens and
exposes only the verified UID. The backend now also has typed SQLAlchemy 2
metadata and one async Alembic foundation migration for explicit user
ownership, trips and ordered itineraries, stable curated POI/content IDs,
normalized sources, menu prices, grounded narrations and PostGIS geography
points. A repository-owned curated pipeline now validates canonical YAML (and
accepted JSON) against immutable Pydantic schema version 1 plus a generated
JSON Schema, then seeds the fixed T030 schema with async, transaction-scoped,
idempotent upserts. Starter packages contain two HCMC POIs and one Bangkok POI,
each linked to reviewable official sources with retrieval timestamps. An
immutable provider-neutral POI boundary now accepts a validated city, optional
query/category, request-scoped origin, bounded metre radius and bounded limit.
The first adapter reads curated POIs through an injected async session, uses
PostGIS geography filtering/distance, orders by distance then stable POI ID and
maps typed provenance/freshness without exposing ORM/spatial rows or arbitrary
provider payloads. One exception shape standardizes timeout, unavailable,
rate-limited, invalid request/response, misconfiguration, unsupported and
internal failures while preserving cancellation. Canonical
`GET /pois/nearby` now maps validated `city`, WGS84 origin, optional
query/category, radius default 5,000/max 50,000 metres and limit default 5/max
20 into that provider boundary. It returns only normalized destination POIs,
explicit metre distance, typed provenance/freshness, count and `is_complete`;
the request origin, UID, ORM rows and arbitrary payloads never enter the
response. Missing Authorization is anonymous and skips Firebase verification,
while any supplied token is strictly verified and invalid credentials remain a
controlled error; `/auth/me` remains strict. Each non-injected app owns a lazy
async engine for its lifespan and closes one read-only session per nearby
request without committing. `/health` opens no session or database connection.
Provider failures map to stable sanitized 400/429/501/502/503/500 errors with
matching request IDs and preserved cancellation. A database-free static
travel-package builder now converts exactly one validated T031 city package per
invocation into schema-version-1 public data plus a schema-version-1 manifest.
The committed HCMC pair is byte-deterministic and independently verifiable by
exact byte size and SHA-256. Android now downloads/resumes and validates that
HCMC artifact through a user-triggered WorkManager flow, then atomically
activates it in Room while retaining old offline data on every failure.
Canonical private `GET /preferences` and `PUT /preferences` now persist one
strict schema-version-1 generic document by authenticated Firebase UID. Android
stores each account's complete document, local revision, pending flag and last
server timestamp in app-private DataStore under a hashed account key; a unique
connected WorkManager job gets the ID token only at request time and pushes the
latest snapshot before any refresh. T040 now defines the complete strict,
immutable provider-neutral contract package for Router, Discovery, Narration,
Local Culture, Itinerary, Grounding Reviewer, Response Composer and the
code-orchestrated runtime boundary. T041 implements the independent Router run
and fallback. T042 now implements one independent Discovery execution over the
injected T032 provider and a selected-curated, read-only menu boundary. It
preserves PostGIS distance/ID order and missing optionals, builds only
tool-grounded deterministic evidence, returns safe usable partial results, and
has no final prose. Live Google Places, preference taxonomy/UI, Narration and
the end-to-end agent runtime remain unimplemented.

## Current goal

T042 Discovery Agent is complete. T043 Narration Agent is next by roadmap and
dependency readiness, but must not begin until explicitly assigned.

## Completed

- Product discovery decisions recorded.
- Android-first decision recorded.
- Strict real multi-agent definition recorded.
- Initial task backlog created.
- T000 Bootstrap repository.
- T001 Verify developer environment.
- T002 Approve context and ADR baseline.
- T003 Create local backend infrastructure.
- T004 Add CI checks.
- T010 Create Android Compose app.
- T011 Add Android architecture shell.
- T012 Implement navigation and theme.
- T013 Create Room offline schema.
- T014 Import curated seed into Room.
- T015 Implement foreground location context.
- T016 Implement nearby local search.
- T017 Implement POI detail and local narration.
- T018 Open external navigation.
- T019 Add explicit offline UI state.
- T020 Integrate Firebase configuration.
- T021 Implement email authentication.
- T022 Implement Google authentication.
- T023 Create FastAPI service.
- T024 Verify Firebase tokens in backend.
- T025 Synchronize user preferences.
- T030 Create server database schema.
- T031 Build curated data pipeline.
- T032 Define POI provider adapters.
- T033 Implement nearby POI API.
- T034 Build travel package artifact.
- T035 Download and activate travel package.
- T040 Define agent contract models.
- T041 Implement Router Agent.
- T042 Implement Discovery Agent.

## In progress

- None.

## Next up

- T043 Implement Narration Agent.

## Open questions

- Final visual identity/project name.
- Cloud deployment provider.
- Split of 30–50 curated POIs between HCMC and Bangkok.
- Exact list of source publishers accepted for narration.
- Exact production retention duration for rounded or redacted operational
  location-request logs within the accepted 7–30 day range.
- Final user-facing preference taxonomy and editing UI.

## Architecture decisions

- Android native for lowest demo risk.
- Python backend for agent ecosystem.
- Code-orchestrated independent specialist runs.
- Curated-first POI and narration data.
- Room travel packages for offline mode.
- Room version 1 uses stable string identifiers, Unix epoch milliseconds,
  SQLite REAL-backed `Double` coordinates and integer currency minor units.
- Room version 2 adds only nullable `source_label` to stored narrations through
  explicit migration 1→2. Version-1 rows remain valid, both schemas are tracked
  and no destructive migration fallback is enabled.
- Nearby search loads HCMC POIs and aliases from Room in two deterministic
  queries, normalizes Vietnamese text in Kotlin and ranks valid coordinates by
  straight-line Haversine distance without a network fallback.
- POI detail navigation passes only the stable POI ID through `poi/{poiId}`.
  A Hilt-created detail ViewModel loads one transaction-safe POI/menu/Vietnamese
  narration snapshot from Room, exposes Loading, Content, NotFound and Error,
  and never exposes Room entities or user coordinates to Compose. Narration is
  shown only with a nonblank stored source label.
- External navigation uses a generic `ACTION_VIEW` `geo:` Intent through a
  Hilt-bound Android launcher. It validates the stored POI identity and
  coordinates, checks for a compatible activity, handles resolution/launch
  races without crashing and returns typed outcomes to transient detail UI.
  The replaceable no-op analytics hook receives only POI ID and outcome.
- App-shell connectivity is observed through a replaceable boundary backed by
  `ConnectivityManager`. Online requires both `NET_CAPABILITY_INTERNET` and
  `NET_CAPABILITY_VALIDATED`; callback registration is cancelled with the
  owning Flow and failures remain a controlled Checking state. A separate Room
  Flow selects HCMC package metadata by publication timestamp, version and
  package ID, so connectivity and local-data failures stay independent.
- Firebase uses the official Google Services Gradle plugin only in the app
  module, with the plugin version and Firebase Android BoM managed by the version
  catalog. Only the dedicated development config at
  `android/app/src/debug/google-services.json` is allowed in Git; automatic
  initialization is used, while production/release configuration and
  authentication behavior remain outside T020.
- Email authentication uses a Hilt-bound repository over a Firebase SDK gateway.
  An auth-state listener is registered only while the session Flow is collected
  and Firebase current-user state is the sole session source of truth. Immutable
  models expose only UID, email and verification status; passwords and tokens
  are neither returned nor persisted. Unverified users map to
  VerificationRequired, verified users map to Authenticated, and explicit
  reload/resend/sign-out actions originate only from Profile user actions.
- Google authentication uses Credential Manager's explicit
  `GetSignInWithGoogleOption` button flow at the Activity boundary. The generated
  `default_web_client_id` resource supplies the server client ID. Only a typed
  Google ID custom credential is accepted; its token is exchanged immediately
  through the existing Firebase gateway and is never stored in ViewModel/UI
  state, local persistence or logs. Cancellation is distinct from failure.
  Firebase current-user observation remains the sole persistent session source,
  and the common sign-out path clears both Firebase and Credential Manager state.
- The backend application is created only through a typed FastAPI factory. Its
  required `DATABASE_URL` is stored as a redacted secret and restricted to the
  planned `postgresql+asyncpg` scheme, but T023 opens no database connection.
  `/health` is liveness-only. Safe caller request IDs are preserved; invalid
  values are replaced by UUIDs, and all application JSON errors share a typed,
  sanitized envelope containing the response request ID.
- Backend authentication is a deterministic replaceable service. The production
  adapter lazily creates a uniquely named Firebase Admin app configured with the
  required expected project ID and ADC, then passes that app explicitly to
  `verify_id_token` with revocation checking enabled. Synchronous SDK work runs
  outside the event loop. Routes receive only an immutable validated UID;
  decoded claims and credentials never cross the adapter boundary.
- POI-owned aliases, menus and narrations cascade on POI deletion. Itinerary
  items cascade on itinerary deletion, while a deleted POI sets an optional
  itinerary-item POI reference to null so the user's itinerary item remains.
- Server-owned user, preference, trip, itinerary and itinerary-item records use
  UUID primary keys; curated POIs, sources, menu items and narrations use stable
  bounded text IDs for deterministic future upserts. Preferences are one
  versioned non-null JSONB document per owner because the product taxonomy is
  not yet fixed. POIs use canonical `GEOGRAPHY(POINT, 4326)` storage with a GiST
  index; no user location history is modeled. Composite trip/owner references
  prevent cross-owner itineraries. Retained curated records restrict source
  deletion so provenance cannot disappear silently.
- `/preferences` is the sole private preference resource. GET is read-only and
  returns canonical `{schema_version: 1, preferences: {}, updated_at: null}`
  when no owner row exists. PUT validates before mutation, resolves/creates the
  user with PostgreSQL conflict handling, upserts exactly one preference row
  and commits once. Neither route accepts or exposes UID, token, claim, email or
  database UUID.
- Preference schema version 1 deliberately has no product taxonomy. Its strict
  envelope forbids unknown top-level fields; the generic object permits only
  null, boolean, bounded integer, bounded Unicode string, array and nested
  object. Limits are a 16 KiB serialized envelope, depth 6, key length 64,
  string length 512, 50 entries per array/object, 500 total values and integer
  magnitude at most 10^12. Decimal/non-finite numbers, binary, tuples and
  arbitrary objects fail closed. Validation errors redact preference paths.
- Preference conflicts use server-receipt-order last-write-wins: each committed
  PUT replaces the complete JSONB document; the transaction that commits last
  wins and PostgreSQL supplies `updated_at`. There is no client-clock choice,
  field merge or cross-device silent merge.
- Android preference storage is separate from Room and static packages.
  App-private DataStore holds one strict record per SHA-256 Firebase account
  key: schema/document, monotonic local revision, pending flag and last server
  timestamp. A local edit commits before scheduling. Sign-out immediately hides
  the old record; switching accounts selects a different record; returning to
  the same account restores pending state. Preference DataStore is excluded
  from backup/transfer.
- Authenticated preference networking uses a dedicated typed backend origin
  (`http://10.0.2.2:8000/` only for debug; release unset/cleartext-disabled),
  bounded timeouts/body/media checks and disabled redirects. Firebase token is
  fetched only immediately before request, attached only to that origin,
  force-refreshed at most once after 401 and never persisted or logged. Static
  package OkHttp remains a separate unauthenticated client.
- One unique, non-periodic `preference-sync` WorkManager request requires
  connected networking and bounded exponential backoff. Work Data contains no
  account identity, token, email or document. At execution it reads the current
  verified account and newest complete local snapshot. Pending data is PUT
  before any GET; otherwise GET may refresh cache. A success clears pending only
  when its captured revision still matches, so an edit made in flight remains
  pending and triggers another WorkManager attempt.
- Curated package schema version 1 uses YAML as the canonical authoring format
  and accepts strict JSON through the same typed boundary. Stable lowercase
  hyphenated identifiers are city-prefixed with `hcmc-` or `bkk-`; supported
  city codes are exactly `hcmc` and `bkk`. The generated Draft 2020-12 JSON
  Schema is committed and CI checks it byte-for-byte against the frozen
  Pydantic contract.
- T031 package validation forbids unknown fields, rejects unsupported versions,
  malformed/naive/future timestamps, unsafe identifiers, invalid HTTP(S) URLs,
  duplicate IDs, broken references, city mismatches, non-finite/swapped/out-of-
  city coordinates, floating/negative money, malformed currencies and
  ungrounded narrations. Errors carry file, stable code, entity, optional record
  ID, JSONPath-like field and sanitized message in deterministic order.
- T031 sources preserve source type, label/publisher, URL and available
  publication/retrieval timestamps. POIs retain normalized source links; menu
  rows retain a direct source, matching source type, integer minor units,
  currency and source update timestamp; narrations retain a direct source or
  explicit fallback label. Missing facts remain absent.
- Curated seed validation completes before engine creation. Each package uses
  one async SQLAlchemy transaction in dependency-safe source → POI → link →
  menu → narration order. Stable-ID conflict updates are conditional, so an
  identical second seed does not rewrite rows; absent input never triggers
  deletion. Any late failure rolls back the whole package.
- POI discovery uses one immutable FastAPI-independent request with current city,
  optional whitespace-normalized text/category, plain validated WGS84 origin,
  positive radius capped at 50,000 metres and result limit capped at 20.
  Normalized POIs use deterministic `<provider>:<provider-owned-id>` identity,
  with provider namespaces `curated` and future `google_places`; coordinates,
  metre distance, accepted optional facts, typed source summaries, retrieval
  freshness and curated/external flags are the only public result fields. No
  ORM, GeoAlchemy, raw response, metadata or payload escape hatch is part of the
  contract.
- Provider adapters implement one structural async `discover` protocol.
  `PoiProviderError` carries a frozen canonical failure for timeout,
  unavailable, rate-limited, invalid request, invalid response, misconfigured,
  unsupported or internal errors plus fixed retryability. Adapter deadlines are
  bounded and injected; `asyncio.timeout` normalizes deadline expiry while
  external cancellation propagates unchanged. No retry/backoff is present.
- The curated adapter receives an injected `AsyncSession`, creates no global
  engine/session and performs no writes. One parameterized query builds the
  WGS84 origin in PostgreSQL, uses `ST_DWithin` and `ST_Distance` on the stored
  geography, casts only to read POINT longitude/latitude, applies exact
  case-insensitive category and minimal canonical-name/category text matching,
  fetches one extra POI to signal truncation and orders by distance then POI ID.
  Provenance is outer-joined in the same query, de-duplicated and sorted by
  source ID; publication/retrieval timestamps remain timezone-aware. Google
  Places remains a contract-only future namespace: no client, SDK, API key,
  payload schema, request or production mock exists.
- `GET /pois/nearby` is the only nearby HTTP route. It accepts only `hcmc` or
  `bkk`, finite WGS84 latitude/longitude, radius 1–50,000 metres, limit 1–20 and
  optional query/category normalized by `PoiDiscoveryRequest`; defaults are
  5,000 metres and five results. Bounded truncation uses `is_complete` rather
  than an invented cursor.
- Nearby authentication is optional only when Authorization is absent. A
  supplied Bearer credential is verified through the unchanged Firebase
  boundary and any malformed, invalid, expired or revoked token is rejected;
  UID neither personalizes nor enters the response and no user row is created.
  `/auth/me` remains strictly authenticated and `/health` remains public.
- Each production app creates its async engine/session factory during lifespan,
  connects lazily, disposes the engine at shutdown and gives the curated
  provider one always-closed request session. The read-only route never commits
  or creates tables. Injecting a fake `PoiProvider` bypasses database runtime
  creation entirely.
- Nearby responses are explicit API Pydantic models containing normalized
  provider identity, destination coordinates, `distance_metres`, supported
  optional facts, typed source provenance, retrieval/envelope freshness,
  curated/external flags, returned count and completeness only. Request origin,
  Firebase UID, SQLAlchemy/GeoAlchemy objects, raw payload and arbitrary
  metadata are excluded; unsupported facts remain null.
- Provider invalid-request/rate-limit/timeout/unavailable/misconfigured/
  unsupported/invalid-response/internal failures map respectively to sanitized
  400/429/503/503/503/501/502/500 application errors. Response header/body
  request IDs match, no raw error or SQL is logged, cancellation propagates,
  and no retry/backoff or invented `Retry-After` is added.
- Agent contracts live in `backend/app/agents/contracts/`, split into shared,
  router, discovery, narration, local-culture, itinerary, grounding, composer
  and orchestration modules with one explicit public export surface. Every
  public model is frozen, strict and `extra="forbid"`; strings, identifiers,
  collections, money, finite numbers and timezone-aware timestamps are bounded.
  JSON Schema is generated directly from each Pydantic type, and ordinary JSON
  serialization preserves Unicode. There is no raw payload, arbitrary metadata,
  provider SDK, ORM, exception, UID/token/email, transcript or session escape
  hatch.
- Model-executed agent identity is exactly `router`, `discovery`, `narration`,
  `local_culture`, `itinerary`, `grounding_reviewer` and
  `response_composer`. The application-code orchestrator is not an agent kind.
  Router specialist fan-out is limited to Discovery, Narration, Local Culture
  and Itinerary. The closed MVP intent taxonomy is nearby discovery, POI
  information, local culture, itinerary drafting, general travel help and
  unsupported. Router validation binds each intent to a canonical, unique plan;
  unsupported/general-help intents do not schedule optional specialists.
- Agent request context is deliberately scoped: normalized query, locale,
  supported city and optional unchanged schema-version-1 generic preference
  document are reusable; the exact WGS84 origin exists only in Discovery input
  or the runtime input that will create it. No output contains an origin, full
  transcript, Firebase identity or persistent location history.
- Shared evidence consists of sorted unique typed source and factual-claim
  registries. Stable request, POI, source, evidence, claim, specialist-output
  and itinerary-item IDs reject blanks, control characters and traversal.
  Fact kinds are closed to identity, location, category, distance, description,
  history, culture, menu item, price, rating, opening hours, etiquette and
  itinerary constraint. Every claim references an existing source; price uses
  integer minor units, a three-letter currency and an aware source-update
  timestamp. Missing optional values remain absent/`None` and are never replaced
  with unknown text, zero facts or guessed values.
- Shared safe issue records use the closed codes `invalid_input`,
  `invalid_output`, `insufficient_evidence`, `provider_timeout`,
  `provider_unavailable`, `specialist_timeout`, `specialist_failed`,
  `grounding_rejected`, `partial_result`, `unsupported_intent`,
  `latency_budget_exceeded` and `internal`. They carry only agent stage, code,
  bounded sanitized message and retryability; prompts, provider responses,
  credentials, SQL and exception detail are not representable.
- Router contracts contain only query context and a typed intent/entities/plan
  result. Discovery reuses strict T032 normalized POI shapes, retains metre
  units and represents usable partial provider failure explicitly without
  exposing the input origin. Narration enforces inclusive 100–200-word plain
  text, unique key points and exact source/claim references, while insufficient
  evidence yields content-free limited output. Local Culture allows only
  source-linked culture/etiquette guidance or a content-free limited result.
  Itinerary uses one local date plus an IANA timezone and explicit local times,
  validates ordered non-overlapping candidate-backed stops, records assumptions
  and is always `draft_only=true`; it has no saved-itinerary identity or write
  command.
- Grounding input uses a discriminated union of Discovery, Narration, Local
  Culture and Itinerary outputs. Review output contains only reviewed/approved
  claim IDs, typed rejection reasons, approved specialist-output IDs and safe
  warnings: decisions must be disjoint and cover the declared reviewed set, and
  validation against the request prevents new claim/output IDs. Typed rejection
  reasons include missing source, missing price timestamp, unsupported claim,
  stale evidence and inconsistent evidence; the reviewer cannot author
  replacement factual text.
- Response Composer accepts approved claims/evidence, approved discriminated
  specialist content and safe warnings only. Its coordinate-free plain-text
  output must use approved claim/source IDs and preserve every input warning;
  optional POI presentation fields stay missing. Runtime request/result models
  add a caller-supplied request ID, discriminated per-agent stage records,
  finite nonnegative `duration_ms`, and `success`/`partial`/`failed`
  consistency. Partial requires usable composer output plus an issue; success
  rejects failures; failed rejects final output. No model/token/trace usage was
  speculated because tracing and usage belong to T049.
- T040 adds contracts and validation only. It adds no OpenAI dependency,
  prompts, instructions, tools, Runner calls, retries, timeouts, network or
  database access, FastAPI route, migration, provider implementation or Android
  change.
- T041 owns `backend/app/agents/router/` and pins `openai-agents==0.18.3` in
  normal runtime requirements. Its public `RouterExecutor` protocol accepts one
  validated `RouterRequest` and returns only a revalidated `RouterOutput`; SDK
  result objects, IDs, usage, traces, raw JSON and exception details do not
  cross this boundary.
- The configured adapter creates one stable Router agent with static
  version-controlled instructions, `output_type=RouterOutput`, empty tools,
  handoffs and MCP servers, `tool_choice="none"`,
  `parallel_tool_calls=false`, one maximum turn and no model retry. `Runner.run`
  receives no session, conversation ID or previous response ID. Each run uses
  `RunConfig(tracing_disabled=true, trace_include_sensitive_data=false)` until
  T049.
- Router model configuration is read lazily from nonblank `OPENAI_API_KEY` and
  explicit `OPENAI_ROUTER_MODEL`; neither field was added to global FastAPI
  settings. Missing configuration performs no model call. Model exceptions,
  unexpected types and contract-invalid output use the deterministic fallback;
  caller cancellation propagates and never triggers fallback.
- Router model input is compact deterministic Unicode JSON containing exactly
  the four `RouterRequest` fields. It adds no identity, token, coordinates,
  transcript, provider/database data or environment values. Safe logs contain
  only operation, model/fallback path, a stable reason and selected intent.
- The pure fallback normalizes whitespace, case, Unicode and Vietnamese
  diacritics only for matching. Its fixed precedence is itinerary drafting,
  local culture, nearby discovery, POI information, general travel help, then
  unsupported. Vietnamese accented/unaccented and English signals cover all six
  intents; isolated generic `plan`/`information` language is insufficient.
- Fallback plans are exactly Discovery; Narration; Local Culture; Discovery then
  Itinerary; empty; and empty for the six intents respectively. Unsupported
  input receives a safe clarification. City extraction accepts only HCMC/Ho Chi
  Minh/Sài Gòn and Bangkok/Băng Cốc aliases, preserves an explicit request city,
  declines conflicting query cities and never infers city from locale or
  preferences. It invents no category, query term, POI ID or itinerary
  constraint.
- T041 adds no FastAPI route, database/provider/Firebase behavior, Android
  change, specialist execution, reviewer/composer behavior, orchestration,
  tracing export or usage accounting. T043 through T050 remain unimplemented.
- T042 owns `backend/app/agents/discovery/`. Its public structural
  `DiscoveryExecutor` accepts one validated `DiscoveryRequest`, returns only a
  revalidated `DiscoveryOutput`, and raises one sanitized typed
  `DiscoveryExecutionError` only when a total POI failure leaves no usable
  candidate. SDK result/tool objects, rows, spatial values, raw JSON,
  exceptions, traces, usage and arbitrary metadata never cross the boundary.
- Each run creates its own registry over an injected T032 `PoiProvider` and
  injected `PoiMenuReader`; no global engine, provider, session or mutable run
  state exists. The zero-argument agent tools derive city, origin, radius,
  limit, query, category and selected curated provider IDs only from the
  validated request/registry. POI runs exactly once; menu runs at most once
  only for requested menu/price facts and never accepts model-authored IDs.
- `SqlAlchemyPoiMenuReader` receives an `AsyncSession` owned by its caller and
  performs one bounded parameterized join over selected POIs, menus and sources
  ordered by POI ID then menu item ID. It creates no engine, commits no write,
  performs no N+1 read and preserves cancellation. Current zero-menu HCMC and
  Bangkok packages are valid empty successes.
- Private tool models are strict, frozen, bounded, recursively
  extra-forbidden, JSON-serializable and have no `Any`, raw payload or metadata
  escape hatch. Unsupported/malformed source or tool data fails closed. Stable
  provider/menu failures map to Discovery-stage timeout, unavailable or
  invalid-output issues without exception text.
- Evidence assembly is pure and deterministic: normalized real sources are
  de-duplicated by exact identity; source timestamps are unchanged; SHA-256
  derivations produce stable claim/evidence IDs without clocks or randomness.
  Claims are created only for requested facts supported by normalized tools.
  Menu/price claims use the real menu source, integer minor units, currency and
  source freshness. Missing rating, opening hours, menu and price create no
  claim, and deterministic distance has no synthetic source.
- Candidate order is exactly T032 PostGIS distance then stable-ID order; no
  model or assembler reranking occurs. T040's prior validator incorrectly
  required globally lexicographic candidate IDs, conflicting with valid
  distance order, so T042 narrowly relaxed that check to uniqueness while
  retaining the same public fields/schema and all evidence/partial invariants.
- The configured Discovery agent has exactly two normalized function tools,
  `output_type=DiscoveryOutput`, no handoffs, sessions, MCP, hosted tools or
  agent-as-tool behavior, `parallel_tool_calls=false`, three maximum turns and
  zero model retry. `OPENAI_API_KEY` plus explicit
  `OPENAI_DISCOVERY_MODEL` are read lazily; missing/blank configuration runs
  normalized tools deterministically. Tracing and sensitive trace data remain
  disabled until T049.
- After every model attempt, the same registry completes only missing
  operations. Exact output closure requires every candidate, source, claim,
  failure, order, completeness and truncation value to equal deterministic
  registry output. Plain text, model/SDK failure or any invented/modified value
  returns that deterministic output without another successful provider/menu
  call. Caller cancellation always propagates.
- POI success plus menu failure or truncation retains usable candidates and
  evidence as `PARTIAL`; zero menus and absent optional facts remain
  `COMPLETE`. Empty successful POI search is empty `COMPLETE`. Total POI
  failure never fabricates a partial result. Output and safe logs contain no
  request origin or final user-facing prose; logs contain only path, city,
  candidate count, completeness and stable failure code.
- T042 adds no FastAPI route, migration, schema field, curated production
  content, Android change, Google Places adapter, narration, reviewer,
  composer, orchestration, tracing export, usage accounting or retry policy.
  Alembic now preserves already-imported application logger enablement during
  in-process migration tests; this one-line isolation fixes the pre-existing
  T041 CI log-capture failure without changing Router behavior.

## T002 baseline consistency review

| Area | Accepted baseline |
| --- | --- |
| Product scope | Vietnamese-first native Android travel assistant; text output initially, with voice limited to speech-to-text input. |
| Target users | Vietnamese domestic travelers plus selected outbound demo cases. |
| Supported cities | Ho Chi Minh City is primary and Bangkok is the international demo; 30–50 curated POIs total, with the city split unresolved. |
| Online/offline | Online mode may use approved provider adapters; offline mode uses only downloaded, versioned travel-package data and offers no new AI generation. |
| Curated data | Curated POI, menu, narration and local-culture records are the trust anchor; external sources may enrich them with provenance and freshness. |
| Grounding | Unavailable facts are never invented; unsupported claims are removed, missing fields stay missing and historical/cultural claims need sources or an explicit fallback label. |
| Stack | Kotlin/Jetpack Compose native Android; Python 3.12/FastAPI backend; PostgreSQL/PostGIS database; OpenAI Agents SDK runtime. |
| Authentication | Firebase Authentication with email/password and Google; token verification and authorization are deterministic services, not agents. |
| Agent runtime | Router → Discovery → deterministic ranking → Grounding Reviewer → Response Composer; Narration, Local Culture and Itinerary are optional specialist agents. |
| Deterministic services | Location acquisition, speech recognition, distance, opening-hours evaluation, ranking, authentication/authorization, offline search and package synchronization remain application services. |
| Privacy/permissions | No server-side exact location history or stored voice audio; foreground location and microphone permissions are requested only at their feature points; background location is outside MVP. |
| Task sequence | T000 through T004, T010 through T025, T030–T035 and T040–T042 are complete; T043 is next but unassigned. |
| Implementation state | The Android architecture shell, five-destination Navigation Compose shell, centralized Material 3 theme and Room version-2 offline schema/core DAO layer are present under `android/`. A bundled HCMC demo seed imports safely and idempotently and still contains no menu or narration records. Explore has user-triggered, one-shot foreground location context plus offline Room search by name, alias and category, Vietnamese normalization and deterministic straight-line distance ranking. Nearby POIs open local detail screens resolved by stable ID; missing optional data is omitted, while stored prices include freshness dates and stored narration requires a real source label. Explore location/query state survives Back. Loaded details expose an explicit `Dẫn đường` action that validates the stored POI destination and opens any compatible external `geo:` handler, with typed failures, localized retryable UI and coordinate-free no-op analytics. Validated connectivity is observed without network requests; the shell explicitly shows Offline while local Room search/detail remains usable. Downloads now exposes HCMC-only user-triggered package sync with WorkManager, strict manifest/artifact validation, resumable app-private staging, exact byte/SHA-256 verification and one-transaction Room activation. Active package metadata/data survives process restart and every failed update; bundled seed never replaces a valid downloaded package. Assistant still explains its Internet-only future behavior, while external navigation is never disabled solely because connectivity is Offline. The dedicated Firebase development configuration is integrated only for debug and initializes the default Firebase app automatically. Profile implements email/password registration and sign-in, verification-email delivery/resend, explicit verification refresh and a common sign-out path. It also implements explicit Google authentication through Credential Manager; Google ID credentials are exchanged only ephemerally for Firebase, cancellation is controlled, Firebase remains the single session source of truth and sign-out clears Credential Manager state. Manual development-project validation confirms email/password and Google sessions restore after force-stop/cold launch; Explore and local Room data remain independent of authentication. A taxonomy-neutral preference repository now keeps strict per-account DataStore documents and revision/pending metadata, while unique connected WorkManager sync obtains Firebase tokens only at request time and protects newer in-flight edits. Production/release Firebase and backend hosting configuration remain absent. There is no background tracking or exact-location persistence. The backend builds and verifies deterministic static travel-package JSON directly from validated T031 input, with a committed two-POI HCMC artifact and no package HTTP endpoint; Android-to-backend transport is implemented only for private preferences. Local PostgreSQL/PostGIS infrastructure exists. The backend FastAPI factory, validated settings, liveness endpoint, request IDs, sanitized error envelope and Firebase Admin ID-token verification are implemented; `/auth/me` exposes only UID and `/health` remains public and database-free. Canonical authenticated GET/PUT `/preferences` return or transactionally replace one strict bounded version-1 JSON document by verified UID without exposing identity. Typed SQLAlchemy metadata and an async Alembic migration create the ownership, itinerary, curated provenance, menu, narration and PostGIS POI schema. The strict version-1 curated pipeline validates and transactionally seeds sourced HCMC/Bangkok starter packages. A provider-neutral async discovery contract normalizes bounded nearby requests, namespaced result identity, provenance/freshness and canonical errors/timeouts. Its first injected-session curated adapter performs one read-only parameterized PostGIS query with deterministic distance/ID ordering and no payload/ORM escape. Canonical `GET /pois/nearby` validates bounded HTTP query parameters, supports anonymous or strictly verified optional Firebase authentication, and returns only normalized curated POIs with metre distance, provenance/freshness, returned count and completeness. Its app-owned lazy engine and request session lifecycle do not persist request origins or commit writes. The independent Discovery Agent calls that injected provider and a selected-curated menu reader, assembles deterministic closed evidence, preserves distance order/missing values and returns no final prose. Live Google Places, Android nearby transport, Narration and end-to-end orchestration are not implemented. |

## Session notes

After each task, move it to Completed and set exactly one Next Up task.

T001 completed on 2026-07-19. It added a read-only repository verification
script and expanded Apple Silicon setup instructions. Git, Java 21, Android
Studio, Android SDK platform/build-tools/command-line tools, adb, an ARM64 Google
Play AVD, emulator acceleration, Gradle wrapper, Python 3.12, Node.js LTS, npm,
Codex CLI, Docker CLI and Docker daemon all passed. A physical Android device is
still required for later GPS/microphone behavior testing, but is not a T001
blocker.

T002 completed on 2026-07-21. Accepted context and ADRs now state the locked
runtime path, optional specialist roles, deterministic-service boundary,
grounding policy and actual starter-project state consistently. No application
source or build configuration was changed.

T003 completed on 2026-07-21. It added a single-service Docker Compose setup for
local PostgreSQL/PostGIS, a named persistent volume, explicit health check,
loopback-only host port and safe sample environment values. Compose validation,
database health, SQL connectivity, PostGIS availability and volume persistence
were verified without adding backend application code.

T004 completed on 2026-07-21. GitHub Actions now checks the existing Android
starter with debug lint, JVM unit tests and debug assembly, and checks the empty
backend boundary with pinned Ruff, mypy and pytest tooling plus a placeholder CI
smoke test. Workflow YAML parsing, read-only permissions, cache inputs and all
job-equivalent local commands passed. A deliberate temporary pytest failure
returned a non-zero exit status and was removed. The first remote CI run failed because sdkmanager was not on PATH. A follow-up CI fix invoked sdkmanager through ANDROID_HOME, and the subsequent GitHub
Actions run passed both Android and backend jobs.

T010 completed on 2026-07-21 by reconciling the existing Kotlin/Compose starter
without recreating the project or changing its package, module, SDK, Gradle
wrapper or dependencies. Package/namespace and application ID remain
`com.kltn.travelassistant`, with `.MainActivity` as the single launcher activity.
Debug assembly, JVM tests and the focused CI-equivalent lint/test/build command
passed. The debug APK installed on the authorized
`Pixel_7_API_36_Google_Play_ARM64` emulator, Activity Manager launched
`com.kltn.travelassistant/.MainActivity` with `Status: ok`, the process remained
alive with the activity top-resumed and focused, and no immediate package fatal
exception appeared in a focused logcat scan. The clarified instrumented Android
app identity smoke test passed on the emulator. At T010 completion, the
generated starter UI remained minimal and T011 still owned the architecture
shell; later tasks owned navigation, theme and product features.

T011 completed on 2026-07-21 by adding the minimal Android architecture shell
without changing the app identity, module/activity count, SDK, Gradle wrapper,
AGP, Kotlin or Compose versions. The app now has a Hilt application and entry
point, a singleton-bound repository contract/implementation, and a Hilt-created
sample ViewModel that exposes immutable `StateFlow<HomeUiState>`. The starter
Compose UI only observes and renders that state. Three JVM tests cover initial
state, repository-to-ViewModel propagation and public-state immutability. JVM
tests, lint, the CI-equivalent lint/test/assemble command, the existing identity
instrumented test, installation and a cold emulator launch all passed. The
first lint attempt selected a VS Code runtime without `bin/jlink`; after the
daemon was stopped, the same check passed using the required Android Studio JDK
21. Activity Manager reported `Status: ok`, the process remained alive with
MainActivity top-resumed/focused, and focused logcat inspection found no Hilt,
binding, generated-component or AndroidRuntime fatal error. Navigation,
persistence, networking and product features remain incomplete and belong to
later tasks.

T012 completed on 2026-07-21 by adding one Navigation Compose host and a
Material 3 navigation bar for Explore, Assistant, Itinerary, Downloads and
Profile. Canonical routes are centralized and unique, Explore is the start
destination, repeated selections do not duplicate a top-level destination, and
Back from a non-start destination returns to Explore using Navigation's own
back stack. Explore retains the T011 Home/ViewModel state boundary; the other
destinations are localized placeholders only. Complete provisional light/dark
fallback schemes, typography and spacing are centralized under `ui/theme`,
without claiming final identity or branding. Three destination-contract JVM
tests and three Compose navigation tests were added while the three T011 JVM
tests and identity instrumented test were preserved. The first connected test
run revealed that the existing Espresso 3.5.1 reflected a removed Android 36.1
input API; updating to stable Espresso 3.7.0 and JUnit extension 1.3.0 resolved
the compatibility failure. JVM tests, connected instrumented tests, debug lint,
debug assembly, install and a cold launcher-activity start all passed on the
Pixel API 36.1 emulator. Destination features remain unimplemented by design.

T013 completed on 2026-07-21 with the initial version-1 Room database, all nine
accepted local entities, aggregate-oriented DAOs and singleton Hilt database/DAO
providers. The schema is exported to a tracked JSON file, starts directly at
version 1 and has no destructive-migration fallback. Field-level choices not
fixed by the context use stable string IDs, epoch-millisecond timestamps,
`Double` coordinates and integer currency minor units. Package metadata remains
limited to the accepted city/version/manifest/publication fields; no active or
latest-package behavior was invented. Six isolated in-memory Room tests cover
POI/content queries, both deliberate foreign-key delete behaviors, ordered
itinerary aggregates and cascading deletion, package lookup, deterministic sync
ordering/state updates/removal and per-test isolation. JVM tests, instrumented
tests, lint and debug/test APK assembly passed. Seed data/importing, FTS, product
repositories/UI, synchronization workers and networking remain outside T013.

T014 completed on 2026-07-21 with a tracked, deterministic HCMC demo seed
containing five POIs and five English aliases. Kotlin serialization parses a
typed document strictly; validation rejects malformed input, unsupported city
values, invalid coordinates, duplicate identifiers, invalid monetary values and
missing POI references before entity conversion. The importer checks bundled
package ID/version metadata for durable idempotency and writes all content plus
the completion marker in one Room transaction. It is started asynchronously
from the Hilt application boundary and reports concise imported, skipped or
failed status without exposing seed content or exceptions. JVM tests cover
strict parsing and independent validation. Four in-memory Room importer tests
cover the real asset, five-POI import, unique identifiers, valid child
references, stable second-run counts, package metadata, malformed input,
invalid foreign keys and late-write rollback. JVM tests, lint, all 14
instrumented tests, the CI-equivalent build, installation and two cold emulator
launches passed; the first launch imported five POIs and the second reported the
durable already-imported path. Room remains at version 1 and its exported schema
is unchanged. POI UI, search, location, networking and later-task behavior
remain outside T014.

T015 completed on 2026-07-22 with a user-triggered foreground location section
on Explore. Activity Result permission launchers remain in `MainActivity`; cold
launch and navigation never request permission. Coarse permission is accepted,
denial exposes retry and settings recovery, and the Hilt-bound `LocationClient`
uses the platform `LocationManagerCompat.getCurrentLocation` API for one current
fix with cancellation and a 15-second timeout. Exact coordinates exist only in
immutable in-memory state and are neither displayed, persisted, transmitted nor
logged. JVM tests cover Idle, Loading, Available, PermissionDenied and Error,
retry, immutable state, duplicate suppression and cancellation. Compose tests
cover cold-launch Idle plus all location render states while preserving bottom
navigation. JVM tests, lint, all 20 instrumented tests and the CI-equivalent
command passed. Runtime validation on the Pixel API 36 emulator confirmed an
ungranted cold launch, denial and retry, coarse-only handling, a precise
one-shot success with 5 m reported accuracy, immediate request unregistration,
and a second cold launch with no automatic request. The emulator accepted the
HCMC geo-fix command but continued to report its default simulated coordinate;
its network provider was disabled, so the coarse-only acquisition timed out into
the recoverable Error state. A physical-device coarse/precise GPS check remains
recommended. Nearby POI search and distance ranking remain outside T015.

T016 completed on 2026-07-22 with an offline-only nearby search boundary backed
by the existing Room version-1 POI DAO. It loads HCMC POIs and all relevant
aliases without a query per POI, normalizes Vietnamese diacritics and `đ`
deterministically, matches canonical names, aliases, stored categories and
localized category labels, excludes invalid stored coordinates and ranks valid
matches by Haversine distance with stable tie ordering. Explore now exposes
separate WaitingForLocation, Loading, Content, Empty and Error search states,
keeps the query in memory, refreshes after each successful one-shot location and
shows locale-formatted kilometres with a straight-line-distance notice. No Room
entities or exact coordinates enter rendered result models, and search failures
do not replace location permission state. Room remains version 1 and the exported
schema is unchanged. Pure JVM tests cover normalization, distance, formatting,
ranking and fake-repository ViewModel behavior; in-memory Room and Compose tests
cover bundled-seed search, DAO integration and UI states. `./gradlew test`, the
CI-equivalent lint/test/assemble command and all 28 connected emulator tests
passed. POI detail navigation, narration, FTS, maps, networking and package
downloads remain outside T016.

T017 completed on 2026-07-22 with clickable nearby results and one non-top-level
`poi/{poiId}` destination. The route carries only the encoded stable POI ID; a
Hilt detail ViewModel resolves a transaction-safe Room snapshot through a
replaceable repository and exposes explicit Loading, Content, NotFound and Error
states with retry. Back returns to Explore with its in-memory location and query,
and the bottom navigation bar is hidden on detail. Missing optional POI
attributes, menu and narration sections are omitted instead of synthesized.
Currency formatting uses each ISO currency's real fraction digits, including
zero-decimal VND, and every displayed menu price includes its source type and
stored update date. Room moved from version 1 to 2 solely to add nullable
`source_label` to local narrations through explicit migration 1→2; schemas 1 and
2 are tracked, old POI/narration rows survive, and no destructive fallback is
enabled. Seed DTO mapping accepts an optional nonblank source label, while the
bundled JSON remains byte-for-byte unchanged with five POIs, five aliases, no
menus and no narrations. JVM tests, lint, the CI-equivalent build and all 40
connected emulator tests passed. Runtime validation on the Pixel API 36.1
emulator acquired the HCMC foreground location, opened two correct seeded POIs,
returned to the preserved Explore results, hid bottom navigation, omitted absent
sections and produced no focused Room migration, Navigation, Hilt, fatal-runtime
or exact-coordinate log match. External map navigation remains T018.

T018 completed on 2026-07-23 with an explicit `Dẫn đường` action on loaded POI
details. The Room-backed detail model now exposes a POI-owned destination target
without rendering coordinates or using the user's current location. A
Hilt-bound Android launcher validates nonblank identity/name, finite coordinate
bounds, creates a provider-neutral locale-independent `ACTION_VIEW` `geo:` URI,
checks package resolution and controls missing-activity, launch-race, security
and malformed-target failures. The detail route owns transient localized errors
and allows retry; success clears prior errors. A replaceable analytics hook
records only POI ID plus requested/outcome events, with a no-op production
implementation and no SDK or coordinate logging. The manifest adds only the
minimal `geo:` package-visibility query and no permission. JVM tests, debug
lint, the CI-equivalent build and all 50 connected emulator tests passed. The
debug APK installed and cold-launched with the process alive and no focused
AndroidRuntime fatal error. Embedded maps, route calculation, tracking,
networking and explicit offline UI state remain outside T018.

T019 completed on 2026-07-23 with a Hilt-created app-shell state owner that
combines independent connectivity and local-package metadata streams.
`ConnectivityManager` observes the active/default network without making a
request and classifies it Online only with both Internet and validated
capabilities; initial state, callbacks, expected failures and callback cleanup
are explicit and tested. A Room Flow observes the latest deterministic HCMC
package selection and maps only version plus publication timestamp into UI
state. The shell shows a reusable offline warning without blocking content,
with in-memory dismissal scoped only to the current Offline episode. Package
freshness is separate, compact informational content shown only in Downloads;
valid versions remain visible when an invalid publication date is omitted.
Room-backed search, Vietnamese filtering, POI detail, Back and external `Dẫn
đường` remain usable Offline.
Assistant and Downloads show localized Internet-required explanations without
exposing unimplemented actions. JVM tests, lint, the CI-equivalent build and all
64 connected emulator tests passed.
Runtime validation covered validated-network launch, loss/restoration callbacks,
five retained local POIs, offline filtering/detail/navigation and cold offline
startup. Room remains version 2; schemas 1 and 2 and the bundled seed are
unchanged. Networking, downloads, authentication and AI remain unimplemented.

T020 completed on 2026-07-23 by integrating the dedicated Firebase development
client configuration only into the Android debug variant. Google Services plugin
4.5.0 is declared through the version catalog, applied only to the app module,
and uses the debug-specific `google-services.json`. Firebase Android BoM 34.16.0
aligns the sole Firebase product dependency, Firebase Authentication 24.2.0, as
foundation for T021 without any authentication API calls or UI. Standard
FirebaseInitProvider automatic initialization creates the default Firebase app.
A JVM configuration-policy test verifies the exact debug path and package while
rejecting root, main, release, production, staging and local configs. A
network-free instrumented smoke test verifies the default app, application
context and nonblank required options without hardcoded identifiers. JVM tests,
lint, the CI-equivalent build and all 65 connected emulator tests passed. The
debug APK installed and cold-launched with `Status: ok`; the process remained
alive, existing Explore content rendered and focused log checks found no
Firebase initialization/resource error, Hilt/AndroidRuntime fatal, or supplied
Firebase identifier value. CI needs no production config, Firebase repository
secret or server credential. Room remains version 2; schemas 1 and 2 and the
bundled seed are unchanged. Email/Google authentication, backend token
verification and other Firebase products remain unimplemented.

T021 completed on 2026-07-24. A
Hilt-created Profile ViewModel observes a Firebase-backed repository session
Flow and renders Checking, SignedOut, VerificationRequired, Authenticated and a
controlled observation Error state inside the existing Profile destination.
Registration trims and validates email without trimming passwords, requires the
Firebase baseline six-character password and matching confirmation, creates the
account, and requests a localized verification email. Delivery failure keeps
the newly created unverified session and exposes resend instead of encouraging
duplicate registration. Sign-in reloads the Firebase user before mapping
verification status; explicit refresh, resend and sign-out are duplicate-safe.
Firebase exceptions map to stable localized errors, including a neutral invalid
credentials message, and no password/token/credential is logged, returned or
persisted. Explore and Room data remain independent of authentication. All 92
JVM tests, lint, the CI-equivalent build, Google Services processing and all 73
emulator tests passed; the existing Firebase initialization smoke test remains
green. Manual validation against the Firebase development project confirmed
localized validation, live registration, verification delivery/resend,
unverified restoration as VerificationRequired, explicit refresh after
verification, verified restoration as Authenticated, sign-out, verified
email/password sign-in and the neutral incorrect-password error. Explore and
local Room data remained intact after sign-out, and no password, Firebase token
or credential was committed or logged.

T022 completed on 2026-07-24. Profile now has an explicit
`Tiếp tục với Google` action that starts only from user interaction and uses
Credential Manager's `GetSignInWithGoogleOption` button flow with the generated
`default_web_client_id`. The action displays Google's official full-color “G”
asset unchanged at 20 dp with decorative accessibility semantics, while keeping
the existing full-width Material 3 button behavior. A Hilt-bound coordinator
receives the Activity only for the active request, accepts only the Google ID
custom credential type, parses it through `GoogleIdTokenCredential.createFrom`
and immediately exchanges the ephemeral ID token through the existing Firebase
gateway. Credential Manager cancellation is harmless and retryable; missing
configuration, no credential, provider unavailability, malformed credentials,
Firebase collisions, disabled accounts, throttling, network failures and
unexpected failures map to stable Vietnamese UI messages without exposing raw
exceptions or credential data. Firebase current-user observation remains the
single persistent session source, including restoration after force-stop and
cold launch. The common email/Google sign-out path signs out Firebase and clears
Credential Manager state; clearing failure leaves the app SignedOut with a
recoverable warning. Credential Manager 1.6.0 and googleid 1.2.0 are managed
through the version catalog, with the existing Firebase BoM/auth dependency
unchanged. All 105 JVM tests, lint, the CI-equivalent build, Google Services
processing and all 77 emulator tests passed. Manual validation on the authorized
Google Play emulator confirmed the centered multicolor logo in both light and
dark themes, no automatic picker, explicit Credential Manager launch, harmless
cancellation, live Google/Firebase authentication, restored session after cold
launch, sign-out with renewed account selection, preserved Explore/Room package
data and location permission, and a localized offline authentication failure.

T023 completed on 2026-07-27. The backend now pins its minimal production and
test dependencies and exposes a typed `create_app` factory without module-level
application construction. Settings are immutable, load from environment, require
a redacted `DATABASE_URL` using `postgresql+asyncpg`, and constrain environment
and log-level values. `GET /health` returns only safe service liveness metadata
without touching PostgreSQL or another service. Pure ASGI middleware validates
or generates `X-Request-ID` values, keeps them request-scoped and adds them to
success and controlled-error responses. Typed handlers normalize HTTP,
validation and unexpected failures into one sanitized JSON envelope; the 500
path exposes no exception detail. Tests cover settings, independent factories,
database-free health, request-ID validation and all error paths. CI now caches
both dependency files and applies strict mypy checks to application and test
code. Firebase verification, database connectivity/schema/migrations, protected
routes, provider adapters, AI runtime and Android networking remain unimplemented.

T024 completed on 2026-07-27. Backend settings now require a trimmed, bounded
`FIREBASE_PROJECT_ID` while keeping `DATABASE_URL` redacted and credentials out
of application configuration. A typed verifier protocol returns only a frozen
UID principal. Its Firebase Admin 7.5.0 production adapter lazily initializes a
uniquely named app with the expected project ID and ADC, explicitly verifies ID
tokens with `check_revoked=True` in a worker thread, validates the decoded UID
and normalizes invalid/expired/revoked/disabled credentials separately from
certificate, credential and network unavailability. `GET /auth/me` strictly
requires Bearer authentication, uses the existing request-ID error envelope and
returns only `uid`; `/health` remains public and database-free. Deterministic
fake/mocked tests cover settings, parsing, errors, privacy, cancellation,
concurrency and independent factories without credentials or network access.
At T024 completion, Android still did not obtain or transport ID tokens to the
backend, and PostgreSQL connectivity/schema/migrations remained incomplete.

T030 completed on 2026-07-27. The backend now pins SQLAlchemy 2, Alembic,
asyncpg, GeoAlchemy2 and the greenlet runtime required by SQLAlchemy's async
bridge. Typed declarative models cover users, one versioned JSONB preference
document per owner, trips, owned itineraries with ordered items, stable curated
POIs, normalized sources and POI-source links, menu items and grounded
narrations. User-owned records use UUIDs while curated records keep stable text
IDs for future idempotent imports. Database constraints enforce unique Firebase
UIDs and preferences, cross-owner trip/itinerary rejection, unique itinerary
positions, nonnegative integer prices, uppercase three-letter currencies and a
source or explicit fallback label for every narration. POIs store canonical
`GEOGRAPHY(POINT, 4326)` coordinates with a GiST index; no user-location history
is stored. The async Alembic environment reads only `DATABASE_URL`, does not
initialize Firebase, installs PostGIS idempotently when permitted and leaves
the shared extension on downgrade. Its initial revision upgrades, downgrades
and upgrades again cleanly on a throwaway real PostGIS database without seed
rows. Source deletion is restricted while curated content retains it, POI
deletion preserves itinerary items through `SET NULL`, and itinerary deletion
cascades to items. Model import and FastAPI `/health` remain database-free.
Runtime engine/session creation, APIs, user provisioning, seed/import behavior
and T031 work remain intentionally unimplemented.

T031 completed on 2026-07-27 with repository-owned curated package schema
version 1. YAML is canonical and JSON is accepted through the same frozen,
extra-forbidden Pydantic boundary; a generated Draft 2020-12 JSON Schema is
committed with deterministic write/check commands. Validation is entirely
offline and reports sorted, sanitized file/code/entity/record/JSONPath errors
for structural, identifier, reference, city, timestamp, URL, coordinate,
provenance, narration and integer-money failures before database access. Stable
city codes are `hcmc` and `bkk`. Starter packages are `hcmc-starter-v1` with two
POIs/two sources and `bkk-starter-v1` with one POI/one source. They deliberately
contain no unverified menus or AI-authored narrations and do not claim the
future 30–50 POI target.

The async SQLAlchemy seed command uses only `DATABASE_URL`, refuses targets not
visibly local/development/test, converts validated longitude-first coordinates
to `GEOGRAPHY(POINT, 4326)`, and writes source → POI → source-link → menu →
narration in one transaction. Stable-ID upserts update changed supported fields
without deleting absent rows; unchanged second runs do not rewrite records, and
late failures roll back the package. Real disposable PostGIS tests confirmed
both cities remain separate, row counts remain stable on second import, spatial
type/SRID, provenance/freshness mappings, deterministic updates, rollback, and
zero writes to user-owned tables. CI now checks dependency consistency, schema
drift and both packages before pytest. FastAPI CRUD/nearby APIs, runtime route
sessions, provider adapters and Android travel-package synchronization were
still incomplete at T031 completion.

T032 completed on 2026-07-27 with a frozen FastAPI-independent POI discovery
request, typed normalized result/source/envelope models, deterministic
provider-namespaced identities and one structural async provider protocol.
Coordinates are finite plain WGS84 values; radius is explicit metres capped at
50 km, result limit is capped at 20, timestamps are timezone-aware, arbitrary
payload fields are forbidden and missing rating/price/hours remain absent.
Canonical provider failures cover timeout, unavailable, rate-limited, invalid
request/response, misconfigured, unsupported and internal outcomes with fixed
safe messages and retryability. Each adapter receives a bounded deadline;
deadline expiry is normalized and caller cancellation is never converted.

The first adapter reads only curated T030 tables through an injected
`AsyncSession`. Its single parameterized query uses PostGIS geography
`ST_DWithin`/`ST_Distance`, reads WGS84 POINT coordinates through an explicit
geometry cast, filters city plus optional category/canonical-name/category text,
fetches one extra candidate for truncation and orders by distance then stable
POI ID. The same query outer-joins sources, avoiding N+1 access; typed source
summaries are unique/sorted and preserve URL, publisher, publication and
retrieval timestamps. Real disposable PostGIS tests cover HCMC/Bangkok,
filtering, limits, distance/tie ordering, provenance/freshness, no mutations,
no user-table access, one-query behavior, timeout and cancellation. Google
Places remains unimplemented and requires no key/client/network call. No
FastAPI route, runtime route session, migration, curated production package or
Android file changed; nearby HTTP behavior remains T033.

T033 completed on 2026-07-27 with the single canonical
`GET /pois/nearby` route. HTTP inputs accept only `hcmc`/`bkk`, finite WGS84
coordinates, optional query/category, integer radius default 5,000 and bounded
at 50,000 metres, and integer limit default five and bounded at 20. The route
constructs the frozen T032 request so whitespace/category normalization and
provider bounds remain centralized. Validation uses the existing sanitized
422 envelope. Bounded truncation is exposed as `is_complete`; no alias, offset
or cursor was added.

Missing Authorization is accepted without calling Firebase. Any supplied
header uses the same Bearer parser/verifier as strict `/auth/me`; malformed,
invalid, expired and revoked credentials remain controlled failures rather than
anonymous access. Nearby results do not use or expose UID and create no user
row. Explicit response models expose normalized provider identity, canonical
destination data, destination coordinates, `distance_metres`, supported
optional facts, typed provenance, timezone-aware retrieval/envelope freshness,
curated/external flags, count and completeness. They exclude request origin,
ORM/spatial values, raw provider data and arbitrary metadata; unsupported
rating/price/hours remain null.

Each production app creates a lazy async SQLAlchemy engine/session factory in
lifespan, disposes it on shutdown and gives `CuratedPoiProvider` one
always-closed request session without commit. Injected fake providers bypass
database runtime construction, while `/health` remains connection-free.
Canonical provider failures map to stable sanitized 400/429/501/502/503/500
errors with matching request IDs; raw errors, SQL, URLs, tokens, exact origins,
queries and UID are not logged, cancellation propagates and no retry metadata
is invented. Deterministic API/runtime tests and migrated, seeded disposable
PostGIS endpoint tests cover both cities, filters, radius/limit, distance/tie
ordering, SRID-derived coordinates, provenance/freshness, duplicate prevention,
session cleanup and no database mutation. Google Places and Android networking
remain unimplemented.

T033 required checks passed on Python 3.12.13: dependency installation and
`pip check`, Ruff, strict mypy over app/tests, Alembic head, curated schema
drift check, both package validations, all 197 pytest tests, compileall and
repository diff validation. Manual loopback Uvicorn validation against the
healthy migrated/seeded local PostGIS database returned 200 for `/health`,
anonymous HCMC/Bangkok nearby calls and filtered nearby search; invalid bounds
returned controlled 422, malformed optional Authorization returned controlled
401 and unauthenticated `/auth/me` remained 401. Live access records contained
only `/pois/nearby` without query strings, confirming origin/query redaction.

T034 completed on 2026-07-27 with separate immutable Pydantic contracts for
manifest schema version 1 and artifact/data schema version 1. The offline
builder validates exactly one canonical T031 YAML package before creating an
output directory or writing an artifact; it never reads PostgreSQL, calls the
nearby API, initializes FastAPI/Firebase/provider clients or uses the current
clock. The committed artifact is
`data/travel-packages/hcmc/1.0.0/`, containing
`hcmc-starter-v1-1.0.0.data.json` and
`hcmc-starter-v1-1.0.0.manifest.json`. It contains the two approved HCMC POIs
and zero aliases, menu items or narrations; no records were added to approach
the future 30–50 target.

The manifest allowlist is exactly `schemaVersion`, `artifactSchemaVersion`,
`packageId`, `city`, `contentVersion`, `publishedAt`, `dataFilename`,
`mediaType`, `byteSize` and `sha256`. Approved data sections are
`packageMetadata`, `pois`, `aliases`, `menuItems` and `narrations`, plus the
top-level `formatVersion`; nested models expose only Android/Room-compatible
stable identifiers, names/category/address/coordinates, optional area and
description, package publication metadata, aliases when supported, integer
minor-unit menu data with source type/freshness, and grounded narration with
source label/freshness. T031 source documents, URLs, raw metadata, provider
payloads, user/trip/preference/location/request data and credentials cannot
cross the extra-forbidden recursive model boundary.

Canonical JSON is UTF-8 with Unicode preserved, lexicographically sorted keys,
stable-ID-sorted entity arrays, compact separators and exactly one final
newline. Datetimes are derived from validated input: manifest publication is
canonical UTC RFC 3339 and Android-facing timestamps are Unix epoch
milliseconds. SHA-256 is lowercase hexadecimal over the exact data-file bytes;
the manifest stores the matching byte count and only a safe relative filename.
Both files are fully serialized, checksummed and model-validated before staged
temporary files are written. Staged files are fsynced and atomically replaced;
handled replacement failures remove temporary files and restore any prior
known artifact without deleting unrelated output files.

Verification is database/network-free and rejects unreadable or malformed
manifest/data JSON, unsupported schema versions, unsafe/traversing filenames,
missing data, size/checksum mismatch, invalid public data, noncanonical entity
order/reference identity, and package/city/version/publication/filename
inconsistency. CI regenerates and byte-compares the committed HCMC pair before
pytest. The downloadable shapes map to current T014 seed DTO types and every
required Room version-2 column, so no Room migration is required. The T014
startup validator itself remains intentionally HCMC-only with a five-POI
bundled-demo minimum; T035 must add downloaded-package staging/activation
around this compatible data shape rather than reuse that startup policy
unchanged. Bangkok can be built generically but is not committed. There is no
package HTTP endpoint, compression, Android download, WorkManager, checksum
activation or Room activation in T034.

T034 required checks passed on Python 3.12.13: dependency installation and
`pip check`, Ruff, strict mypy over app/tests, curated JSON Schema drift check,
both curated package validations, artifact build/check/verify commands, all
219 pytest tests and compileall. Two HCMC builds in different temporary
directories had byte-identical data and manifest files, identical names and
identical SHA-256. macOS `shasum -a 256` returned
`daa7678e1998348c6904f12f6e96026aa7ac33068fab7d8dcdc2ec0b23ae6be3`,
matching the 934-byte manifest. Appending one byte caused verification to fail.
A loopback Python static server plus curl preserved both files byte-for-byte
and the downloaded pair verified successfully. The recursive privacy scan
passed, and build/verify/check also passed while PostgreSQL was stopped; the
local database service was restored healthy afterward.

T035 completed on 2026-07-27 with one Hilt-injected `CoroutineWorker` and
unique WorkManager chain per city. The visible and configured scope is exactly
HCMC; internal models keep a typed city boundary, but no Bangkok UI is claimed.
The work request requires connected networking, uses exponential backoff from
30 seconds, keeps an existing unfinished user request, and replaces it only for
an explicit retry. Progress `Data` carries only city/phase identifiers for
queued, manifest download, data download, verification, validation and atomic
activation. WorkManager 2.11.2, AndroidX Hilt Work 1.4.0 and OkHttp/MockWebServer
5.3.0 are pinned in the version catalog. No periodic or automatic update is
scheduled.

The replaceable manifest-location boundary has a debug-only default of
`http://10.0.2.2:8081/hcmc-starter-v1-1.0.0.manifest.json`. Release has no
endpoint, accepts no cleartext and remains blocked on production hosting.
Debug network security permits cleartext only for emulator host `10.0.2.2`;
external Intents cannot select URLs. OkHttp uses bounded connect/read/call
timeouts, rejects redirects, sends no Authorization/Firebase token, UID,
location or query, logs no URL/body/content and performs only idempotent static
GETs. The backend nearby API and static package synchronization remain separate
paths; T035 added no backend route or token transport.

Strict Kotlin serialization DTOs recursively reject unknown fields in manifest
and data. Manifest validation freezes schema/artifact version 1, HCMC package
identity, canonical content version/publication timestamp, JSON media type,
lowercase SHA-256, a safe relative data filename and a 50 MiB Android ceiling.
The resolved data URL must retain the manifest scheme, host and port. Data
validation enforces manifest identity/publication agreement, stable sorted
unique IDs, finite WGS84 coordinates, HCMC relationships, integer money,
currency/source enums and grounded narration fields; empty alias/menu/narration
sections are valid and fabricate nothing.

App-private staging uses deterministic per-artifact `.part` and `.verified`
names under `files/travel-packages/staging/hcmc`. Existing partial data requests
`Range`; only a matching `206 Content-Range` appends, while a server `200`
truncates and restarts safely. Standard OkHttp stale-connection recovery handles
the local Python HTTP/1.0 server; WorkManager owns application retry/backoff.
Retryable interruption preserves safe partial/verified bytes, while permanent
manifest/data/checksum failures remove them. Exact byte count and streamed
SHA-256 with constant-time comparison complete before UTF-8 parsing. Verified
data can survive process death before activation and is deleted after success.

Room activation constructs every entity before entering one `withTransaction`.
It rejects older or same-timestamp conflicting packages, treats an identical
active manifest as idempotent, removes only the selected city's package content
and metadata, inserts the complete POI graph, and writes active metadata last.
Room rollback preserves all old package data/metadata; other cities remain
untouched and itinerary items survive stale POI removal through the existing
`SET_NULL` relationship. No schema or migration changed. Bundled seed startup
now checks for any valid active HCMC metadata, so a fresh install still receives
five bundled POIs but a downloaded two-POI package is never overwritten after
restart.

Downloads now has Vietnamese-first HCMC package UI for absent, bundled active,
downloaded active, queued/downloading, verifying, activating, success,
retryable failure and invalid-package failure states. It shows real version and
publication metadata, indeterminate phase progress only, and explicitly says
old offline data remains usable after failure. A repository combines durable
Room metadata and WorkManager state into immutable `StateFlow`; Compose and its
ViewModel never call WorkManager, OkHttp or Room directly. Explore remains
available throughout sync and offline.

Final automated verification used Android Studio JDK 21.0.10. From the Android
Gradle root, `lintDebug testDebugUnitTest assembleDebug` passed with 122 JVM
tests, and `connectedDebugAndroidTest` passed all 86 tests on the ARM64 Google
Play emulator. Tests cover the committed 934-byte checksum, one-byte mutation,
strict manifest/artifact failures, same-origin/path safety, valid download,
retryable HTTP failures, oversized/short data, interrupted response retention,
valid `206` resume, ignored Range with safe `200` restart, no sensitive headers,
checksum-before-activation, two-POI Room activation, empty child sections,
rollback, other-city/itinerary preservation, same/older version policy, seed
precedence, WorkRequest constraints/safe data, ViewModel actions and Downloads
UI states. Exported Room v1/v2 schemas were unchanged and no destructive
migration exists.

Manual localhost validation downloaded both committed files, activated
`hcmc-starter-v1` version `1.0.0` and showed exactly the two T034 Vietnamese
POIs. Force-stop/cold-launch retained the downloaded metadata and the bundle did
not return. With the server stopped, Explore still returned both Room POIs. A
temporary same-size data mutation with the original manifest produced
`checksum_mismatch`; UI stated that prior data remained, and direct Room
inspection still showed version `1.0.0` plus the original two POIs. A separate
server outage returned WorkManager retry; restoring hosting caused the same
work ID to retry after its 30-second backoff and succeed. Release hosting,
Bangkok download UI and Android-to-backend networking remain unresolved and
outside T035.

T025 completed on 2026-07-28 with one private, authenticated preference
document per verified Firebase UID. `GET /preferences` is read-only and returns
a canonical empty schema-v1 document when absent. `PUT /preferences` validates
and completely replaces the document in one PostgreSQL transaction; concurrent
first writes converge on one user row and one preference row. The JSON contract
accepts only null, booleans, bounded integers, strings, arrays and objects, with
conservative depth, item, key, string and total-size limits. Unknown envelope
fields, floats, non-finite numbers, binary values and oversized documents are
rejected. Responses and sanitized errors never expose a UID, token, raw
document, preference key/value or database detail. No migration or public
contract outside preferences changed.

Android now stores the latest complete schema-v1 preference document in
account-scoped DataStore records keyed by a SHA-256 account identifier. Local
writes are atomic and durable before unique connected WorkManager work is
scheduled. Synchronization pushes pending edits before fetching, obtains a
fresh Firebase ID token immediately before each request, retries one 401 after a
forced token refresh, and never persists or logs the token. Exact local
revisions prevent an in-flight request from clearing or overwriting a newer
edit. The network client is preference-specific, redirect-free, bounded and
limited to the validated fixed `/preferences` endpoint. Release builds have no
development backend URL and reject cleartext; debug cleartext remains limited
to emulator host `10.0.2.2`. Backup rules exclude preference DataStore data.
No preference UI, periodic synchronization, ranking, AI prompt behavior or
taxonomy was added.

Final backend verification on Python 3.12 passed dependency installation,
`pip check`, Ruff, strict mypy over app/tests, Alembic upgrade to head, curated
schema/package drift checks, the exact 934-byte travel artifact check,
compileall and all 242 pytest tests. The PostgreSQL integration tests apply the
real migration chain, call the authenticated API, verify replacement semantics,
unrelated-table preservation, two-user isolation and concurrent first writes.

Final Android verification used Android Studio JDK 21.0.10. The combined
`test lintDebug assembleDebug connectedDebugAndroidTest` invocation passed,
including all 135 JVM tests and all 90 device tests on the ARM64 API 36 Google
Play emulator. AndroidX DataStore 1.2.1 removed the platform 16 KiB compatibility
dialog observed with 1.2.0; `zipalign -c -P 16 -v 4` also verified the debug APK.
Tests cover contract parity, Unicode, bounds, GET/PUT transport, bearer handling,
single 401 refresh, redirect/body/media failures, cancellation, pending-first
ordering, in-flight edit races, durable recreation, account isolation, revision
guards and safe WorkManager data.

Live synchronization against a development Firebase project was not run because
no production credential, real user token or preference-editing UI was added.
The exact online/offline/account-switch behavior is exercised by deterministic
API, network, sync-engine and instrumented DataStore tests. Preference taxonomy,
product UI and release HTTPS hosting remain open for later explicitly assigned
work.

T040 completed on 2026-07-28 with the strict contract package at
`backend/app/agents/contracts/`. Shared bounded identifier, evidence, claim,
price, warning and failure values support separate Router, Discovery,
Narration, Local Culture, Itinerary, Grounding Reviewer and Response Composer
request/output models plus discriminated specialist and per-stage runtime
unions. Cross-boundary validation closes specialist output over its exact input
evidence, prevents the reviewer/composer from adding claim IDs, preserves
partial warnings and fails closed on inconsistent router plans, evidence,
narration lengths, itinerary schedules, review coverage and orchestration
status. Origin coordinates remain input-only.

All 35 focused T040 contract tests passed. Full backend verification on Python
3.12.13 passed dependency installation, `pip check`, Ruff, strict mypy over
app/tests, curated schema drift and both package validations, travel-package
drift, compileall and 255 pytest tests; 22 disposable-PostGIS integration tests
were skipped because their opt-in database environment was not enabled. Manual
clean-process imports, JSON Schema generation, representative JSON round trips,
invalid-output checks, environment-free imports, privacy/escape-hatch scanning
and the unchanged route set passed. No dependency, route, setting, database,
provider, Android or generated-schema file changed. OpenAI Agents SDK execution,
prompts, tools and orchestration remain T041–T049 work and were not started.

T041 completed on 2026-07-28 with the focused Router implementation at
`backend/app/agents/router/` and exact runtime pin `openai-agents==0.18.3`.
`RouterService` chooses one explicitly configured `OpenAIRouterExecutor` or a
pure deterministic fallback. The public structural `RouterExecutor` boundary
accepts only validated `RouterRequest` and returns only revalidated
`RouterOutput`; SDK result objects, raw output, response IDs, traces, usage and
exceptions remain private.

The configured agent has static instructions, `output_type=RouterOutput`, empty
tools/handoffs/MCP servers, disabled parallel tool calls, `tool_choice="none"`,
one maximum turn and zero model retry. Async `Runner.run` receives no session,
conversation ID or previous response ID. Tracing and sensitive trace data are
disabled until T049. Runtime configuration is read lazily only from nonblank
`OPENAI_API_KEY` plus an explicit nonblank `OPENAI_ROUTER_MODEL`; absent
configuration performs no network call. Invalid output or ordinary model
failure falls back without exposing details, while cancellation propagates.

The fallback's documented precedence is itinerary drafting, local culture,
nearby discovery, POI information, general travel help and unsupported. It
matches representative accented/unaccented Vietnamese and English signals,
returns only canonical specialist plans and safely clarifies unsupported input.
Entity extraction preserves an explicit request city, recognizes only accepted
HCMC/Sài Gòn and Bangkok/Băng Cốc aliases, declines conflicting query cities and
never infers from locale/preferences or invents category, query term, POI ID or
itinerary constraints. Input serialization contains exactly RouterRequest
fields as compact deterministic Unicode JSON. Safe logs contain only operation,
path, reason and intent.

Final backend verification on Python 3.12.13 passed full development dependency
installation, `pip check`, Ruff, strict mypy over app/tests, curated schema
drift, both curated package validations, travel-package drift, compileall and
318 pytest tests; 22 opt-in disposable-PostGIS integration tests were skipped
because their database environment was not enabled. The 63 focused T041 tests
and all 35 unchanged T040 contract tests passed. Credential-free manual
validation imported with OpenAI/database/Firebase configuration absent and
network access blocked, exercised all six intents twice deterministically,
validated unsupported clarification and both JSON Schemas, and confirmed the
unchanged four-route set without external initialization. No local API
key/model configuration was available, so no live model call was run; fake
runner coverage proves the complete model success/failure boundary. No FastAPI
route, database/provider/Firebase/Android behavior, Discovery or later-agent
implementation, orchestration, tracing export or usage accounting was added.

T042 completed on 2026-07-28 with the focused Discovery implementation at
`backend/app/agents/discovery/`. `DiscoveryService` selects one explicit
OpenAI-backed executor only when both `OPENAI_API_KEY` and
`OPENAI_DISCOVERY_MODEL` are nonblank; otherwise it runs the same normalized
tools directly. The public `DiscoveryExecutor` protocol accepts one validated
T040 request and returns only `DiscoveryOutput`. Total POI failure raises a
sanitized typed execution error because T040 correctly forbids candidate-free
partial output.

The POI tool maps the request exactly into T032 and calls the injected provider
once without SQL or HTTP. The optional menu tool has no model arguments and
uses only curated provider IDs selected by that POI result. Its injected-session
adapter executes one read-only selected-POI query ordered by POI/menu stable ID,
maps integer prices and source freshness exactly, and treats zero rows as
success. Both operations preserve cancellation and normalize invalid or failed
results without raw exception text.

Pure evidence assembly de-duplicates exact sources, preserves source
timestamps/Unicode and uses stable SHA-256-derived evidence/claim IDs. Only
requested facts actually present in normalized results become claims; menu and
price claims use the real menu source and price freshness, while distance gets
no synthetic source. Missing rating, menu, price and opening hours remain
absent. Model output must equal every deterministic candidate, source, claim,
failure, completeness/truncation value and order from its own registry; any
plain text, exception or invented/modified value falls back over already
successful tool data without retry. T040 candidate validation was narrowly
relaxed from global ID sorting to uniqueness because global sorting contradicted
T032's distance-first order for valid origins; the public schema/fields and
other closure rules are unchanged.

Final backend verification on Python 3.12.13 passed dependency consistency,
Ruff, strict mypy over app/tests, curated schema drift, both curated package
validations, travel-package drift, compileall and all 378 pytest tests with
local disposable PostGIS enabled. The 32 focused Discovery unit tests and 16
curated-provider/menu integration tests passed. Alembic now uses
`disable_existing_loggers=false`, fixing the pre-existing T041 CI failure where
in-process migration setup disabled Router (and Discovery) loggers before
privacy tests; Router source and behavior remain unchanged.

Credential-free manual validation migrated and idempotently seeded both starter
packages, then executed each request twice through one request-owned session.
HCMC returned Central Post Office then War Remnants Museum; Bangkok returned
Wat Pho. Both were `complete`, untruncated, zero-menu results with missing
rating/price/opening-hours facts preserved, byte-identical repeated JSON, no
origin and no final prose. No local OpenAI configuration was available, so live
model validation was not run; fake-runner tests cover valid closure, altered
candidate/order/evidence rejection, plain-text/exception fallback, single-call
reuse, no retry and cancellation. No route, migration revision, database
schema, production data, Android, Google Places, narration, orchestration,
tracing export or usage-accounting change was added.
