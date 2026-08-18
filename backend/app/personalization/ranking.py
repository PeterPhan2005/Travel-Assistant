"""Deterministic soft ranking over already eligible discovery candidates."""

from __future__ import annotations

import re

from app.agents.contracts import DiscoveryCandidate, DiscoveryOutput
from app.preferences.contracts import (
    AgentPreferenceProjectionV1,
    BudgetPreference,
    TravelInterest,
)
from app.providers.poi.models import PriceLevel

_CATEGORY_INTERESTS: dict[TravelInterest, frozenset[str]] = {
    TravelInterest.FOOD_AND_CAFES: frozenset(
        {"bakery", "cafe", "coffee", "food", "restaurant"}
    ),
    TravelInterest.CULTURE_AND_HISTORY: frozenset(
        {
            "art",
            "church",
            "culture",
            "gallery",
            "heritage",
            "historic",
            "history",
            "museum",
            "pagoda",
            "temple",
        }
    ),
    TravelInterest.SCENIC_AND_LANDMARKS: frozenset(
        {"attraction", "landmark", "monument", "scenic", "viewpoint"}
    ),
    TravelInterest.NATURE_AND_OUTDOORS: frozenset(
        {"beach", "garden", "hiking", "nature", "outdoor", "park"}
    ),
    TravelInterest.LOCAL_LIFE_AND_MARKETS: frozenset(
        {"local", "market", "neighborhood", "shopping", "street"}
    ),
    TravelInterest.ENTERTAINMENT_AND_NIGHTLIFE: frozenset(
        {"bar", "cinema", "club", "entertainment", "nightlife", "theater"}
    ),
    TravelInterest.FAMILY_ACTIVITIES: frozenset(
        {"amusement", "aquarium", "family", "playground", "theme", "zoo"}
    ),
    TravelInterest.WELLNESS_AND_RELAXATION: frozenset(
        {"massage", "relaxation", "spa", "wellness", "yoga"}
    ),
}
_COMPATIBLE_PRICE_LEVELS = {
    BudgetPreference.BUDGET: frozenset({PriceLevel.FREE, PriceLevel.INEXPENSIVE}),
    BudgetPreference.MODERATE: frozenset({PriceLevel.INEXPENSIVE, PriceLevel.MODERATE}),
    BudgetPreference.PREMIUM: frozenset(
        {
            PriceLevel.MODERATE,
            PriceLevel.EXPENSIVE,
            PriceLevel.VERY_EXPENSIVE,
        }
    ),
}


def interest_for_category(category: str) -> TravelInterest | None:
    """Map a provider-neutral category to at most one closed interest."""
    tokens = frozenset(
        token
        for token in re.sub(r"[^a-z0-9]+", "_", category.lower()).split("_")
        if token
    )
    for interest in TravelInterest:
        if tokens.intersection(_CATEGORY_INTERESTS[interest]):
            return interest
    return None


def personalize_discovery_output(
    output: DiscoveryOutput,
    projection: AgentPreferenceProjectionV1 | None,
) -> DiscoveryOutput:
    """Soft-rank candidates, preserving input order as the final tie-break."""
    if projection is None or projection.is_empty:
        return output
    selected_interests = frozenset(projection.interests)
    indexed = tuple(enumerate(output.candidates))
    ranked = tuple(
        candidate
        for _, candidate in sorted(
            indexed,
            key=lambda item: (
                _interest_bucket(item[1], selected_interests),
                _budget_bucket(item[1], projection.budget_preference),
                item[0],
            ),
        )
    )
    if ranked == output.candidates:
        return output
    return output.model_copy(update={"candidates": ranked})


def _interest_bucket(
    candidate: DiscoveryCandidate,
    selected: frozenset[TravelInterest],
) -> int:
    if not selected:
        return 0
    return 0 if interest_for_category(candidate.category) in selected else 1


def _budget_bucket(
    candidate: DiscoveryCandidate,
    budget: BudgetPreference | None,
) -> int:
    if budget is None:
        return 0
    if candidate.price_level is None:
        return 1
    return 0 if candidate.price_level in _COMPATIBLE_PRICE_LEVELS[budget] else 2
