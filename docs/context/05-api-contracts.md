# API Contracts

## POST /v1/assistant/query

Private endpoint. Requires a verified Firebase Bearer ID token. The authenticated
UID authorizes only this request and is not passed to the agent runtime, returned,
logged or persisted.

Strict input (`Content-Type: application/json`, unknown fields rejected):

```json
{
  "text": "Tôi muốn ăn phở",
  "latitude": 10.776,
  "longitude": 106.700,
  "locale": "vi-VN",
  "trip_id": null,
  "client_mode": "online"
}
```

`text` is trimmed, preserves Unicode, rejects blank/control-character input and
is limited to 500 Unicode code points without truncation. `locale` follows the
existing strict locale contract; Android sends `vi-VN`. Latitude/longitude must
be supplied together as finite WGS84 values or both omitted. They are used only
as a request-scoped discovery origin. `trip_id` is currently required to be
null; non-null trip behavior is not implemented. `client_mode` accepts only
`online`. No audio, file, URI, bytes, recording or MIME field is accepted.

Success/partial/failed runtime output:

```json
{
  "request_id": "uuid",
  "status": "success",
  "intent": "nearby_discovery",
  "message": "string",
  "poi_results": [],
  "narration": null,
  "itinerary": null,
  "sources": [],
  "warnings": [],
  "retryable": false
}
```

`status` is one of `success`, `partial`, `failed`. `intent` uses the closed
Router taxonomy and is null only when no validated Router output exists.
`message` is composer-approved final text or the fixed safe failed-runtime
message. POIs contain only composer-approved presentation fields; missing
address, distance, rating/count, price and opening-hours values remain null.
Price uses integer `minor_units`, ISO-4217 `currency` and an aware `updated_at`.
Sources contain only public label/publisher/URL/timestamps referenced by the
approved final output and expose no internal source ID. Warnings contain only
bounded safe message/retryability. Optional narration and draft itinerary omit
claim/source/POI IDs. The response never contains request coordinates, Firebase
identity/token, trace or model identifiers, stage structures/timing, token
usage, prompts, exceptions, arbitrary metadata or audio.

## GET /pois/nearby

Query: `lat`, `lng`, `radius_m`, `category`, `query`.

## GET /v1/pois/{poi_id}

Returns canonical POI details, price timestamp and source metadata.

## POST /v1/itinerary-drafts/generate

Private generation-only endpoint. A verified Firebase Bearer ID token is
required. Missing, invalid and temporarily unverifiable credentials use the
shared sanitized `401 authentication_required`, `401 invalid_token` and
`503 authentication_unavailable` policy.

Strict input rejects unknown fields and accepts exactly:

```json
{
  "city": "hcmc",
  "local_date": "2026-08-01",
  "timezone": "Asia/Ho_Chi_Minh",
  "start_local_time": "09:00",
  "end_local_time": "17:00",
  "maximum_stops": 4,
  "notes": null,
  "locale": "vi-VN",
  "client_mode": "online",
  "latitude": null,
  "longitude": null
}
```

`city` is only `hcmc` or `bkk`, with exact timezone closure to
`Asia/Ho_Chi_Minh` or `Asia/Bangkok`. Date and minute-aligned local times are
strict, start is before end, maximum stops is an integer 1–20, notes are at
most 500 Unicode code points, and coordinates are either an absent pair or a
finite WGS84 pair. Audio, transcript, candidates, evidence and internal IDs are
not part of the contract.

Every validly processed request returns HTTP 200 with closed `status` of
`success`, `partial` or `failed`, exact request city/date/timezone/window,
bounded chronological items, assumptions, safe warnings, optional stable
`failure_category`, and `retryable`. The JSON contains no coordinates,
distance/provider/candidate/evidence/claim/source IDs, Firebase identity,
request/trace ID, agent metadata, prompts, usage or saved-itinerary ID. The
operation performs no itinerary persistence or commit.

The public response uses Pydantic's canonical JSON serialization for Python
`time` values: every minute-aligned response window and item time is exactly
`HH:mm:ss` with seconds `00` (for example, `"09:00:00"`). Android request fields
remain the strict form contract `HH:mm`; its response codec accepts only the
canonical whole-minute response representation and rejects format drift or
nonzero seconds.

## Private saved itineraries under /v1/itineraries

Every route requires a verified Firebase Bearer token. UID/owner is never
accepted from path, query or body. Cross-owner IDs use the same non-enumerating
`404 itinerary_not_found` result as absent IDs.

- `GET /v1/itineraries` returns `{"itineraries": [...]}` in deterministic
  local-date descending, update descending, UUID ascending order.
- `GET /v1/itineraries/{itinerary_uuid}` returns one current owned snapshot.
- `PUT /v1/itineraries/{itinerary_uuid}` creates or replaces one complete
  snapshot. The strict body contains `base_revision`, `title`, `city`,
  `local_date`, `timezone`, `start_local_time`, `end_local_time`, ordered
  stable-ID `items`, `assumptions` and `warnings` only.
- `DELETE /v1/itineraries/{itinerary_uuid}` accepts only
  `{"base_revision": integer}` and returns
  `{"id": uuid, "revision": integer, "deleted": true}`.

Create requires `base_revision = 0`; every accepted PUT increments the server
revision. Update/delete require the exact current revision. A stale revision
returns stable `409 itinerary_conflict`. Delete stores an owner/revision-backed
tombstone; repeated delete is idempotent, while every stale PUT remains a
conflict and cannot recreate the row. Parent and ordered children are written in
one explicit request-scoped transaction. Contracts reject unknown fields,
identity, coordinates, notes, audio/transcript, prompt/model/trace metadata and
arbitrary ORM values.

## GET /v1/travel-packages/{city}/manifest

Returns package version, size, checksum and asset list.

## GET /v1/travel-packages/{city}/download

Authenticated package download.

## GET/PUT /v1/me/preferences

Synchronize explicit preferences.

## Error shape

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "safe user-facing message",
    "request_id": "uuid"
  }
}
```
