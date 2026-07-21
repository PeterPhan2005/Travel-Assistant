# Progress Tracker

## Current phase

Phase 1 is in progress. The Android architecture shell is present, with Hilt,
ViewModel/StateFlow and repository boundaries established. The top-level
Navigation Compose shell and centralized Material 3 theme are complete;
the initial version-1 Room schema and DAO layer are complete. Seed importing,
networking and product features remain incomplete.

## Current goal

Begin T014 curated seed importing only when that task is explicitly assigned.

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

## In progress

- None.

## Next up

- T014 Import curated seed into Room.

## Open questions

- Final visual identity/project name.
- Exact Google Maps/MapLibre choice for first demo.
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
| Task sequence | T000 through T004 and T010 through T013 are complete; T014 is the sole next task. |
| Implementation state | The Android architecture shell, top-level Navigation Compose shell, centralized Material 3 theme and Room version-1 offline schema/core DAO layer are present under `android/`. Bundled seed importing, destination product features, networking and authentication remain incomplete. Local PostgreSQL/PostGIS infrastructure exists; backend application, server database schema/migrations, data pipeline and agent runtime are not implemented. |

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
