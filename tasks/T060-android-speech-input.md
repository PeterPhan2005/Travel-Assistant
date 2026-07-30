---
id: T060
title: Implement Android speech-to-text input
status: done
depends_on: [T012]
area: android
---

# Goal

Add push-to-talk microphone flow using Android SpeechRecognizer and return editable transcript.

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

- [x] Permission requested only on use.
- [x] Cancellation/error states are handled.
- [x] Transcript can be edited before submission.
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

Implementation, emulator validation and physical-device validation completed
on 2026-07-30 without adding a dependency, network transport, persistence layer
or backend change.

Implementation evidence:

- The Assistant placeholder is now a Vietnamese-first query composer with
  editable manual text, partial/final speech transcripts, explicit cancel,
  local-only confirmation and localized unavailable, permission-denied and
  typed recognition-error states.
- `MainActivity` owns the one `RECORD_AUDIO` activity-result launcher and calls
  it only after the user selects `Nói câu hỏi`. Each tap receives one bounded,
  process-local attempt ID. Only the current permission attempt can start
  recognition; duplicate taps and obsolete grant/denial callbacks are ignored.
  Cancel, Assistant departure and Activity stop invalidate pending attempts.
- On every Activity resume, `MainActivity` reads the current Android microphone
  permission and forwards only that Boolean status. A newly granted permission
  clears a stale permission-denied UI state without creating an attempt,
  requesting permission or starting recognition; the user must select
  `Nói câu hỏi` again.
- The selected-destination lifecycle boundary cancels active recognition
  exactly once when the user leaves Assistant, independently of Activity
  `onStop`. Editable partial, manual and confirmed text remains intact, and
  returning to Assistant never restarts recognition.
- The voice control clears text-field focus and hides the software keyboard
  before invoking the application-owned recognition callback. Text composition
  and editing never invoke that callback; active recognition replaces the
  control with `Hủy nghe`.
- Manual input, partial/final recognition and local confirmation share one
  1,000-Unicode-code-point bound. Manual editing preserves outer whitespace;
  recognition and confirmation trim outer whitespace, preserve Vietnamese and
  never split a UTF-16 surrogate pair.
- A feature-owned platform-neutral contract prevents `SpeechRecognizer`,
  `Intent`, `Bundle`, raw Android error integers, audio buffers, paths and
  exceptions from entering ViewModel/UI state. The Android adapter requests
  Vietnamese `vi-VN` free-form partial results and maps all 15 error constants
  present in compile SDK 36.1. Its recognizer remains lazy; cancellation and
  close invalidate callbacks before platform calls, close is idempotent,
  active close cancels then destroys exactly once, and start after close
  returns a typed client failure without recreating the recognizer.
- `SpeechRecognizer.ERROR_SPEECH_TIMEOUT` remains mapped exactly to
  `SpeechRecognitionFailure.NO_SPEECH`; this state retains editable text and
  requires an explicit user retry.
- The listener intentionally ignores Android audio buffers. Query text,
  recognition state and confirmed transcript exist only in the ViewModel
  `StateFlow`; no repository, Room, DataStore, file, API request, analytics or
  agent boundary is involved.
- Visible privacy wording states that TravelAssistant neither writes audio to a
  file nor persists/uploads it, while the device-selected recognition service
  may use network processing. Transcript text remains temporary, local and
  editable until future submission is implemented.
- The manifest adds only `RECORD_AUDIO` and the recognition-service query while
  preserving the existing `geo:` query.

Checks run from `android/`:

- `./gradlew test --no-daemon --stacktrace`: exit 0, `BUILD SUCCESSFUL`; 168
  JVM tests passed.
- `./gradlew connectedDebugAndroidTest --no-daemon --stacktrace`: exit 0,
  `BUILD SUCCESSFUL`; all 112
  instrumented tests passed on both
  `Pixel_7_API_36_Google_Play_ARM64(AVD) - 17` and the ZTE nubia V60
  (`NX721J`, Android 15, serial `320143952923`).
- `./gradlew :app:lintDebug :app:testDebugUnitTest :app:assembleDebug --no-daemon --stacktrace`:
  exit 0, `BUILD SUCCESSFUL`; lint reported zero issues.
- `./gradlew installDebug` plus a cold Activity launch succeeded. Device-level
  inspection confirmed the composer layout and that the Android microphone
  permission dialog first appears only after tapping `Nói câu hỏi`.
- With macOS host-microphone access, emulator host-microphone access,
  `RECORD_AUDIO` and foreground AppOps access enabled, the application-owned
  `Nói câu hỏi` flow produced `Tôi muốn tìm quán phở gần đây` in the editable
  Assistant field and allowed local confirmation.
- Interaction and source-policy tests prove typing does not start recognition,
  the voice action invokes only the application callback, active recognition
  shows `Hủy nghe`, `NO_SPEECH` retains text, stale permission callbacks are
  rejected, tab departure cancels, all five destinations remain present, the
  common code-point bound holds, and no Gboard, keyboard voice-input,
  package-specific recognition, recording, persistence or T061 transport API
  is used.
- Backend `.venv/bin/python -m app.agent_evals check`: exit 0; all 43 T050
  fixtures passed. Repository `git diff --check`: exit 0.
- Final physical validation passed on the ZTE nubia V60. The app requested no
  microphone permission at launch, Assistant entry or manual typing; the
  request appeared only after `Nói câu hỏi`. Application-owned Vietnamese
  recognition, editable/local confirmation, explicit cancellation, Assistant
  departure cancellation, Activity background cancellation, denial handling
  and cold-launch non-persistence all passed. AppOps reported foreground allow
  with recent microphone use.
- The repaired App Info return path passed without restarting: after granting
  `RECORD_AUDIO`, stale denial UI disappeared, `Nói câu hỏi` became enabled,
  listening did not start automatically, existing query/confirmation remained,
  and one explicit tap started recognition without another permission prompt.
  The repaired build was installed only on `NX721J` for this final retest.

Known limitations:

- Installed Vietnamese language support and recognition quality depend on the
  device's selected Android recognition service.
- Android's selected recognition service may itself require network access;
  this app does not receive audio buffers beyond the ignored callback, record
  audio to a file, persist it or upload it to a TravelAssistant endpoint.
- A separate Gboard voice-typing attempt displayed `Không nhận được âm thanh,
  hãy thử lại sau`; that keyboard behavior is outside T060. The Assistant flow
  does not call Gboard or keyboard voice-input APIs and no workaround is added.
- Confirmation is deliberately local and sends nothing. T061 remains
  unimplemented.
