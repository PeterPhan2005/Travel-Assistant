# Privacy and Security

## Agreed retention

- Exact location history: not stored server-side.
- Location used in a request: logs must be rounded or removed. The accepted
  operational-retention range is 7–30 days; the exact production duration is an
  explicit open question in the progress tracker.
- Itinerary: retained until user deletes it/account.
- Preferences: retained until user deletes them/account.
- Voice audio: not stored or uploaded by TravelAssistant.
- Transcript: confirmed text is sent only in the foreground assistant request
  and is not persisted by Android or backend. T061 analytics is a no-op boundary
  that receives only closed intent and outcome values; T090 owns any future
  analytics storage.
- Structured itinerary form values and the optional current in-memory location
  are used only by the foreground generation request. Android and backend do not
  persist the request, draft or coordinates in T062; logs omit form values,
  identity, token, coordinates, itinerary content and raw bodies. Completed
  Emulator/nubia manual review confirmed the sentinel note, Authorization/token,
  UID/email, exact coordinates, itinerary bodies/content and provider failure
  details were absent from backend and process-only Android logs; no audio was
  uploaded and no itinerary was persisted.
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
