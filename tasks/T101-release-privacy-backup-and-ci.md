---
id: T101
title: Harden release privacy backup and CI
status: todo
depends_on: [T090, T099, T100]
area: quality
---

# Goal

Audit and harden the real release artifact before release-candidate freeze.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md` files.
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/11-evaluation-plan.md`
- `docs/context/12-progress-tracker.md`
- `android/app/src/main/AndroidManifest.xml`
- `android/app/src/main/res/xml/backup_rules.xml`
- `android/app/src/main/res/xml/data_extraction_rules.xml`
- `.github/workflows/ci.yml`

# Scope

- Audit cloud backup and device-transfer policy for Room, DataStore and all
  account-owned state.
- Prevent restore leakage across accounts, sign-out and account deletion.
- Prove debug analytics, demo providers and debug Firebase are absent from the
  release artifact.
- Prove release has no localhost/cleartext dependency, unnecessary permission
  or embedded secret.
- Add release-variant build/test coverage and an automated credential/config
  scan to CI.
- Run a release-like target-device smoke test.

# Acceptance criteria

- [ ] Backup/device-transfer rules cover all sensitive Room/DataStore/account state.
- [ ] Restore cannot leak data across accounts or resurrect deleted ownership state.
- [ ] Debug analytics, demo providers and debug Firebase are absent from release.
- [ ] Release has no localhost, cleartext, unnecessary permission or secret.
- [ ] Release-variant build/tests and credential/config scan run in CI.
- [ ] A release-like target-device smoke test passes.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
./gradlew test lintRelease assembleRelease
ruff check backend
mypy --strict backend/app backend/tests
pytest backend
```

# Expected evidence

- Backup/transfer and release-artifact audit results.
- CI/release-variant/credential-scan results.
- Exact files changed and known limitations.

