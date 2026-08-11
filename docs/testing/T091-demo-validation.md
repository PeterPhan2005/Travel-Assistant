# T091 demo validation

## Accepted end-to-end boundary

T091 automates the existing Android product path
`Explore query → HomeViewModel → active-package Room FTS → Compose navigation →
Room POI detail → external-navigation boundary`. The Assistant result cards do
not currently expose a navigation action. Adding one only for this task would
be new product behavior, so it is not part of T091.

The accepted flows are Android-local. They require no Firebase session,
backend, PostgreSQL/PostGIS or OpenAI model. The task-level backend `pytest`
command remains a regression gate. All automated cases use synthetic HCMC
location and content values in an isolated in-memory Room database and perform
no network request.

## Automated coverage matrix

| Flow | Starting state | Auth | Network | Package/location | Services | Actions and expected result | Persistence/privacy/cleanup |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HCMC food query to navigation | Fresh test composition on Explore | None | Online app state | Bundled HCMC package imported into isolated Room; synthetic foreground HCMC location | Real Room v4 search/detail repositories, HomeViewModel and Compose navigation; no backend/model | Enter `phở bò`, open the deterministically first matching POI, observe stored narration and its source, tap `Dẫn đường`, and receive the exact stored POI at the external-navigation boundary | Only the in-memory test database is changed; coordinates are neither asserted as UI text nor logged; database closes after the test |
| Sourced narration | Same food-flow detail session | None | Online app state | Same isolated active package and fixture | Real Room detail snapshot/repository and production POI detail UI | Narration content and `Nguồn: …` are both visible; source-less narration behavior remains covered by the existing repository tests | Synthetic source label only; no provider payload or model output; database closes after the test |
| Offline package search after disconnect | Fresh test composition starts Online, then changes through the accepted connectivity seam to Offline before the query | None | Offline app state after an observable Online → Offline transition | Same active HCMC package and synthetic foreground location | Real Room v4 FTS/HomeViewModel/Explore UI; no Firebase/backend/provider/model boundary exists in the harness | Offline warning becomes visible; enter `pho bo`; active-package result remains visible and deterministically ranked | Query remains transient; no HTTP/auth/model dependency; database closes after the test |

The external map application itself, physical GPS radio and microphone service
are device-owned boundaries. They remain manual evidence and must not be marked
passed from the deterministic instrumentation harness.

## Manual runbook

Run this section on the exact build under review. Record the Git SHA, device
class (`Emulator` or physical model), Android version and PASS/FAIL category
only. Do not record account identity, transcript text, coordinates, tokens,
request/response bodies or screenshots containing private input.

### Preconditions

1. Confirm the repository worktree and exact build SHA.
2. Install the debug APK on one API-36 Google Play Emulator and, for GPS and
   microphone evidence, one physical Android device.
3. Confirm the HCMC package is active before disconnecting. Do not clear app
   data after this point.
4. Keep Firebase/OpenAI credentials outside the repository. GPS and local
   Explore search require no authentication or backend.
5. Note the device's initial Wi-Fi, mobile-data and airplane-mode states so they
   can be restored exactly during cleanup.

### Foreground GPS

1. On the physical device, revoke TravelAssistant's foreground location
   permission from App Info, then cold-launch the app.
2. Verify launch and ordinary tab navigation do not show a location permission
   prompt.
3. Open `Khám phá` and tap the explicit current-location action once.
4. Grant only foreground permission. Verify the UI reaches the available
   location state and renders local nearby results without displaying exact
   coordinates.
5. Tap refresh once and verify one new foreground acquisition occurs; leaving
   the app during an acquisition must not leave a stale success.
6. Record only `foreground_permission_timing`, `location_available`,
   `nearby_content` and `background_cancellation` as PASS/FAIL categories.

### Microphone and voice-origin input

1. On the physical device, revoke TravelAssistant's microphone permission from
   App Info, force-stop, and cold-launch the app.
2. Verify launch, opening `Trợ lý` and manual typing do not request microphone
   permission or start recognition.
3. Tap `Nói câu hỏi`, grant microphone permission, and speak one short
   Vietnamese food request.
4. Verify partial/final text appears in the editable field and can be edited
   before confirmation. Do not copy the transcript into evidence.
5. Start another attempt, cancel it, then leave `Trợ lý`; verify no late result
   replaces the current text and no automatic restart occurs on return.
6. Force-stop and relaunch; verify neither transcript nor recognition session
   is restored. Record only permission timing, editable-result, cancellation,
   departure and non-restoration categories.

### Actual network isolation

1. With an active HCMC package and foreground location already available,
   disable Wi-Fi and mobile data using device controls. Enable airplane mode if
   the device still reports validated Internet.
2. Wait for the app's Offline indicator; do not use a fixed sleep.
3. In Explore, enter an existing local name/category/dish term and verify a
   Room result opens its canonical detail. Unsupported Assistant generation
   must remain explicitly offline.
4. Force-stop and relaunch while still offline. Reacquire foreground location
   only if the platform requires it, then repeat the local query.
5. Record only `offline_indicator`, `local_search`, `detail_open` and
   `offline_relaunch` categories. Do not dump logcat, database rows or network
   bodies as default evidence.

### External map boundary

1. From a loaded POI detail, tap `Dẫn đường`.
2. Verify a compatible external map chooser/application receives the action, or
   that the localized unavailable error is shown when no handler exists.
3. Return to TravelAssistant and verify the POI detail remains recoverable.

### Cleanup

1. Restore airplane mode, Wi-Fi and mobile data to the states recorded before
   the run; wait for the expected connectivity state.
2. Remove only ADB reverse/proxy rules created for this run. Do not clear
   unrelated device or application data.
3. Optionally revoke TravelAssistant's location and microphone permissions to
   restore the pre-run app-owned permission state.
4. Confirm no credential, token, account identifier, exact coordinate,
   transcript or private log artifact was written into the repository.

## Manual evidence status

Completed for T091 on 2026-08-11 from the user-supplied physical-device runbook
result. Only PASS categories were recorded; no account identity, transcript,
coordinate, token, request/response body or private screenshot/log content was
added.

- Foreground GPS: `foreground_permission_timing` PASS,
  `location_available` PASS, `nearby_content` PASS and
  `background_cancellation` PASS.
- Microphone and voice-origin input: `microphone_permission_timing` PASS,
  `voice_editable_result` PASS, `voice_cancellation` PASS,
  `assistant_departure stale-result protection` PASS and
  `voice_non_restoration after force-stop` PASS.
- Actual physical network isolation: `actual network isolation` PASS,
  `offline_indicator` PASS, `local_search while radios/network were disabled`
  PASS, `canonical detail while offline` PASS and
  `offline force-stop/relaunch` PASS.
- External map boundary: `external map handler` PASS and
  `return to POI detail` PASS.
- Cleanup: `connectivity cleanup/restoration` PASS and
  `repository unchanged during manual validation` PASS.

This evidence closes the device-owned T091 gates, including offline local
search and canonical detail after disabling the device's radios/network, cold
relaunch while offline, external-map handling and restoration of connectivity.
