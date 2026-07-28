"""Pure request closure checks for ItineraryOutput."""

from __future__ import annotations

from app.agents.contracts import (
    FactualClaim,
    ItineraryOutput,
    ItineraryRequest,
)
from app.agents.itinerary.instructions import APPROVED_ASSUMPTIONS


def validate_itinerary_output(
    output: ItineraryOutput,
    request: ItineraryRequest,
) -> ItineraryOutput:
    """Revalidate and close an output over exactly one request."""
    validated = ItineraryOutput.model_validate(
        output.model_dump(mode="python")
    )
    output_poi_ids = tuple(item.poi_id for item in validated.items)
    if len(output_poi_ids) != len(set(output_poi_ids)):
        raise ValueError("Itinerary POI IDs must be unique.")
    validated.validate_against(request)

    if validated.assumptions != APPROVED_ASSUMPTIONS:
        raise ValueError("Itinerary assumptions are not application-approved.")
    if validated.warnings:
        raise ValueError("Itinerary warnings must be empty.")

    expected_item_ids = tuple(
        f"itinerary-item-{index:03d}"
        for index in range(1, len(validated.items) + 1)
    )
    actual_item_ids = tuple(item.item_id for item in validated.items)
    if actual_item_ids != expected_item_ids:
        raise ValueError("Itinerary item IDs must be canonical and sequential.")

    candidates_by_id = {
        candidate.id: candidate
        for candidate in request.candidates
    }
    expected_order = tuple(
        candidate.id
        for candidate in request.candidates
        if candidate.id in set(output_poi_ids)
    )
    if output_poi_ids != expected_order:
        raise ValueError("Itinerary must preserve candidate input order.")

    claims_by_id = {
        claim.claim_id: claim
        for claim in request.evidence.claims
    }
    for item in validated.items:
        candidate = candidates_by_id.get(item.poi_id)
        if candidate is None:
            raise ValueError("Itinerary references an unknown candidate POI.")
        if item.title != candidate.canonical_name:
            raise ValueError("Itinerary title differs from candidate identity.")
        if item.start_local_time.second or item.start_local_time.microsecond:
            raise ValueError("Itinerary item boundaries must use whole minutes.")
        if item.end_local_time.second or item.end_local_time.microsecond:
            raise ValueError("Itinerary item boundaries must use whole minutes.")
        _validate_item_evidence(
            item.poi_id,
            item.supporting_claim_ids,
            item.supporting_source_ids,
            claims_by_id,
        )
    return validated


def _validate_item_evidence(
    poi_id: str,
    claim_ids: tuple[str, ...],
    source_ids: tuple[str, ...],
    claims_by_id: dict[str, FactualClaim],
) -> None:
    if not claim_ids:
        if source_ids:
            raise ValueError("Evidence-free item must not reference sources.")
        return

    claims = []
    for claim_id in claim_ids:
        claim = claims_by_id.get(claim_id)
        if claim is None:
            raise ValueError("Itinerary item references an unknown claim.")
        claims.append(claim)
    if any(claim.poi_id != poi_id for claim in claims):
        raise ValueError("Itinerary item claim is scoped to another POI.")

    expected_sources = tuple(
        sorted(
            {
                source_id
                for claim in claims
                for source_id in claim.supporting_source_ids
            }
        )
    )
    if source_ids != expected_sources:
        raise ValueError(
            "Itinerary item sources must equal the claims' source union."
        )
