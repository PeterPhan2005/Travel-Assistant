# Itinerary Agent

## Purpose

Create a structured itinerary draft from constraints and candidate POIs.

## Input

- Date/time window.
- Start point.
- Budget.
- Pace.
- Preferences.
- Candidate POIs with hours and visit durations.

## Output

- Ordered itinerary items.
- Start/end time.
- Estimated travel time.
- Reason for each stop.
- Budget estimate.
- Assumptions and warnings.

## Allowed tools

- Candidate POI lookup.
- Travel-time estimator.
- Opening-hours service.

## Forbidden

- No booking.
- No hidden mutation of saved itinerary.
- No impossible schedule.
- No invented opening hours.

## Fallback

Return a partial itinerary with explicit gaps.
