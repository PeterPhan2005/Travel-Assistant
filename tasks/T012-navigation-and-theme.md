---
id: T012
title: Implement navigation and theme
status: done
depends_on: [T011]
area: android
---

# Goal

Add Material 3 theme and bottom navigation destinations for Explore, Assistant, Itinerary, Downloads and Profile.

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

- [x] All destinations are reachable.
- [x] Back navigation works.
- [x] Theme tokens are centralized.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test
./gradlew connectedDebugAndroidTest
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.

# Verification evidence

Completed on 2026-07-21 with the existing package, application ID, single app
module, single launcher activity, Hilt setup, repository boundary,
`HomeViewModel` and immutable `StateFlow<HomeUiState>` preserved.

Implementation evidence:

- One Navigation Compose `NavHost` starts at the canonical `explore` route and
  defines all five top-level routes in the centralized `TopLevelDestination`
  model.
- The Material 3 `NavigationBar` exposes Vietnamese labels and accessible icon
  descriptions. Top-level selection uses `popUpTo`, state save/restore and
  `launchSingleTop`; Navigation Compose owns the only back stack and no custom
  `BackHandler` was added.
- Explore continues to render the existing Home/ViewModel state. Assistant,
  Itinerary, Downloads and Profile render only a localized title and concise
  future-feature message.
- Complete centralized light/dark fallback color schemes, typography and
  spacing tokens replace the starter purple/pink theme residue. Dynamic color
  remains available as an explicit opt-in and no final branding is claimed.
- Three JVM tests cover the destination set, unique routes and Explore start
  route. Three Compose instrumented tests cover navigation item visibility,
  reaching/selecting every destination, repeated-tap behavior and Back to
  Explore. The existing app-identity instrumented test remains unchanged.

Checks run from `android/`:

- `./gradlew test`: exit 0, `BUILD SUCCESSFUL`; all six JVM tests passed.
- `./gradlew connectedDebugAndroidTest`: exit 0, `BUILD SUCCESSFUL`; all four
  instrumented tests passed on `Pixel_7_API_36_Google_Play_ARM64(AVD) - 17`.
- `./gradlew :app:lintDebug :app:testDebugUnitTest :app:assembleDebug --no-daemon --stacktrace`:
  exit 0, `BUILD SUCCESSFUL`.
- `./gradlew installDebug`: exit 0; Activity Manager cold-launched
  `com.kltn.travelassistant/.MainActivity` with `Status: ok`, and visual
  inspection confirmed all five Vietnamese navigation items are readable.

The first connected test attempt exposed the existing Espresso 3.5.1 use of a
removed Android 36.1 input API. Updating the already-declared AndroidX test
libraries to stable Espresso 3.7.0 and JUnit extension 1.3.0 resolved it; the
unchanged required command then passed.
