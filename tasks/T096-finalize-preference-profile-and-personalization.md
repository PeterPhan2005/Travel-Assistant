---
id: T096
title: Finalize preference profile and personalization
status: done
depends_on: [T025, T090, T092, T093]
area: fullstack
---

# Goal

Turn the existing generic preference sync into an explicit, bounded,
user-editable travel preference product and use it only at approved
personalization boundaries.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md` files.
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T025-preferences-sync.md`
- `tasks/T090-product-analytics.md`

# Scope

- Define one explicit closed travel-preference taxonomy and versioned typed
  contract.
- Add authenticated read, edit and reset UI with clear user control.
- Preserve T025 account isolation, offline-first local behavior, complete-
  document synchronization and revision-safe in-flight edit handling.
- Use preferences only at explicitly approved deterministic ranking and scoped
  agent-context boundaries.
- Preserve current behavior when preferences are absent.
- Add privacy and account-switch coverage.

# Privacy boundaries

- Do not create hidden or inferred sensitive profiles.
- Do not store exact-location history or derive preference values from it.
- Do not place identity, credentials or preference content in logs or
  analytics.

# Out of scope

- Recommendation behavior outside the approved ranking/agent-context seams.
- Background location, advertising profiles or unreviewed sensitive traits.
- T097 and later release work.

# Acceptance criteria

- [x] The preference taxonomy is closed, typed, versioned and documented.
- [x] Users can read, edit and explicitly reset their preferences.
- [x] Missing preferences preserve existing behavior.
- [x] Offline edits, revision-safe sync and account isolation remain correct.
- [x] Personalization is limited to approved ranking and scoped agent context.
- [x] No hidden sensitive profile or exact-location history is created.
- [x] Privacy, sign-out and two-account switching tests pass.
- [x] Relevant Android/backend tests and documentation are updated.
- [x] Required checks pass or failures are documented.
- [x] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
ruff check .
mypy --strict app tests
pytest
./gradlew test
./gradlew connectedDebugAndroidTest
```

# Expected evidence

- Exact taxonomy and approved personalization seams.
- Account/offline/privacy test results.
- Exact files changed and known limitations.

# Phase 1 decision checkpoint (2026-08-12)

T096 phase 1 is documentation/decision work only. The current generic
schema-version-1 contract, Android account isolation and synchronization races
were audited before any product implementation.

The recommended proposal, which is **not approved or final**, is travel
taxonomy version 1 carried by document schema version 2. Reusing document
schema version 1 would silently reinterpret existing generic documents. The
proposed closed fields are `interests` (at most five values from a closed travel
interest enum), `pace` (`relaxed`, `balanced` or `active`) and
`budget_preference` (`budget`, `moderate` or `premium`). Missing fields and an
empty document mean no personalization.

The proposed personalization boundaries are application-owned deterministic
ranking over already eligible POI candidates and a request-scoped typed agent
projection. No model may rank, derive preferences or receive the stored
document automatically. The proposed reset is an explicit full replacement
with an empty schema-version-2 document; it is not sign-out, local-only default
reset or server-row deletion.

Approval is still required for the taxonomy, ranking order, agent projection,
retrieval policy, reset contract and legacy-version migration before phase 2
may implement production or test code. T097 and later tasks remain unstarted.

# Approved phase 2 contract and completion (2026-08-15)

The user approved the phase-1 plan before implementation. Travel taxonomy
version 1 is carried by document schema version 2, with the exact values and
personalization seams documented in `docs/context/03-architecture.md`.
Schema-version-1 data remains opaque compatibility data; v2 upgrades it, while
v1 cannot overwrite v2. Reset is a complete canonical empty-v2 replacement.

Android now exposes authenticated Vietnamese read/edit/cancel/save/reset UI,
explicit offline/sync/error state and the existing per-account revision-safe
sync. Missing or legacy data produces no personalization until the user saves
v2. Application code soft-ranks only already eligible POIs; Router/Discovery
receive no profile, while the Response Composer receives only an approved,
request-scoped, identity-free typed projection. No preference is inferred,
logged, analyzed or derived from location history.
