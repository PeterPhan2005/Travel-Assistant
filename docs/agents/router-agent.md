# Router Agent

## Purpose

Classify a user request and produce an execution plan. It does not answer the user and does not call POI/content providers.

## Input

- Current user text.
- Locale.
- Online/offline state.
- Minimal trip context.
- Available capability flags.

## Output

- Intent.
- Extracted entities.
- Selected optional specialist agents, if the intent needs them.
- Whether agents can run in parallel.
- Missing information that materially blocks execution.
- Confidence.

## Allowed tools

None in the first version.

## Forbidden

- No user-facing prose.
- No POI facts.
- No itinerary construction.
- No full conversation history unless required.

## Fallback

Deterministic matcher for MVP intents: nearby, food, narration, local culture, itinerary.

## Evals

Correct intent, entity and specialist selection; low unnecessary-call rate.
