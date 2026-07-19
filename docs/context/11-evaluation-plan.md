# Evaluation Plan

## Product KPIs

- Navigation conversion:
  POI detail sessions with “Dẫn đường” / POI detail sessions.
- Itinerary creation success:
  valid itinerary responses / generation requests.
- Voice intent accuracy:
  correctly detected intent + primary entity / labeled voice queries.
- Return during trip:
  users opening app on at least two trip days / users starting a trip.
- Geocontext opens:
  sessions using current location and nearby content.

## Agent evaluations

### Router

- Intent accuracy.
- Entity extraction.
- Correct specialist selection.
- Unnecessary agent-call rate.

### Discovery

- Recall of valid candidate POIs.
- Evidence that requested dish exists.
- Correct handling of missing fields.
- Ranking input completeness.

### Narration/local culture

- 100–200 words.
- Key points first.
- Source coverage.
- No unsupported historical claims.
- Vietnamese clarity.

### Itinerary

- No time overlap.
- Respects opening hours when known.
- Reasonable travel transitions.
- Fits requested time and budget.

### Reviewer/composer

- Unsupported claims removed.
- Prices include update timestamp.
- Final response preserves specialist facts.
- Partial failures are disclosed.

## Initial eval dataset

Create at least:

- 40 food/nearby queries.
- 20 narration queries.
- 20 itinerary requests.
- 20 local-culture queries.
- 20 adversarial/missing-data cases.
