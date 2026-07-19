# ADR 0001: Android Native Kotlin

## Status

Accepted.

## Decision

Build the demo as an Android native app using Kotlin and Jetpack Compose.

## Rationale

The council accepts one platform. Android native avoids cross-platform plugin uncertainty for GPS, microphone, Firebase login and device testing. The team can focus on one release artifact.

## Consequences

- No iOS delivery before MVP.
- UI and device services use Android APIs directly.
- Backend remains platform-neutral for future clients.
