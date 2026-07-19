---
id: T091
title: Add end-to-end demo tests
status: todo
depends_on: [T061, T071, T080, T090]
area: quality
---

# Goal

Automate the key HCMC online flow and offline package flow; document manual GPS/microphone checks.

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

- [ ] Food query reaches navigation.
- [ ] Narration displays source.
- [ ] Offline search works after network disable.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew connectedDebugAndroidTest
pytest
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
