---
id: T105
title: Add online live discovery to Explore
status: todo
depends_on: [T019, T080, T104]
area: fullstack
---

# Goal

Let Explore combine immediate local active-package results with bounded live
online discovery.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md` files.
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T019-offline-ui-state.md`
- `tasks/T080-offline-full-text-search.md`
- `tasks/T104-hybrid-online-poi-discovery.md`

# Scope

- Keep local active-package results immediately usable.
- Add bounded live discovery only when online, with an approved debounce or
  explicit-submit policy and stale-request cancellation.
- Present curated and external results together with provenance/attribution and
  deterministic duplicate suppression.
- Keep local results visible if the live provider fails.
- Add transient external-only POI detail and external map navigation.
- Validate online/offline behavior on Emulator and physical device.

# Storage/security boundaries

- Android contains no provider SDK or server credential.
- Do not insert external-only POIs into canonical Room merely to make detail
  navigation work.
- Offline creates zero live request.

# Acceptance criteria

- [ ] Local active-package results render immediately and survive provider failure.
- [ ] Online discovery is bounded and stale requests are cancelled.
- [ ] Offline mode creates zero live request.
- [ ] Curated/external coexistence, attribution and duplicate suppression are correct.
- [ ] External-only detail is transient and supports external map navigation.
- [ ] No provider SDK/credential or external-only canonical Room insertion exists on Android.
- [ ] Emulator and physical online/offline validation passes.
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

- Local/live state and request-cancellation policy.
- Attribution, transient-detail and online/offline device results.
- Exact files changed and known limitations.

