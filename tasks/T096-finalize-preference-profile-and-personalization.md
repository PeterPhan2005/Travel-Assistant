---
id: T096
title: Finalize preference profile and personalization
status: todo
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

- [ ] The preference taxonomy is closed, typed, versioned and documented.
- [ ] Users can read, edit and explicitly reset their preferences.
- [ ] Missing preferences preserve existing behavior.
- [ ] Offline edits, revision-safe sync and account isolation remain correct.
- [ ] Personalization is limited to approved ranking and scoped agent context.
- [ ] No hidden sensitive profile or exact-location history is created.
- [ ] Privacy, sign-out and two-account switching tests pass.
- [ ] Relevant Android/backend tests and documentation are updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

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

