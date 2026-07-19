# Privacy and Security

## Agreed retention

- Exact location history: not stored server-side.
- Location used in a request: logs must be rounded or removed; operational retention 7–30 days.
- Itinerary: retained until user deletes it/account.
- Preferences: retained until user deletes them/account.
- Voice audio: not stored.
- Transcript: not stored by default; analytics stores only intent and success state.
- Trip context: archive/delete 30 days after trip end unless explicitly retained.

## Security controls

- Firebase ID token required for private endpoints.
- Backend verifies token signature and audience.
- Row ownership enforced for preferences, trips and itineraries.
- Rate limits on assistant and provider endpoints.
- Secrets only in environment/secret manager.
- HTTPS only outside local development.
- Agent tools receive least privilege.
- Logs redact authorization headers, exact coordinates and provider secrets.

## User permissions

- Location requested when opening nearby features.
- Microphone requested only after tapping voice input.
- Background location is outside MVP.
