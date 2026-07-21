# ADR 0002: Code-Orchestrated Independent Agents

## Status

Accepted.

## Decision

Use separate agent executions coordinated by Python application code. The core
runtime path is Router → Discovery → deterministic ranking → Grounding Reviewer
→ Response Composer. Narration, Local Culture and Itinerary are optional
specialists selected by intent. Agents receive scoped structured input and return
typed output; deterministic ranking is performed by application code, not an
agent.

## Rationale

This makes independence observable, testable and traceable. It avoids a single shared session pretending to be multiple agents.

## Consequences

- More model calls than a single-agent loop.
- Explicit latency and token budgets required.
- Stronger contracts and eval coverage.
- Optional specialist output must pass through grounding review before response
  composition.
