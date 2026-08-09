# Evaluation Plan

## Product KPIs

- Navigation conversion:
  POI detail sessions with “Dẫn đường” / POI detail sessions.
- Itinerary creation success:
  valid itinerary responses / generation requests.
- Voice intent accuracy:
  correctly detected intent + primary entity / labeled voice queries.
- Return during trip:
  users opening app on at least two trip days / users starting a trip.
- Geocontext opens:
  sessions using current location and nearby content.

## Product analytics schema version 1

T090 instruments these KPIs on Android, where the explicit actions and validated
presentation outcomes are owned. It adds no backend event, external analytics
vendor, SDK, consent UI, device/user identifier, upload, persistence or delivery
retry. Debug builds retain at most 200 typed records in process memory for
inspection; release builds use the same injected boundary as a no-op. Analytics
never requests a Firebase token and never calls the backend, a provider or an
OpenAI model.

Every record has integer `schema_version = 1`. Event names and properties are
closed as follows:

| Event name | Exact properties | Emission rule |
| --- | --- | --- |
| `navigation_conversion` | `stage`: `detail_opened` or `navigation_requested`; `poi_id`: validated stable product POI ID | `detail_opened` occurs once after a POI detail ViewModel receives valid content. `navigation_requested` occurs for the first explicit `Dẫn đường` tap in that active detail session. Recomposition, configuration change and duplicate/retry taps do not add another event; reopening a popped detail creates a new session. |
| `itinerary_creation` | `outcome`: `attempted`, `succeeded`, `cancelled` or `failed`; `failure_category`: `none`, `offline`, `authentication_required`, `invalid_request`, `timeout`, `rate_limited`, `unavailable`, `invalid_response` or `unsupported_transport` | `attempted` occurs once only when a valid online form reaches the generator. Exactly one terminal event occurs for that in-process attempt. A retry is a new explicit attempt. Success means the response passed the existing exact-request draft validator. Failure categories are closed and never contain exception text. |
| `voice_intent_result` | `intent`: `nearby_discovery`, `poi_information`, `local_culture`, `itinerary_drafting`, `general_travel_help` or `unsupported`; `outcome`: `success`, `partial` or `failed` | Occurs once for a structured Assistant result with a non-null intent when the submitted text came from the app-owned speech-recognition flow. A manual edit changes the input classification to manual and therefore emits no voice KPI event. |
| `trip_return` | none | Occurs once for each explicit open of a saved itinerary from the verified account's visible library. Duplicate calls while that saved item is already open are ignored. Signed-out, unverified and unavailable-library states cannot emit it. |
| `geocontext_opened` | `result_state`: `content` or `empty` | Occurs once per Home ViewModel after an explicit current-location action first produces a successful local nearby result. Query changes, tab return, recomposition and location refreshes in the same ViewModel do not emit again. Failure and cancellation emit nothing. |

KPI calculation uses `navigation_conversion(stage=navigation_requested)` over
`navigation_conversion(stage=detail_opened)`, and
`itinerary_creation(outcome=succeeded)` over
`itinerary_creation(outcome=attempted)`. Events are best-effort and at-most-once
for each rule above. They have no durable queue, background delivery or
exactly-once guarantee across process death. A process restoration starts a new
process-local inspection session but does not replay an action automatically.

The current `trip_return` event is an anonymous explicit saved-trip-content
return proxy. The original cross-day unique-user KPI cannot be calculated until
the product approves a real multi-day trip-start boundary and a consented,
privacy-reviewed anonymous aggregation strategy. T090 does not invent either.

The only free string is `poi_id`, already approved by T018 as a stable curated
product identifier. The schema cannot represent a query, transcript, prompt,
response, narration, itinerary content, title, notes, date, exact coordinate,
address, Firebase identity/email/account key, token/header, request/response
body, database row, exception/stack trace, advertising identifier, secret or
API key. Hashes of those values are equally excluded.

Debug inspection uses a debug-only content provider guarded by Android's
signature-level `android.permission.DUMP`, so ADB shell can inspect it while
ordinary applications cannot. It does not use logs as analytics:

```bash
adb shell content query \
  --uri content://com.kltn.travelassistant.analytics/events
adb shell content delete \
  --uri content://com.kltn.travelassistant.analytics/events
```

### T090 manual validation evidence (completed 2026-08-09)

User-supplied full manual validation passed every required product, lifecycle,
privacy and isolation gate:

- Navigation detail-open and navigation-request stages emitted as specified;
  lifecycle retention and duplicate taps did not duplicate them, while an
  explicit reopened detail session could emit again.
- Valid online itinerary generation produced one attempt and one terminal
  result. Success, cancellation without stale terminal output, typed failure,
  explicit retry, offline exclusion and invalid-form exclusion passed.
- Voice-origin success, partial and failed results passed. Manual input, manual
  editing after voice input, cancellation and stale-result suppression emitted
  no false voice result.
- Anonymous saved-trip return passed for both verified accounts. Same-open
  duplication was suppressed, explicit reopen emitted again, and signed-out and
  cross-account content remained isolated.
- Geocontext content and empty states passed together with same-session
  deduplication and cancelled/stale-result suppression.
- Force-stop cleared the process-local buffer and relaunch replayed no event.
- Provider inspection contained no prohibited sentinel, query, transcript,
  content, coordinate, address, identity or token data. Analytics generated no
  network, Firebase-token, provider, backend or OpenAI request, and T071/T080
  regression checks passed.

No raw sentinel value, private account detail or unapproved event value is
retained in this evidence.

## Agent evaluations

### Router

- Intent accuracy.
- Entity extraction.
- Correct specialist selection.
- Unnecessary agent-call rate.

### Discovery

- Recall of valid candidate POIs.
- Evidence that requested dish exists.
- Correct handling of missing fields.
- Ranking input completeness.

### Narration/local culture

- 100–200 words.
- Key points first.
- Source coverage.
- No unsupported historical claims.
- Vietnamese clarity.

### Itinerary

- No time overlap.
- Respects opening hours when known.
- Reasonable travel transitions.
- Fits requested time and budget.

### Reviewer/composer

- Unsupported claims removed.
- Prices include update timestamp.
- Final response preserves specialist facts.
- Partial failures are disclosed.

## Initial eval dataset

Create at least:

- 40 food/nearby queries.
- 20 narration queries.
- 20 itinerary requests.
- 20 local-culture queries.
- 20 adversarial/missing-data cases.
