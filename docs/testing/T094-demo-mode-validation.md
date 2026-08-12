# T094 safe demo-mode validation

## Accepted boundary

T094 adds only two explicit debug location presets for Explore. Real GPS remains
the default and still runs through `AndroidLocationClient`. Preset selection is
resolved by a debug-only provider, updates the existing transient Home
`ViewModel`, and calls the unchanged `NearbySearchRepository` boundary. It does
not request Android location permission, change device location settings, write
Room/DataStore/files, schedule work, or add a network/backend/provider/model
path.

The main source set contains only the neutral preset/provider contract and UI
that renders controls when the injected list is nonempty. `src/debug` supplies
exactly two presets. `src/release` supplies an empty list and no coordinate, so
the release Home state cannot expose or resolve a demo location. The focused
release-source policy test also requires all preset labels and coordinate
literals to remain outside main/release runtime source.

## Preset coordinate provenance

These values are public destination coordinates already committed and exercised
in repository data/tests; they are not remembered, user, or device coordinates.

| Preset | Exact value | Repository source |
| --- | --- | --- |
| HCMC | `10.7799`, `106.7` | `data/curated/hcmc/package-v1.yaml`, POI `hcmc-poi-central-post-office` (`Bưu điện Trung tâm Sài Gòn`); the same reference is used by `HomeViewModelTest` and deterministic nearby/distance tests |
| Bangkok | `13.746508`, `100.493096` | `data/curated/bangkok/package-v1.yaml`, POI `bkk-poi-wat-pho`; the same Wat Pho origin is used by T093/PostGIS nearby and setup validation |

The debug preset objects have no accuracy or capture timestamp. Application
logs and product analytics receive neither preset coordinates nor preset
labels.

## Latest-action-wins behavior

Every explicit real or preset action advances one in-memory action generation.
Starting a newer action cancels active acquisition/search work, and both the
location callback and nearby result must still match the current generation
before updating UI. This covers real GPS → either preset, either preset → real
GPS, HCMC ↔ Bangkok, query changes under a preset, and non-cooperative stale
callbacks/results. The selected preset survives ordinary tab return and
configuration retention only through the existing `ViewModel`; a new process or
new `ViewModel` starts at Idle with no preset selected.

Only a successful search belonging to a genuine real-location action can arm
`geocontext_opened`. Preset selection and its later query/search results do not
emit that production KPI. The analytics schema is unchanged.

## Active-package audit

Demo location is independent from offline package activation:

- `RoomNearbySearchRepository` still queries only the active
  `Ho Chi Minh City` package for blank and FTS searches.
- Downloads/package sync still exposes only `PackageCity.HCMC` and the existing
  HCMC manifest path.
- Preset code imports no package, Room, WorkManager, download, manifest, or
  activation type.
- Selecting Bangkok therefore changes only the synthetic origin used to rank
  the currently active HCMC Room records. It does not download/activate Bangkok,
  insert T093 records, change package URLs, or bypass active-package FTS rules.

It is acceptable in T094 for Bangkok to show no useful local Bangkok results
(or distance-ranked HCMC records) while the HCMC package remains active. A
dedicated future task should own multi-city offline package download,
selection, and activation; T094 deliberately does not implement it.

## Automated checks

Focused JVM coverage verifies initial/default state, both presets, no
`LocationClient`/permission path, stale real callback suppression, explicit
real-GPS replacement, both preset switch directions, query reuse, stale nearby
suppression, no geocontext analytics, and new-process non-restoration. Debug
Compose/instrumentation covers both visible/selectable controls and the ordinary
current-location action. `DemoLocationReleaseSourcePolicyTest` verifies the
debug-only values, empty release provider, conditional UI exposure, and absence
of scattered `BuildConfig.DEBUG` demo logic.

The repository intentionally has no release Firebase client configuration.
Consequently `assembleRelease` currently stops at
`processReleaseGoogleServices` because `src/release/google-services.json` is
absent. Do not copy the development Firebase config or invent production
credentials to bypass that boundary. Release artifact inspection remains
blocked until the separately owned release-environment task supplies an
approved configuration; source-set isolation is the current T094 proof.

## Manual runbook

Run against the exact Git SHA under review. Record only build/device class,
Android version, and PASS/FAIL categories. Do not record a real-device
coordinate, account identity, token, query/transcript, request/response body,
database row, or private screenshot/log content.

### A. Debug cold launch

1. Install the debug APK, force-stop, and cold-launch TravelAssistant.
2. Open Explore and verify neither preset is shown as selected.
3. Verify no foreground-location permission dialog appears automatically and
   the ordinary `Dùng vị trí hiện tại` action remains available.
4. Record `debug_cold_no_preset`, `no_automatic_permission`, and
   `real_action_default` as PASS/FAIL.

### B. HCMC preset

1. Without tapping the ordinary GPS action, select `Demo: TP.HCM`.
2. Verify the action causes no location-permission dialog and does not open
   device location settings.
3. Verify the UI explicitly says it is using a developer demo location, not
   current GPS, and the transient Explore search updates while preserving the
   current query.
4. Record `hcmc_select`, `hcmc_no_permission`, and `hcmc_transient_search`.

### C. Bangkok preset

1. Select `Demo: Bangkok` and verify it replaces HCMC as the displayed demo
   context.
2. Verify no package download/activation starts and Downloads remains on the
   existing HCMC package path.
3. Accept an empty result or HCMC active-package limitation; do not claim that
   T093 Bangkok records are available in Android Room.
4. Record `bangkok_select`, `bangkok_transient_context`, and
   `bangkok_hcmc_package_limitation_disclosed`.

### D. Back to real GPS

1. Tap the ordinary current-location refresh action.
2. Grant foreground permission if Android requests it.
3. Verify loading uses the real device-location path, clears the demo selection,
   and a successful real fix replaces the synthetic location/search.
4. Do not record the real coordinate. Record only `real_permission_timing`,
   `real_replaces_demo`, and `latest_action_wins`.

### E. Restart

1. Select either preset, then force-stop TravelAssistant.
2. Cold-launch and open Explore.
3. Verify the app returns to Idle with no preset selected and starts no demo
   search automatically.
4. Record `force_stop_no_preset_restore`.

### F. Release

1. Run the focused release-source isolation test and inspect the diff to confirm
   preset definitions/labels/coordinates exist only in `src/debug`, while the
   release provider remains empty.
2. When an approved release Firebase configuration exists, run
   `./gradlew assembleRelease`, inspect/install that exact artifact, and verify
   neither demo control label exists in the UI and no preset can be selected.
3. Until that separate configuration exists, record
   `release_artifact_blocked_missing_approved_firebase_config`; do not mark an
   artifact-level PASS and do not substitute debug configuration.

## Manual evidence status

User-supplied manual validation was recorded on 2026-08-12 with these exact
outcomes:

- A. Debug cold launch: `debug_cold_no_preset`,
  `no_automatic_permission`, and `real_action_default` — PASS.
- B. HCMC preset: `hcmc_select`, `hcmc_no_permission`, and
  `hcmc_transient_search` — PASS.
- C. Bangkok preset: `bangkok_select`, `bangkok_transient_context`,
  `query_preserved_across_presets`, and
  `bangkok_hcmc_package_limitation_disclosed` — PASS.
- D. Return to production location path: `real_permission_timing`,
  `real_replaces_demo`, and `latest_action_wins` — PASS.
- E. Force-stop/relaunch: `force_stop_no_preset_restore` — PASS.
- F. Release isolation: `release_source_isolation` and
  `release_provider_empty` — PASS;
  `release_artifact` — `BLOCKED_MISSING_APPROVED_FIREBASE_CONFIG`.

The release artifact outcome is not a PASS. The required release build still
stops at `:app:processReleaseGoogleServices` because an approved
`src/release/google-services.json` intentionally does not exist. T099 owns a
variant-safe staging/release Firebase configuration distinct from debug, and
T101 owns later release-artifact hardening/proof. The development Firebase
configuration must not be copied or reused to bypass this boundary.

T094 accepts required-check failures when documented and does not require an
installed release artifact. Its source-set isolation and empty release provider
prove that release code cannot resolve a demo preset. The blocked artifact does
not prevent T094 completion; requiring T099/T101 evidence here would also create
a dependency cycle because T099 depends on T094 and T101 depends on T099.

The Bangkok limitation remains accepted and explicit: the preset changes only
the transient synthetic origin while Android continues to use the active HCMC
offline package. Multi-city package selection/activation was not added or
scheduled by this closure.
