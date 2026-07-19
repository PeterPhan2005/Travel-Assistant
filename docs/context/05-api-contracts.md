# API Contracts

## POST /v1/assistant/query

Input:

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

Output:

```json
{
  "request_id": "uuid",
  "intent": "find_food",
  "message": "string",
  "poi_results": [],
  "narration": null,
  "itinerary": null,
  "sources": [],
  "warnings": []
}
```

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
