# Repository Instructions for Codex

## Source of truth

Before editing code, read:

1. `docs/context/00-project-overview.md`
2. `docs/context/01-product-requirements.md`
3. `docs/context/03-architecture.md`
4. The task file explicitly assigned by the user
5. Any nested `AGENTS.md` that applies to files being changed

## Task discipline

- Implement exactly one task file at a time.
- Do not implement future-task behavior.
- Do not combine Android, backend and data-pipeline changes unless the task explicitly allows it.
- Resolve ambiguity by documenting it in `docs/context/12-progress-tracker.md`; do not invent product behavior.
- Keep public contracts backward compatible unless the task is specifically a contract migration.
- Never commit secrets, API keys, service-account files or production credentials.

## Verification

- Run all checks listed in the task.
- Add or update tests for changed behavior.
- Report commands executed and their results.
- Update `docs/context/12-progress-tracker.md` after a meaningful change.

## Completion format

Return:

1. Summary.
2. Files changed.
3. Tests/checks run.
4. Known limitations.
5. Suggested next task ID, without implementing it.
