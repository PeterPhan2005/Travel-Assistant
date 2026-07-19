# Code Standards

## General

- Small modules with one responsibility.
- Prefer explicit types and structured contracts.
- Validate all external input.
- Fix root causes; do not stack workarounds.
- No secrets or environment-specific values in source control.
- Add tests before marking a task complete.

## Kotlin

- Kotlin style guide and formatter enforced.
- Immutable data classes for UI/domain state.
- No `!!` except in test fixtures with justification.
- Coroutines must be lifecycle-safe.
- Repositories own caching and source selection.
- Composables contain presentation only.

## Python

- Ruff format/lint.
- Mypy on application modules.
- Async I/O for database and provider calls.
- Pydantic at API and agent boundaries.
- Dependency injection through FastAPI dependencies/context objects.
- Tool functions return typed domain results, not raw provider payloads.

## API

- Version endpoints under `/v1`.
- Consistent error envelope.
- Request ID on every request.
- Timeout and retry policies documented per provider.
