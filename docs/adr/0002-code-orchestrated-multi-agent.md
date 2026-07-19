# ADR 0002: Code-Orchestrated Independent Agents

## Status

Accepted.

## Decision

Use separate specialist agent executions coordinated by Python application code. Specialists receive scoped structured input and return typed output.

## Rationale

This makes independence observable, testable and traceable. It avoids a single shared session pretending to be multiple agents.

## Consequences

- More model calls than a single-agent loop.
- Explicit latency and token budgets required.
- Stronger contracts and eval coverage.
