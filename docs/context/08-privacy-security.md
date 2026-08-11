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
  and is not persisted by Android or backend. The T090 product-analytics adapter
  receives only closed intent/outcome values plus transient manual/voice origin;
  only a terminal voice-origin result emits, and debug inspection retains no
  transcript.
- Structured itinerary form values and the optional current in-memory location
  are used only by the foreground generation request. T062 does not persist its
  request or coordinates. After explicit save, T071 persists only the approved
  saved snapshot: title, city/date/timezone/window, ordered item IDs/titles/times,
  assumptions, warnings, revisions and sync/deletion state. It persists no form
  notes, coordinates, Firebase UID/token, transcript, source/claim/trace/model
  metadata or generation prompt. Logs omit form values, identity, token,
  coordinates, itinerary content, database rows and raw bodies. Completed
  Emulator/nubia manual review confirmed the sentinel note, Authorization/token,
  UID/email, exact coordinates, itinerary bodies/content and provider failure
  details were absent from backend and process-only Android logs; no audio was
  uploaded and no itinerary was persisted during T062 validation. T071 then
  completed separate two-account, Emulator and nubia V60 validation. A unique
  itinerary-title sentinel, token/Authorization, UID/email/account key,
  coordinates, request/response bodies, database-row content, tracebacks and
  provider exception text were absent from backend and process-only Android
  logs.
- Android derives a SHA-256 account key from verified UID. Saved rows remain on
  device after sign-out but are inaccessible until the same verified account
  returns; another account cannot query them. Worker input contains only the
  itinerary UUID, never UID/account key/token/content.
- Offline POI search keeps both raw and normalized queries transient. They are
  compiled only into parameterized local Room/FTS operations and are never
  persisted, logged, uploaded, included in analytics or used to request a
  Firebase token. Result titles/content, coordinates, database rows and SQL
  containing user text are likewise excluded from logs.
- T090 product analytics is Android-local and schema-versioned. Debug retains a
  bounded process-memory record only; release is no-op. It has no vendor SDK,
  persistence, upload, background work or backend route. Events contain only
  closed stages/outcomes/result states/intents and the T018-approved stable POI
  ID. Raw or normalized queries, Assistant transcript, model prompt/response,
  POI/itinerary/narration content, coordinates, address, UID/email/account key,
  token/header, raw bodies, database rows, exception detail, device/advertising
  identifiers, secrets and hashes of those values are forbidden.
- Trip context: archive/delete 30 days after trip end unless explicitly retained.
- Fresh-web evidence is request-scoped. Raw HTML/page bodies are not retained,
  mirrored into the canonical database or written to logs. Only bounded typed
  provenance/evidence allowed by the accepted contract may continue through a
  request.
- External live POI content is transient unless provider policy and accepted
  architecture explicitly permit a stored field. There is no bulk provider
  mirror and no Google-only canonical Room insertion solely for detail
  navigation.

## Security controls

- Firebase ID token required for private endpoints.
- Backend verifies token signature and audience.
- Row ownership enforced for preferences, trips and itineraries.
- Rate limits on assistant and provider endpoints.
- Secrets only in environment/secret manager.
- HTTPS only outside local development.
- Google Places and web-research credentials remain server-side; Android and
  agent input receive no provider credential.
- Agent tools receive least privilege.
- Logs redact authorization headers, exact coordinates and provider secrets.
- Saved-itinerary CRUD logs only operation, safe result category and aggregate
  count; they never log snapshot/tombstone content or owner identity.
- Fresh-web fetching is application-controlled and enforces HTTPS, SSRF
  protection, private/link-local/loopback rejection except explicit local test
  seams, bounded redirects/timeouts/body size/content types/searches/fetches,
  one overall research deadline and cancellation.
- No arbitrary authorization is forwarded to fetched targets. Webpage content
  is untrusted data, never instructions; prompt-injection text cannot change
  application/system instructions. Bounded evidence is extracted before agent
  use and still requires Grounding Reviewer claim/source closure.
- Source provenance preserves source identity/class, retrieval time, available
  publication/source-update time, geographic scope and freshness category.
  Stale evidence does not satisfy a freshness-sensitive claim automatically.

## User permissions

- Location requested when opening nearby features.
- Microphone requested only after tapping voice input.
- Background location is outside MVP.
