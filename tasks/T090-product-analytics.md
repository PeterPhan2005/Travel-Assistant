---
id: T090
title: Instrument MVP KPIs
status: done
depends_on: [T018, T061, T070]
area: fullstack
---

# Goal

Add events for navigation conversion, itinerary success, voice intent result, trip return and geocontext opens.

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

- [x] Event schema documented.
- [x] No exact coordinates/transcripts in analytics.
- [x] Debug event inspection works.
- [x] Relevant tests are added or updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test
pytest
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.

# Completion record (2026-08-09)

Android owns the closed schema-version-1 model for navigation conversion,
itinerary creation, voice-origin intent results, anonymous saved-itinerary
returns and geocontext opens. Navigation detail/request stages, itinerary
attempt/terminal pairs, voice origin, saved-item sessions and geocontext
sessions use explicit process-local state for at-most-once behavior; process
death clears the buffer and never replays an action.

Release builds use a no-op sink. Debug builds retain at most 200 encoded events
in process memory and expose them only through a debug-only,
`android.permission.DUMP`-protected inspection provider. There is no vendor SDK,
upload, retry, durable analytics store, background delivery or backend analytics
path. The only free string is a validated stable curated product POI ID; all
other properties are closed values, and prohibited query, transcript, content,
coordinate, identity, token, body, exception, device and secret data cannot be
encoded.

Automated validation passed 270/270 Android JVM tests, 141/141 connected tests,
debug lint/unit/assembly and 816/816 backend tests with healthy PostGIS, all with
zero skips or failures where applicable. User-supplied full manual validation
passed navigation lifecycle/reopen and duplicate-tap behavior; itinerary
attempt/success/cancel/failure/retry, invalid/offline exclusion and stale-result
behavior; voice success/partial/failure, manual-edit exclusion and cancellation;
two-account saved-trip isolation/reopen behavior; geocontext content/empty,
deduplication and cancellation; force-stop/no-replay behavior; provider privacy;
network isolation; and T071/T080 regression checks.

Genuine limitations remain: `trip_return` is an anonymous explicit saved-item
open proxy rather than a unique-user multi-day cohort KPI; analytics is
best-effort and process-local; and release collection remains disabled until a
vendor, consent and delivery policy is separately approved.
