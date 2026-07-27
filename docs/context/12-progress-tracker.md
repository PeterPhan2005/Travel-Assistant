# Progress Tracker

## Current phase

Phase 2 is in progress. The Android architecture shell is present, with Hilt,
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
publication metadata is observed by the app-shell state owner but displayed
only in Downloads, while Assistant and Downloads explain their Internet
requirements without claiming those unfinished features work. External
navigation is not disabled solely because the app is offline. Package
downloading, networking, backend token verification, AI and other later product
behavior remain incomplete. The dedicated Firebase
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
activates it in Room while retaining old offline data on every failure. Live
Google Places, Android-to-backend networking and the AI runtime remain
unimplemented.

## Current goal

T035 Android package synchronization is complete. T025 is next by roadmap and
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
- T030 Create server database schema.
- T031 Build curated data pipeline.
- T032 Define POI provider adapters.
- T033 Implement nearby POI API.
- T034 Build travel package artifact.
- T035 Download and activate travel package.

## In progress

- None.

## Next up

- T025 Synchronize user preferences.

## Open questions

- Final visual identity/project name.
- Cloud deployment provider.
- Split of 30–50 curated POIs between HCMC and Bangkok.
- Exact list of source publishers accepted for narration.
- Exact production retention duration for rounded or redacted operational
  location-request logs within the accepted 7–30 day range.

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
| Task sequence | T000 through T004, T010 through T024 and T030–T035 are complete; T025 is next but unassigned. |
| Implementation state | The Android architecture shell, five-destination Navigation Compose shell, centralized Material 3 theme and Room version-2 offline schema/core DAO layer are present under `android/`. A bundled HCMC demo seed imports safely and idempotently and still contains no menu or narration records. Explore has user-triggered, one-shot foreground location context plus offline Room search by name, alias and category, Vietnamese normalization and deterministic straight-line distance ranking. Nearby POIs open local detail screens resolved by stable ID; missing optional data is omitted, while stored prices include freshness dates and stored narration requires a real source label. Explore location/query state survives Back. Loaded details expose an explicit `Dẫn đường` action that validates the stored POI destination and opens any compatible external `geo:` handler, with typed failures, localized retryable UI and coordinate-free no-op analytics. Validated connectivity is observed without network requests; the shell explicitly shows Offline while local Room search/detail remains usable. Downloads now exposes HCMC-only user-triggered package sync with WorkManager, strict manifest/artifact validation, resumable app-private staging, exact byte/SHA-256 verification and one-transaction Room activation. Active package metadata/data survives process restart and every failed update; bundled seed never replaces a valid downloaded package. Assistant still explains its Internet-only future behavior, while external navigation is never disabled solely because connectivity is Offline. The dedicated Firebase development configuration is integrated only for debug and initializes the default Firebase app automatically. Profile implements email/password registration and sign-in, verification-email delivery/resend, explicit verification refresh and a common sign-out path. It also implements explicit Google authentication through Credential Manager; Google ID credentials are exchanged only ephemerally for Firebase, cancellation is controlled, Firebase remains the single session source of truth and sign-out clears Credential Manager state. Manual development-project validation confirms email/password and Google sessions restore after force-stop/cold launch; Explore and local Room data remain independent of authentication. Production/release Firebase configuration remains absent. There is no background tracking or exact-location persistence. The backend builds and verifies deterministic static travel-package JSON directly from validated T031 input, with a committed two-POI HCMC artifact and no package HTTP endpoint; Android-to-backend transport remains separate and unimplemented. Local PostgreSQL/PostGIS infrastructure exists. The backend FastAPI factory, validated settings, liveness endpoint, request IDs, sanitized error envelope and Firebase Admin ID-token verification are implemented; `/auth/me` exposes only UID and `/health` remains public and database-free. Typed SQLAlchemy metadata and an async Alembic migration create the ownership, itinerary, curated provenance, menu, narration and PostGIS POI schema. The strict version-1 curated pipeline validates and transactionally seeds sourced HCMC/Bangkok starter packages. A provider-neutral async discovery contract normalizes bounded nearby requests, namespaced result identity, provenance/freshness and canonical errors/timeouts. Its first injected-session curated adapter performs one read-only parameterized PostGIS query with deterministic distance/ID ordering and no payload/ORM escape. Canonical `GET /pois/nearby` validates bounded HTTP query parameters, supports anonymous or strictly verified optional Firebase authentication, and returns only normalized curated POIs with metre distance, provenance/freshness, returned count and completeness. Its app-owned lazy engine and request session lifecycle do not persist request origins or commit writes. Live Google Places, Android-to-backend networking and agent runtime are not implemented. |

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
