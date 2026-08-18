"""Least-data scoping for the approved Response Composer boundary."""

from __future__ import annotations

from app.agents.contracts import (
    DiscoverySpecialistOutput,
    ItinerarySpecialistOutput,
    SpecialistOutput,
)
from app.preferences.contracts import AgentPreferenceProjectionV1

from .ranking import interest_for_category


def scope_projection_for_composer(
    projection: AgentPreferenceProjectionV1 | None,
    approved_outputs: tuple[SpecialistOutput, ...],
) -> AgentPreferenceProjectionV1 | None:
    """Keep only values relevant to approved specialist output content."""
    if projection is None:
        return None
    discovery_outputs = tuple(
        item for item in approved_outputs if isinstance(item, DiscoverySpecialistOutput)
    )
    available_interests = {
        interest_for_category(candidate.category)
        for item in discovery_outputs
        for candidate in item.output.candidates
    }
    interests = tuple(
        interest for interest in projection.interests if interest in available_interests
    )
    has_known_price = any(
        candidate.price_level is not None
        for item in discovery_outputs
        for candidate in item.output.candidates
    )
    has_itinerary = any(
        isinstance(item, ItinerarySpecialistOutput) for item in approved_outputs
    )
    scoped = AgentPreferenceProjectionV1(
        interests=interests,
        pace=projection.pace if has_itinerary else None,
        budget_preference=(projection.budget_preference if has_known_price else None),
    )
    return None if scoped.is_empty else scoped
