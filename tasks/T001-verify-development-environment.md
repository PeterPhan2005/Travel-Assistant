---
id: T001
title: Verify development environment
status: todo
depends_on: [T000]
area: foundation
---

# Goal

Add a checked setup script/document that verifies Git, Android tooling, Python, Docker, Node and Codex CLI.

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

- [ ] A new developer can follow SETUP.md.
- [ ] Verification commands are documented.
- [ ] Known machine-specific gaps are recorded.
- [ ] Relevant tests are added or updated.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
python --version
docker --version
node --version
codex --version
```

# Expected evidence

- Concise summary.
- Exact files changed.
- Test/check output.
- Known limitations.
