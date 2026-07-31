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

## GET /v1/pois/nearby

Query: `lat`, `lng`, `radius_m`, `category`, `query`.

## GET /v1/pois/{poi_id}

Returns canonical POI details, price timestamp and source metadata.

## POST /v1/itineraries/generate

Returns a structured draft plus validation warnings.

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
