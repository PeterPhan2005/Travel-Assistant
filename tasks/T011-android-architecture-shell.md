---
id: T011
title: Add Android architecture shell
status: done
depends_on: [T010]
area: android
---

# Goal

Add feature-oriented packages, ViewModel pattern, Hilt and base repository interfaces.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/12-progress-tracker.md`

# Scope

Implement only the goal and acceptance criteria in this file.

# Out of scope

- Future tasks.
- Unrequested refactors.
- New product behavior not present in context files.

# Acceptance criteria

- [x] Hilt app starts.
- [x] A sample ViewModel exposes immutable StateFlow.
- [x] No business logic is in composables.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test
./gradlew lint
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.

# Verification evidence

Completed on 2026-07-21 with the existing single-module, single-activity app and
its package, namespace, application ID, compile SDK, Gradle wrapper, AGP, Kotlin
and Compose versions preserved.

Architecture evidence:

- `TravelAssistantApplication` is annotated with `@HiltAndroidApp` and
  registered in the manifest; `MainActivity` is annotated with
  `@AndroidEntryPoint`.
- `AppInfoRepository` is bound to `DefaultAppInfoRepository` in the singleton
  Hilt component.
- `HomeViewModel` depends on the repository interface and exposes a read-only
  `StateFlow<HomeUiState>` produced by `stateIn`; no mutable state is exposed to
  Compose.
- `HomeScreen` receives immutable state and only renders it. Navigation,
  persistence, networking and product behavior were not added.
- Three JVM tests cover the initial state, propagation of a repository update
  and the non-mutable public StateFlow using a fake repository.

Checks run from `android/`:

- `./gradlew --stop`: exit 0.
- `./gradlew test`: exit 0, `BUILD SUCCESSFUL`; three JVM tests passed.
- `./gradlew lint`: final exit 0, `BUILD SUCCESSFUL`. The first attempt selected
  a VS Code Java runtime without `bin/jlink` and failed before lint ran. After
  stopping that daemon, the unchanged command passed with the required Android
  Studio JDK 21 selected through `JAVA_HOME`.
- `./gradlew :app:lintDebug :app:testDebugUnitTest :app:assembleDebug --no-daemon --stacktrace`:
  exit 0, `BUILD SUCCESSFUL` with Android Studio JDK 21.
- `./gradlew connectedDebugAndroidTest`: exit 0; the existing app-identity test
  passed on `Pixel_7_API_36_Google_Play_ARM64(AVD) - 17`.
- `./gradlew installDebug`: exit 0; installed on the authorized emulator.
- `adb shell am start -W -n com.kltn.travelassistant/.MainActivity`: exit 0 with
  `Status: ok` and a cold launch. The process remained alive and MainActivity
  was top-resumed and focused. Focused logcat inspection found no Hilt startup,
  generated-component, binding or AndroidRuntime fatal error.
