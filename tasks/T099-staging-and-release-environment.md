---
id: T099
title: Configure staging and release environment
status: todo
depends_on: [T035, T071, T094, T096, T097, T098, T105, T107]
area: fullstack
---

# Goal

Create one release-like HTTPS environment where real online features work.

# Read first

- `AGENTS.md`
- Applicable nested `AGENTS.md` files.
- `docs/context/00-project-overview.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/12-progress-tracker.md`
- `README.md`
- `SETUP.md`
- `.github/workflows/ci.yml`

# Scope

- Host the backend over HTTPS with PostgreSQL/PostGIS, migrations and explicit
  readiness behavior.
- Configure staging/release Firebase without reusing the debug project.
- Supply backend secrets only through environment or a managed secret store.
- Host immutable travel-package artifacts.
- Configure nonblank HTTPS release backend and package origins.
- Remove release dependence on localhost, ADB reverse and cleartext traffic.
- Document rollback, recovery and a target-device release-like smoke test.

# Out of scope

- Committing credentials, production secrets or service-account files.
- Final release-candidate freeze owned by T095.

# Acceptance criteria

- [ ] A release-like HTTPS backend is deployed with PostgreSQL/PostGIS at migration head.
- [ ] Readiness and rollback/recovery procedures are verified.
- [ ] Staging/release Firebase configuration is variant-safe and distinct from debug.
- [ ] Immutable travel packages are hosted and verifiable.
- [ ] Release backend/package origins are nonblank HTTPS values.
- [ ] Release behavior has no localhost, ADB reverse or cleartext dependency.
- [ ] A target-device release-like smoke test passes.
- [ ] No secret is committed or printed.
- [ ] Required checks pass or failures are documented.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
ruff check backend
mypy --strict backend/app backend/tests
pytest backend
./android/gradlew -p android test lintRelease assembleRelease
```

# Expected evidence

- Environment topology and secret/config inventory without secret values.
- Migration/readiness, immutable-package, rollback and target-device results.
- Exact files changed and known limitations.

