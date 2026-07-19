# Offline and Sync Specification

## Offline capability

- View downloaded POIs.
- Search aliases/dish names in local Room FTS.
- Filter by category, stored price, stored opening hours and straight-line distance.
- View downloaded narration and local culture.
- View and edit saved itinerary locally.
- Open external navigation if the map application can handle it.

## Not promised offline

- New AI generation.
- Realtime price/reviews/open status.
- Search outside downloaded POIs.
- Voice recognition on every device.
- New itinerary generation.
- Route optimization.

## Travel package

Package contains:

- Manifest with version, checksum and timestamps.
- POI records and aliases.
- Menu snapshots.
- Narrations and source labels.
- Local culture content.
- Optional itinerary.
- Optional thumbnails/audio later.

## Update policy

- Download is explicit.
- Wi-Fi is preferred for large package.
- Partial download is resumable.
- New package is written to staging tables/files.
- Check checksum before activation.
- Switch active package atomically.
- Keep previous package until the new one is valid.
