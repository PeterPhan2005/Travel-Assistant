---
id: T071
title: Persist and sync itineraries
status: done
depends_on: [T030, T070, T024]
area: fullstack
---

# Goal

Add itinerary CRUD endpoints, Room storage and authenticated synchronization.

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

- [x] Ownership enforced.
- [x] Offline saved itinerary is readable.
- [x] Sync conflicts are deterministic.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
pytest
./gradlew test
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.

# Completion record (2026-08-04)

- Reuses T030 PostgreSQL itinerary/item models and T013 Room itinerary/item
  tables; no parallel persistence model was introduced.
- Alembic `20260803_0002` adds the approved saved snapshot fields, explicit
  integer revision and owner-scoped tombstones; PostgreSQL/PostGIS was healthy
  at head during validation.
- Canonical private list/get/full-snapshot PUT/delete routes derive ownership
  only from verified Firebase UID. Two verified development accounts proved
  create/list/get/update/delete ownership and safe cross-owner `404` behavior.
- Valid writes increment the integer revision, stale writes return typed
  `409 itinerary_conflict`, delete creates the expected revision/tombstone,
  repeated delete is idempotent and stale PUT cannot resurrect deleted data.
- Room migration 2→3 adds hashed account key, approved snapshot fields,
  local/server revisions, typed sync/deletion state and an account/read index.
- Explicit save is local-first and atomic. Saved content is readable from Room
  after force-stop/relaunch while offline, in the original item order, while
  remote state remains visibly pending until worker success.
- Unique per-itinerary connected WorkManager work reloads current Room state,
  fetches an ephemeral token, refreshes one 401 at most, guards stale completion
  by local revision and caps retry at five attempts.
- Local data is retained after sign-out but filtered by current hashed account
  key. Account B could not see account A data; returning to account A restored
  its retained local library.
- Emulator validation proved generation never auto-saves, explicit local save,
  offline pending/read/relaunch, reconnect-to-synced, live conflict with readable
  local content, explicit delete and no automatic generation or save.
- An older queued upload was proven unable to resurrect a deleted itinerary.
- The same explicit-save, offline force-stop/read, online sync, account
  isolation and delete flow passed on nubia V60 serial `320143952923`; the ADB
  reverse rule was removed afterward.
- Backend and process-only Android privacy scans used a unique itinerary-title
  sentinel. The sentinel, token/Authorization, UID/email/account key,
  coordinates, request/response bodies, database-row content, tracebacks and
  provider exception text were absent.
- Final automated evidence passed: Ruff; strict Mypy over 180 source files;
  816 Pytest tests with zero skips/failures; T050 43/43; Pip check; 246 Android
  JVM tests; 133/133 connected tests; `lintDebug`, `testDebugUnitTest` and
  `assembleDebug`; and migration to Alembic `20260803_0002`.
- Validation used the deterministic no-model path with no OpenAI model
  configuration. Live-model validation was not run and is not a T071 completion
  gate. T080, T090 and T091 were not started or modified.
