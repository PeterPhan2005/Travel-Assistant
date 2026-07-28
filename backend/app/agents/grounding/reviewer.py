"""Pure deterministic closed-world grounding review."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timedelta

from app.agents.contracts import (
    AnswerStatus,
    ClaimRejectionReason,
    DiscoverySpecialistOutput,
    FactKind,
    FreshnessRequirement,
    GroundingCandidateClaim,
    GroundingReviewOutput,
    GroundingReviewRequest,
    GroundingReviewStatus,
    ItinerarySpecialistOutput,
    LocalCultureSpecialistOutput,
    NarrationSpecialistOutput,
    RejectedClaim,
    SourceRecord,
    SpecialistOutput,
)
from app.providers.poi.models import SourceReference

_REASON_ORDER = (
    ClaimRejectionReason.MISSING_SOURCE,
    ClaimRejectionReason.MISSING_PRICE_TIMESTAMP,
    ClaimRejectionReason.INCONSISTENT_EVIDENCE,
    ClaimRejectionReason.UNSUPPORTED_CLAIM,
    ClaimRejectionReason.STALE_EVIDENCE,
)


def build_deterministic_review(
    request: GroundingReviewRequest,
) -> GroundingReviewOutput:
    """Review exactly one request without model knowledge or current time."""
    source_by_id, conflicting_source_ids = _source_registry(request)
    claim_by_id, claim_reasons = _claim_registry(request)
    specialist_reasons, structurally_valid_outputs = _specialist_issues(
        request,
        source_by_id,
        claim_by_id,
    )
    for claim_id, reasons in specialist_reasons.items():
        claim_reasons[claim_id].update(reasons)

    requirement_by_kind = {
        requirement.fact_kind: requirement
        for requirement in request.freshness_requirements
    }
    for claim_id, claim in claim_by_id.items():
        claim_reasons[claim_id].update(
            _claim_issues(
                claim,
                source_by_id,
                conflicting_source_ids,
                requirement_by_kind,
            )
        )

    reviewed_claim_ids = tuple(sorted(claim_by_id))
    rejected_claims = tuple(
        RejectedClaim(
            claim_id=claim_id,
            reason=min(
                claim_reasons[claim_id],
                key=_REASON_ORDER.index,
            ),
        )
        for claim_id in reviewed_claim_ids
        if claim_reasons[claim_id]
    )
    rejected_ids = {
        rejection.claim_id for rejection in rejected_claims
    }
    approved_claim_ids = tuple(
        claim_id
        for claim_id in reviewed_claim_ids
        if claim_id not in rejected_ids
    )
    approved_claim_set = set(approved_claim_ids)

    approved_output_ids = tuple(
        output.output_id
        for output in request.specialist_outputs
        if output.output_id in structurally_valid_outputs
        and _specialist_claim_ids(output).issubset(approved_claim_set)
    )

    if rejected_claims and not approved_claim_ids:
        status = GroundingReviewStatus.REJECTED
        approved_output_ids = ()
    elif rejected_claims:
        status = GroundingReviewStatus.PARTIAL
    else:
        status = GroundingReviewStatus.APPROVED

    return GroundingReviewOutput(
        status=status,
        reviewed_claim_ids=reviewed_claim_ids,
        approved_claim_ids=approved_claim_ids,
        rejected_claims=rejected_claims,
        approved_specialist_output_ids=approved_output_ids,
        warnings=(),
    )


def _source_registry(
    request: GroundingReviewRequest,
) -> tuple[dict[str, SourceRecord], set[str]]:
    sources: dict[str, SourceRecord] = {}
    conflicting: set[str] = set()
    for source in request.evidence.sources:
        existing = sources.setdefault(source.source_id, source)
        if existing != source:
            conflicting.add(source.source_id)
    return sources, conflicting


def _claim_registry(
    request: GroundingReviewRequest,
) -> tuple[
    dict[str, GroundingCandidateClaim],
    defaultdict[str, set[ClaimRejectionReason]],
]:
    claims: dict[str, GroundingCandidateClaim] = {}
    evidence_ids: dict[str, str] = {}
    reasons: defaultdict[str, set[ClaimRejectionReason]] = defaultdict(set)
    for claim in request.evidence.claims:
        if claim.claim_id in claims:
            reasons[claim.claim_id].add(
                ClaimRejectionReason.INCONSISTENT_EVIDENCE
            )
        else:
            claims[claim.claim_id] = claim
        previous_claim_id = evidence_ids.setdefault(
            claim.evidence_id,
            claim.claim_id,
        )
        if previous_claim_id != claim.claim_id:
            reasons[claim.claim_id].add(
                ClaimRejectionReason.INCONSISTENT_EVIDENCE
            )
            reasons[previous_claim_id].add(
                ClaimRejectionReason.INCONSISTENT_EVIDENCE
            )
    return claims, reasons


def _claim_issues(
    claim: GroundingCandidateClaim,
    source_by_id: dict[str, SourceRecord],
    conflicting_source_ids: set[str],
    requirement_by_kind: Mapping[FactKind, FreshnessRequirement],
) -> set[ClaimRejectionReason]:
    reasons: set[ClaimRejectionReason] = set()
    source_ids = tuple(claim.supporting_source_ids)
    if not source_ids or any(
        source_id not in source_by_id for source_id in source_ids
    ):
        reasons.add(ClaimRejectionReason.MISSING_SOURCE)
    if any(source_id in conflicting_source_ids for source_id in source_ids):
        reasons.add(ClaimRejectionReason.INCONSISTENT_EVIDENCE)

    if claim.fact_kind is FactKind.PRICE:
        price = claim.price
        price_timestamp = price.source_updated_at if price is not None else None
        if (
            price is None
            or price.price_minor_units is None
            or price.currency is None
            or claim.freshness_at is None
            or price_timestamp is None
        ):
            reasons.add(ClaimRejectionReason.MISSING_PRICE_TIMESTAMP)
        if (
            claim.freshness_at is not None
            and price_timestamp is not None
            and claim.freshness_at != price_timestamp
        ):
            reasons.add(ClaimRejectionReason.INCONSISTENT_EVIDENCE)
    elif claim.price is not None:
        reasons.add(ClaimRejectionReason.INCONSISTENT_EVIDENCE)

    requirement = requirement_by_kind.get(claim.fact_kind)
    if requirement is not None:
        as_of = requirement.as_of
        maximum_age_seconds = requirement.maximum_age_seconds
        timestamps = _freshness_timestamps(claim, source_by_id)
        if not timestamps:
            reasons.add(ClaimRejectionReason.UNSUPPORTED_CLAIM)
        elif any(
            not _is_aware(timestamp) or timestamp > as_of
            for timestamp in timestamps
        ):
            reasons.add(ClaimRejectionReason.INCONSISTENT_EVIDENCE)
        elif any(
            as_of - timestamp > timedelta(seconds=maximum_age_seconds)
            for timestamp in timestamps
        ):
            reasons.add(ClaimRejectionReason.STALE_EVIDENCE)
    return reasons


def _freshness_timestamps(
    claim: GroundingCandidateClaim,
    source_by_id: dict[str, SourceRecord],
) -> tuple[datetime, ...]:
    timestamps: list[datetime] = []
    if claim.freshness_at is not None:
        timestamps.append(claim.freshness_at)
    for source_id in claim.supporting_source_ids:
        source = source_by_id.get(source_id)
        if source is None:
            continue
        timestamp = source.retrieved_at or source.published_at
        if timestamp is not None:
            timestamps.append(timestamp)
    return tuple(timestamps)


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _specialist_issues(
    request: GroundingReviewRequest,
    source_by_id: dict[str, SourceRecord],
    claim_by_id: dict[str, GroundingCandidateClaim],
) -> tuple[
    defaultdict[str, set[ClaimRejectionReason]],
    set[str],
]:
    reasons: defaultdict[str, set[ClaimRejectionReason]] = defaultdict(set)
    valid_output_ids: set[str] = set()
    seen_output_ids: set[str] = set()
    for specialist in request.specialist_outputs:
        if specialist.output_id in seen_output_ids:
            continue
        seen_output_ids.add(specialist.output_id)
        if _specialist_is_closed(
            specialist,
            source_by_id,
            claim_by_id,
            reasons,
        ):
            valid_output_ids.add(specialist.output_id)
    return reasons, valid_output_ids


def _specialist_is_closed(
    specialist: SpecialistOutput,
    source_by_id: dict[str, SourceRecord],
    claim_by_id: dict[str, GroundingCandidateClaim],
    reasons: defaultdict[str, set[ClaimRejectionReason]],
) -> bool:
    if isinstance(specialist, DiscoverySpecialistOutput):
        return _discovery_is_closed(
            specialist,
            source_by_id,
            claim_by_id,
            reasons,
        )
    if isinstance(specialist, NarrationSpecialistOutput):
        return _narration_is_closed(specialist, claim_by_id, reasons)
    if isinstance(specialist, LocalCultureSpecialistOutput):
        return _culture_is_closed(specialist, claim_by_id, reasons)
    return _itinerary_is_closed(specialist, claim_by_id, reasons)


def _discovery_is_closed(
    specialist: DiscoverySpecialistOutput,
    source_by_id: dict[str, SourceRecord],
    claim_by_id: dict[str, GroundingCandidateClaim],
    reasons: defaultdict[str, set[ClaimRejectionReason]],
) -> bool:
    output = specialist.output
    candidate_ids = {candidate.id for candidate in output.candidates}
    claims_by_poi_id = {
        claim.poi_id
        for claim in output.evidence.claims
        if claim.poi_id is not None
    }
    valid = True
    for evidence_source in output.evidence.sources:
        if source_by_id.get(evidence_source.source_id) != evidence_source:
            valid = False
    for claim in output.evidence.claims:
        candidate_claim = claim_by_id.get(claim.claim_id)
        if (
            candidate_claim is None
            or candidate_claim
            != GroundingCandidateClaim.from_approved(claim)
        ):
            if claim.claim_id in claim_by_id:
                reasons[claim.claim_id].add(
                    ClaimRejectionReason.INCONSISTENT_EVIDENCE
                )
            valid = False
        if claim.poi_id is not None and claim.poi_id not in candidate_ids:
            if claim.claim_id in claim_by_id:
                reasons[claim.claim_id].add(
                    ClaimRejectionReason.UNSUPPORTED_CLAIM
                )
            valid = False
    for candidate in output.candidates:
        if candidate.id not in claims_by_poi_id:
            valid = False
        if not candidate.sources:
            valid = False
        for candidate_source in candidate.sources:
            registry_source = source_by_id.get(candidate_source.source_id)
            if (
                registry_source is None
                or not _candidate_source_matches(
                    candidate_source,
                    registry_source,
                )
            ):
                for claim in output.evidence.claims:
                    if claim.poi_id == candidate.id:
                        reasons[claim.claim_id].add(
                            ClaimRejectionReason.INCONSISTENT_EVIDENCE
                        )
                valid = False
    return valid


def _candidate_source_matches(
    source: SourceReference,
    record: SourceRecord,
) -> bool:
    return (
        source.source_type == record.source_type.value
        and source.label == record.label
        and source.publisher == record.publisher
        and source.url == record.url
        and source.published_at == record.published_at
        and source.retrieved_at == record.retrieved_at
    )


def _narration_is_closed(
    specialist: NarrationSpecialistOutput,
    claim_by_id: dict[str, GroundingCandidateClaim],
    reasons: defaultdict[str, set[ClaimRejectionReason]],
) -> bool:
    output = specialist.output
    if output.status is AnswerStatus.LIMITED:
        return (
            output.narration_text is None
            and not output.key_points
            and not output.used_claim_ids
            and not output.used_source_ids
        )
    return _references_are_closed(
        output.used_claim_ids,
        output.used_source_ids,
        claim_by_id,
        reasons,
    )


def _culture_is_closed(
    specialist: LocalCultureSpecialistOutput,
    claim_by_id: dict[str, GroundingCandidateClaim],
    reasons: defaultdict[str, set[ClaimRejectionReason]],
) -> bool:
    output = specialist.output
    if output.status is AnswerStatus.LIMITED:
        return not output.guidance and output.respectful_caution is None
    valid = True
    for item in output.guidance:
        if not _references_are_closed(
            item.claim_ids,
            item.source_ids,
            claim_by_id,
            reasons,
        ):
            valid = False
    return valid


def _itinerary_is_closed(
    specialist: ItinerarySpecialistOutput,
    claim_by_id: dict[str, GroundingCandidateClaim],
    reasons: defaultdict[str, set[ClaimRejectionReason]],
) -> bool:
    valid = True
    for item in specialist.output.items:
        if not item.supporting_claim_ids:
            if item.supporting_source_ids:
                valid = False
            continue
        claims = [
            claim_by_id.get(claim_id)
            for claim_id in item.supporting_claim_ids
        ]
        for claim_id, claim in zip(
            item.supporting_claim_ids,
            claims,
            strict=True,
        ):
            if claim is not None and claim.poi_id != item.poi_id:
                reasons[claim_id].add(
                    ClaimRejectionReason.UNSUPPORTED_CLAIM
                )
                valid = False
        if not _references_are_closed(
            item.supporting_claim_ids,
            item.supporting_source_ids,
            claim_by_id,
            reasons,
        ):
            valid = False
    return valid


def _references_are_closed(
    claim_ids: tuple[str, ...],
    source_ids: tuple[str, ...],
    claim_by_id: dict[str, GroundingCandidateClaim],
    reasons: defaultdict[str, set[ClaimRejectionReason]],
) -> bool:
    if not claim_ids:
        return False
    claims = [claim_by_id.get(claim_id) for claim_id in claim_ids]
    if any(claim is None for claim in claims):
        for claim_id, claim in zip(claim_ids, claims, strict=True):
            if claim is not None:
                reasons[claim_id].add(
                    ClaimRejectionReason.UNSUPPORTED_CLAIM
                )
        return False
    expected_source_ids = tuple(
        sorted(
            {
                source_id
                for claim in claims
                if claim is not None
                for source_id in claim.supporting_source_ids
            }
        )
    )
    if source_ids != expected_source_ids:
        for claim_id in claim_ids:
            if claim_id in claim_by_id:
                reasons[claim_id].add(
                    ClaimRejectionReason.INCONSISTENT_EVIDENCE
                )
        return False
    return True


def _specialist_claim_ids(output: SpecialistOutput) -> set[str]:
    if isinstance(output, DiscoverySpecialistOutput):
        return set(output.output.evidence.claim_ids)
    if isinstance(output, NarrationSpecialistOutput):
        return set(output.output.used_claim_ids)
    if isinstance(output, LocalCultureSpecialistOutput):
        return {
            claim_id
            for item in output.output.guidance
            for claim_id in item.claim_ids
        }
    return {
        claim_id
        for item in output.output.items
        for claim_id in item.supporting_claim_ids
    }
