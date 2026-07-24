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
separate and absent.

## Current goal

T022 Google authentication is complete. Do not begin T023 until it is explicitly
assigned.

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

## In progress

- None.

## Next up

- T023 Create FastAPI service.

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
- POI-owned aliases, menus and narrations cascade on POI deletion. Itinerary
  items cascade on itinerary deletion, while a deleted POI sets an optional
  itinerary-item POI reference to null so the user's itinerary item remains.

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
| Task sequence | T000 through T004 and T010 through T022 are complete; T023 is the sole next task. |
| Implementation state | The Android architecture shell, five-destination Navigation Compose shell, centralized Material 3 theme and Room version-2 offline schema/core DAO layer are present under `android/`. A bundled HCMC demo seed imports safely and idempotently and still contains no menu or narration records. Explore has user-triggered, one-shot foreground location context plus offline Room search by name, alias and category, Vietnamese normalization and deterministic straight-line distance ranking. Nearby POIs open local detail screens resolved by stable ID; missing optional data is omitted, while stored prices include freshness dates and stored narration requires a real source label. Explore location/query state survives Back. Loaded details expose an explicit `Dẫn đường` action that validates the stored POI destination and opens any compatible external `geo:` handler, with typed failures, localized retryable UI and coordinate-free no-op analytics. Validated connectivity is observed without network requests; the shell explicitly shows Offline while local Room search/detail remains usable. Local package version and publication metadata is visible only in Downloads. Assistant and Downloads explain Internet-only future actions, while external navigation is never disabled solely because connectivity is Offline. The dedicated Firebase development configuration is integrated only for debug and initializes the default Firebase app automatically. Profile implements email/password registration and sign-in, verification-email delivery/resend, explicit verification refresh and a common sign-out path. It also implements explicit Google authentication through Credential Manager; Google ID credentials are exchanged only ephemerally for Firebase, cancellation is controlled, Firebase remains the single session source of truth and sign-out clears Credential Manager state. Manual development-project validation confirms email/password and Google sessions restore after force-stop/cold launch; Explore and local Room data remain independent of authentication. Production/release Firebase configuration and backend Firebase ID-token verification remain absent. There is no background tracking or exact-location persistence. Package downloading, networking and AI remain incomplete. Local PostgreSQL/PostGIS infrastructure exists; backend application, server database schema/migrations, data pipeline and agent runtime are not implemented. |

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
