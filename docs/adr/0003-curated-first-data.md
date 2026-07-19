# ADR 0003: Curated-First Data

## Status

Accepted.

## Decision

Curated internal POI, menu, narration and local-culture data is the trust anchor. External providers enrich the data.

## Consequences

- Initial dataset work is manual.
- Provider outages do not break the core demo.
- Provenance and freshness must be stored per field/snapshot.
