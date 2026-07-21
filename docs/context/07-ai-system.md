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

The locked core runtime path is:

Router Agent → Discovery Agent → deterministic ranking → Grounding Reviewer
Agent → Response Composer Agent.

1. Application code gathers deterministic context such as location and speech
   transcript before or around routing as needed.
2. Router Agent returns an execution plan.
3. Discovery Agent retrieves candidate evidence; it does not determine the final
   order.
4. Application code applies deterministic ranking and validators.
5. Narration, Local Culture and Itinerary agents run only when selected for the
   request; independent optional work may run in parallel.
6. Grounding Reviewer checks ranked discovery results, optional specialist
   outputs, evidence and missing fields.
7. Response Composer creates the final user-facing response without adding facts
   or changing the deterministic rank.

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
