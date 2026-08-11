---
id: T102
title: Implement Google Places live provider
status: todo
depends_on: [T032, T033, T092, T093, T097]
area: backend
---

# Goal

Implement the current contract-only `google_places` provider namespace as the
first real external online POI provider.

# Read first

- `AGENTS.md`
- `backend/AGENTS.md`
- `docs/context/00-project-overview.md`
- `docs/context/01-product-requirements.md`
- `docs/context/03-architecture.md`
- `docs/context/08-privacy-security.md`
- `docs/context/12-progress-tracker.md`
- `tasks/T032-poi-provider-contracts.md`
- `tasks/T033-nearby-api.md`
- `tasks/T097-api-rate-limits-and-ai-cost-guards.md`

# Scope

- Keep the provider credential server-side and environment/secret-manager only.
- Use strict minimal request fields, bounded result/radius/deadline policy and
  cancellation.
- Support text and nearby discovery as the selected API permits; request
  details only when necessary.
- Normalize quota, rate-limit, timeout, unavailable and invalid-response errors.
- Preserve stable external identity, provider attribution and typed provenance.
- Return only the T032 normalized result; no raw payload may escape or persist.
- Add deterministic fake tests and an explicitly separate live smoke test.

# Storage boundaries

- Do not bulk mirror Google content into canonical storage.
- Do not persist raw provider payloads.
- Do not place the server credential or a provider SDK requiring that credential
  in Android.

# Acceptance criteria

- [ ] The `google_places` adapter implements the unchanged T032 provider contract.
- [ ] Credential, request fields, radius, result count and deadlines are bounded.
- [ ] Text/nearby/details behavior is minimal and documented for the selected API.
- [ ] Stable external identity, attribution and provenance are normalized.
- [ ] Typed quota/rate/timeout/unavailable/invalid-response errors and cancellation work.
- [ ] No raw payload escapes or persists and no bulk mirror is created.
- [ ] Deterministic fake tests pass without network or credentials.
- [ ] A separately run live smoke result is documented without secrets or raw payloads.
- [ ] `docs/context/12-progress-tracker.md` is updated.

# Required checks

```bash
ruff check .
mypy --strict app tests
pytest
python -m app.agent_evals check
```

# Expected evidence

- Selected API operations/field masks and normalized contract mapping.
- Deterministic test and sanitized live-smoke results.
- Exact files changed and known limitations.

