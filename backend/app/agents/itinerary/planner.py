"""Pure deterministic one-day itinerary planning."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.agents.contracts import (
    DiscoveryCandidate,
    ItineraryItem,
    ItineraryOutput,
    ItineraryRequest,
)
from app.agents.itinerary.errors import (
    ItineraryExecutionError,
    ItineraryFailureReason,
)
from app.agents.itinerary.instructions import APPROVED_ASSUMPTIONS


def plan_itinerary(request: ItineraryRequest) -> ItineraryOutput:
    """Build the same validated draft for the same validated request."""
    total_minutes = _available_minutes(request)
    selected = select_candidates(request, available_minutes=total_minutes)
    durations = _allocate_durations(total_minutes, len(selected))

    current = datetime.combine(request.local_date, request.start_local_time)
    items: list[ItineraryItem] = []
    for index, (candidate, duration) in enumerate(
        zip(selected, durations, strict=True),
        start=1,
    ):
        item_end = current + timedelta(minutes=duration)
        items.append(
            ItineraryItem(
                item_id=f"itinerary-item-{index:03d}",
                poi_id=candidate.id,
                title=candidate.canonical_name,
                start_local_time=current.time(),
                end_local_time=item_end.time(),
                supporting_claim_ids=(),
                supporting_source_ids=(),
            )
        )
        current = item_end

    output = ItineraryOutput(
        local_date=request.local_date,
        timezone=request.timezone,
        start_local_time=request.start_local_time,
        end_local_time=request.end_local_time,
        items=tuple(items),
        assumptions=APPROVED_ASSUMPTIONS,
        warnings=(),
        draft_only=True,
    )

    return output.validate_against(request)


def select_candidates(
    request: ItineraryRequest,
    *,
    available_minutes: int | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    """Apply constraints while preserving exact candidate input order."""
    constraints = request.constraints
    excluded = set(constraints.excluded_poi_ids)
    required = set(constraints.required_poi_ids)
    usable = tuple(
        candidate
        for candidate in request.candidates
        if candidate.id not in excluded
    )
    if not usable:
        raise ItineraryExecutionError(
            ItineraryFailureReason.NO_USABLE_CANDIDATES
        )

    usable_ids = {candidate.id for candidate in usable}
    if not required.issubset(usable_ids):
        raise ItineraryExecutionError(
            ItineraryFailureReason.UNSATISFIABLE_CONSTRAINTS
        )

    capacity = constraints.maximum_stops
    if available_minutes is not None:
        if available_minutes < len(required):
            raise ItineraryExecutionError(
                ItineraryFailureReason.UNSATISFIABLE_TIME_WINDOW
            )
        capacity = min(capacity, available_minutes)
    if capacity <= 0:
        raise ItineraryExecutionError(
            ItineraryFailureReason.UNSATISFIABLE_TIME_WINDOW
        )

    selected_ids = set(required)
    preferred_categories = set(constraints.preferred_categories)
    for candidate in usable:
        if len(selected_ids) >= capacity:
            break
        if (
            candidate.id not in selected_ids
            and candidate.category in preferred_categories
        ):
            selected_ids.add(candidate.id)
    for candidate in usable:
        if len(selected_ids) >= capacity:
            break
        selected_ids.add(candidate.id)

    selected = tuple(
        candidate
        for candidate in usable
        if candidate.id in selected_ids
    )
    if not selected:
        raise ItineraryExecutionError(
            ItineraryFailureReason.NO_USABLE_CANDIDATES
        )
    return selected


def _available_minutes(request: ItineraryRequest) -> int:
    start = request.start_local_time
    end = request.end_local_time
    if (
        start.second
        or start.microsecond
        or end.second
        or end.microsecond
    ):
        raise ItineraryExecutionError(
            ItineraryFailureReason.UNSATISFIABLE_TIME_WINDOW
        )
    start_datetime = datetime.combine(request.local_date, start)
    end_datetime = datetime.combine(request.local_date, end)
    total_minutes = int(
        (end_datetime - start_datetime).total_seconds() // 60
    )
    if total_minutes <= 0:
        raise ItineraryExecutionError(
            ItineraryFailureReason.UNSATISFIABLE_TIME_WINDOW
        )
    return total_minutes


def _allocate_durations(
    total_minutes: int,
    item_count: int,
) -> tuple[int, ...]:
    if item_count <= 0 or total_minutes < item_count:
        raise ItineraryExecutionError(
            ItineraryFailureReason.UNSATISFIABLE_TIME_WINDOW
        )
    minutes_per_item, remainder = divmod(total_minutes, item_count)
    return tuple(
        minutes_per_item + (1 if index < remainder else 0)
        for index in range(item_count)
    )
