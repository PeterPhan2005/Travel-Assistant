"""Deterministic ranking and least-data projection tests for T096."""

from __future__ import annotations

from app.agents.contracts import (
    AgentKind,
    DiscoveryCandidate,
    DiscoveryCompleteness,
    DiscoveryOutput,
    DiscoverySpecialistOutput,
    EvidenceBundle,
    SupportedCity,
)
from app.personalization.projection import scope_projection_for_composer
from app.personalization.ranking import personalize_discovery_output
from app.preferences.contracts import (
    AgentPreferenceProjectionV1,
    BudgetPreference,
    TravelInterest,
    TravelPace,
)
from app.providers.poi.models import (
    Coordinates,
    PoiProviderKind,
    PriceLevel,
)


def _candidate(
    provider_id: str,
    *,
    category: str,
    price_level: PriceLevel | None,
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        id=f"curated:{provider_id}",
        provider=PoiProviderKind.CURATED,
        provider_id=provider_id,
        canonical_name=provider_id,
        city=SupportedCity.HCMC,
        category=category,
        coordinates=Coordinates(latitude=10.77, longitude=106.69),
        price_level=price_level,
        is_curated=True,
        is_externally_supplied=False,
    )


def _output(
    candidates: tuple[DiscoveryCandidate, ...],
) -> DiscoveryOutput:
    return DiscoveryOutput(
        candidates=candidates,
        evidence=EvidenceBundle(),
        completeness=DiscoveryCompleteness.COMPLETE,
        is_truncated=False,
    )


def test_interest_then_budget_ranking_preserves_base_order_for_ties() -> None:
    museum = _candidate(
        "museum",
        category="museum",
        price_level=PriceLevel.INEXPENSIVE,
    )
    restaurant = _candidate(
        "restaurant",
        category="restaurant",
        price_level=PriceLevel.EXPENSIVE,
    )
    cafe = _candidate("cafe", category="cafe", price_level=None)
    output = _output((museum, restaurant, cafe))
    projection = AgentPreferenceProjectionV1(
        interests=(TravelInterest.FOOD_AND_CAFES,),
        budget_preference=BudgetPreference.BUDGET,
    )

    ranked = personalize_discovery_output(output, projection)

    assert tuple(item.provider_id for item in ranked.candidates) == (
        "cafe",
        "restaurant",
        "museum",
    )
    assert personalize_discovery_output(output, None) is output


def test_budget_bucket_orders_compatible_unknown_then_incompatible() -> None:
    expensive = _candidate(
        "expensive",
        category="restaurant",
        price_level=PriceLevel.EXPENSIVE,
    )
    unknown = _candidate("unknown", category="restaurant", price_level=None)
    free = _candidate(
        "free",
        category="restaurant",
        price_level=PriceLevel.FREE,
    )
    ranked = personalize_discovery_output(
        _output((expensive, unknown, free)),
        AgentPreferenceProjectionV1(
            budget_preference=BudgetPreference.BUDGET
        ),
    )

    assert tuple(item.provider_id for item in ranked.candidates) == (
        "free",
        "unknown",
        "expensive",
    )


def test_composer_projection_contains_only_approved_relevant_values() -> None:
    discovery = DiscoverySpecialistOutput(
        agent=AgentKind.DISCOVERY,
        output_id="approved-discovery",
        output=_output(
            (
                _candidate(
                    "museum",
                    category="museum",
                    price_level=PriceLevel.MODERATE,
                ),
            )
        ),
    )
    scoped = scope_projection_for_composer(
        AgentPreferenceProjectionV1(
            interests=(
                TravelInterest.FOOD_AND_CAFES,
                TravelInterest.CULTURE_AND_HISTORY,
            ),
            pace=TravelPace.ACTIVE,
            budget_preference=BudgetPreference.MODERATE,
        ),
        (discovery,),
    )

    assert scoped == AgentPreferenceProjectionV1(
        interests=(TravelInterest.CULTURE_AND_HISTORY,),
        budget_preference=BudgetPreference.MODERATE,
    )
    assert "uid" not in scoped.model_dump_json()
    assert "updated_at" not in scoped.model_dump_json()
