---
id: T062
title: Implement structured itinerary generation transport
status: todo
depends_on: [T024, T033, T045, T048, T061, T070]
area: fullstack
---

# Goal

Connect the completed T070 structured itinerary form to an authenticated backend
draft-generation endpoint and return a validated itinerary draft without
persisting it.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md` files.
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/05-api-contracts.md`
- `docs/context/08-privacy-security.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T024-firebase-token-verification.md`
- `tasks/T033-nearby-api.md`
- `tasks/T045-itinerary-agent.md`
- `tasks/T048-code-orchestrator.md`
- `tasks/T061-voice-query-integration.md`
- `tasks/T070-itinerary-mobile-ui.md`
- `tasks/T071-itinerary-persistence-sync.md`

# Scope and ownership

- T062 owns structured itinerary draft generation transport.
- T070 owns the Android form and timeline presentation.
- T071 owns persistence, CRUD, offline saved-itinerary reading,
  synchronization and conflict handling.
- T090 owns real analytics.
- T062 must not implement T071 or T090 behavior.

# Canonical private endpoint

Implement exactly:

```text
POST /v1/itinerary-drafts/generate
```

The endpoint is generation-only. It must not create or update a saved
itinerary.

# Backend request contract

Accept only approved structured user input:

- `city`, limited to:
  - Ho Chi Minh City;
  - Bangkok.
- `local_date`.
- `timezone`.
- `start_local_time`.
- `end_local_time`.
- `maximum_stops`.
- Optional bounded `notes`.
- `locale`.
- `client_mode`.
- Optional paired latitude and longitude snapshot.

Android must not send internal candidates, evidence bundles, source IDs, claim
IDs or agent context. The backend must resolve request-scoped candidates and
evidence through the existing curated POI/provider/menu boundaries, then
construct the existing strict itinerary runtime context internally.

# Backend requirements

- Require Firebase authentication through the existing T024 boundary.
- Strictly validate the request and reject unknown fields.
- Enforce exact city/timezone consistency.
- Require a valid one-day time window.
- Require `maximum_stops` from 1 through 20.
- Accept coordinates only as a finite paired WGS84 latitude/longitude snapshot.
- Do not silently default, truncate, clamp or infer a city or another field.
- Do not serialize the request through a transcript, chat session or free-text
  workaround.
- Accept no audio.
- Perform no itinerary persistence, database write or commit.
- Use no WorkManager and add no automatic retry.
- Propagate cancellation.
- Use a request-scoped database session.
- Preserve the deterministic no-model fallback.
- Map results through safe transport-specific response models.
- Do not expose internal stages, trace IDs, prompts, usage, claim/source IDs,
  Firebase identity or coordinates.
- Do not log notes, coordinates, tokens, identity, itinerary content or raw
  request/response bodies.

# Android integration requirements

- Replace the production `UnsupportedTransport` generator with a typed
  repository.
- Reuse the validated backend-origin, Firebase-token and OkHttp patterns from
  T061.
- Fetch the Firebase token immediately before the request.
- After a 401, force-refresh the token at most once.
- Do not automatically retry any other result.
- Ensure coroutine cancellation cancels the active OkHttp call.
- Start no request while offline or signed out.
- Retry only after an explicit user action.
- Persist no request, response or itinerary.
- Map the public response into the existing T070 domain models.
- Preserve T070 validation and fail-closed timeline behavior.
- Do not expose transport or backend internal types in presentation state.

# Safe response contract

Return only a safe structured draft, including:

- Public result status: `success`, `partial` or `failed`.
- Selected city, date, timezone and time window.
- Chronological draft items.
- Item start and end times.
- Safe titles.
- Assumptions.
- Warnings.
- Retryability where appropriate.

Do not return:

- Internal candidates or evidence.
- Source or claim IDs.
- Agent or stage names.
- Request or trace IDs in Android UI.
- Firebase identity.
- Token usage.
- Prompts.
- Exact coordinates.
- Saved-itinerary IDs.

# Tests required

## Backend

- Authentication.
- Strict request validation.
- City/timezone consistency.
- Date and time-window validation.
- Maximum-stop validation.
- Coordinate pairing and bounds.
- Rejection of unknown, audio and internal fields.
- Request-scoped candidate/evidence construction.
- Exact runtime mapping.
- Deterministic fallback.
- Success, partial and failure response closure.
- Cancellation propagation.
- No persistence or database commit.
- No sensitive logging.
- Isolation through a fake injected generator/orchestrator.

## Android

- Exact endpoint and JSON request mapping.
- No audio or internal-evidence fields.
- Firebase token and one-401-refresh behavior.
- No retry for other failures.
- Cancellation cancels OkHttp.
- Offline and authentication-required states.
- Loading, cancellation and explicit retry.
- Mapping into the existing T070 draft models.
- Invalid timeline response fails closed.
- No persistence or WorkManager.
- Existing T060, T061 and T070 behavior remains green.

# Manual validation

- Authenticated Emulator request.
- Authenticated nubia V60 request through ADB reverse.
- Ho Chi Minh City draft.
- Bangkok draft.
- Loading state.
- Explicit cancellation.
- Explicit retry.
- Offline state.
- Signed-out state.
- No restoration after force-stop.
- No automatic save.
- Privacy-safe Android and backend logs.
- Report deterministic fallback separately from live-model validation.

# Acceptance criteria

- [ ] The authenticated structured generation endpoint works.
- [ ] The backend derives approved candidates and evidence internally.
- [ ] Android renders a real validated draft through the T070 UI.
- [ ] Loading, cancellation, retry, authentication and offline behavior works.
- [ ] No itinerary is persisted.
- [ ] Privacy and logging requirements pass.
- [ ] Relevant tests and documentation are updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

## Backend

```bash
ruff check .
mypy --strict app tests
pytest
python -m app.agent_evals check
pip check
```

## Android

```bash
./gradlew test
./gradlew connectedDebugAndroidTest
./gradlew lintDebug
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

# Completion policy

- Fake transport tests alone are insufficient.
- Authenticated Android-to-local-backend validation is required.
- Deterministic fallback is acceptable.
- Live OpenAI validation remains separate.
- Do not mark T062 done while production Android still uses
  `UnsupportedTransport`.
- Do not begin T071 until T062 and T070 are complete and exact-SHA CI is green.

# Expected evidence

- Concise summary.
- Exact files changed.
- Backend and Android test/check output.
- Authenticated Emulator and nubia V60 validation evidence.
- Privacy-safe log review.
- Deterministic fallback and live-model validation reported separately.
- Known limitations.
