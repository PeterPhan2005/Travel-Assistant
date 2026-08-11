---
id: T098
title: Implement account deletion and data lifecycle
status: todo
depends_on: [T021, T022, T025, T071]
area: fullstack
---

# Goal

Make the existing retention promises actionable through explicit,
user-confirmed account deletion.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md` files.
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T021-email-auth.md`
- `tasks/T022-google-auth.md`
- `tasks/T025-preferences-sync.md`
- `tasks/T071-itinerary-persistence-sync.md`

# Scope

- Add explicit confirmation and reauthentication for destructive account
  deletion.
- Delete the Firebase account and backend-owned account data through bounded,
  owned operations.
- Remove local account-owned DataStore and Room state.
- Prevent WorkManager jobs or stale responses from resurrecting deleted data.
- Define recoverable partial-failure behavior and safe retry/reconciliation.
- Prove two-account isolation and privacy.

# Invariants

- Sign-out is not account deletion.
- Another account's local or backend data must never be deleted or exposed.
- Credentials, account content and deletion payloads must not enter logs.

# Acceptance criteria

- [ ] Account deletion requires explicit confirmation and valid reauthentication.
- [ ] Firebase, backend-owned and local account-owned data follow the documented lifecycle.
- [ ] Preference and saved-itinerary state cannot be resurrected by stale work.
- [ ] Partial failures have a deterministic recoverable state.
- [ ] Sign-out remains behaviorally distinct from deletion.
- [ ] Two-account isolation and privacy tests pass.
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

- Deletion state machine and data inventory.
- Reauthentication, partial-failure, anti-resurrection and isolation results.
- Exact files changed and known limitations.

