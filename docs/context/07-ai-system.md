# AI System Specification

## Definition of real multi-agent for this project

A runtime agent is considered independent only when it has:

- Its own instructions.
- Its own allowed tools.
- Its own structured input and output contract.
- A separate model execution/agent loop.
- Scoped context rather than unrestricted shared history.
- Independent timeout, retry, trace and evaluation.
- A clear responsibility that another agent does not own.

## Orchestration

1. Router Agent returns an execution plan.
2. Application code gathers deterministic context.
3. Required specialists run separately; independent tasks may run in parallel.
4. Deterministic validators run.
5. Grounding Reviewer checks evidence and missing fields.
6. Response Composer creates the final user-facing response.

## Model configuration

Do not hardcode model names in business code. Use:

- `MODEL_ROUTER`
- `MODEL_SPECIALIST`
- `MODEL_REVIEWER`
- `MODEL_COMPOSER`

## Context boundaries

- Specialists do not receive the full user history by default.
- Discovery receives query, coordinates, filters and explicit preferences.
- Narration receives POI identity and retrieved source passages.
- Itinerary receives trip constraints and candidate POIs.
- Composer receives validated specialist outputs.
- Long-term preferences come from application storage, not agent session memory.

## Failure behavior

- If Router fails, use deterministic intent fallback for MVP intents.
- If a specialist fails, return partial results where safe.
- If Reviewer rejects unsupported claims, remove them rather than regenerate indefinitely.
- Limit agent turns and total latency.
