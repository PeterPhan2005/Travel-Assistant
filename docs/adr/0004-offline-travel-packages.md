# ADR 0004: Offline Travel Packages

## Status

Accepted.

## Decision

Offline mode uses versioned destination packages downloaded before a trip and imported into Room.

## Consequences

- Offline search is limited to package content.
- Package checksum, staging and atomic activation are required.
- No on-device LLM is needed for MVP.
