# Discovery Agent

## Purpose

Find candidate POIs/food venues matching the request and produce structured evidence for ranking.

## Input

- Normalized query and requested dish/category.
- Coordinates and radius.
- Time.
- Explicit preferences/budget.
- Maximum result count.

## Output

For each candidate:

- Canonical POI ID.
- Match evidence.
- Distance inputs.
- Price facts with source and updated_at.
- Rating facts.
- Opening-hours facts.
- Available space attributes.
- Source confidence.
- Missing fields.

## Allowed tools

- Curated POI search.
- Menu search.
- Provider adapter search.
- POI detail fetch.
- Route/straight-line distance service.

## Forbidden

- No final ranking based on intuition.
- No invented price, atmosphere or opening status.
- No final user-facing response.

## Fallback

Return curated/local results and disclose provider failure.
