"""Pure evidence merge, scoping, and approval conversion helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from app.agents.contracts import (
    EvidenceBundle,
    FactKind,
    FactualClaim,
    GroundingCandidateClaim,
    GroundingCandidateEvidence,
    GroundingReviewOutput,
    PriceFact,
    SourceRecord,
)


def merge_strict_evidence(
    bundles: Iterable[EvidenceBundle],
) -> EvidenceBundle:
    """Merge exact duplicates and reject conflicting strict identities."""
    sources: dict[str, SourceRecord] = {}
    claims: dict[str, FactualClaim] = {}
    for bundle in bundles:
        for source in bundle.sources:
            existing_source = sources.setdefault(source.source_id, source)
            if existing_source != source:
                raise ValueError("Conflicting source identity.")
        for claim in bundle.claims:
            existing_claim = claims.setdefault(claim.claim_id, claim)
            if existing_claim != claim:
                raise ValueError("Conflicting claim identity.")
    return EvidenceBundle(
        sources=tuple(sources[key] for key in sorted(sources)),
        claims=tuple(claims[key] for key in sorted(claims)),
    )


def merge_candidate_evidence(
    bundles: Iterable[EvidenceBundle],
) -> GroundingCandidateEvidence:
    """Preserve conflicting identities while collapsing exact duplicates."""
    sources: list[SourceRecord] = []
    claims: list[GroundingCandidateClaim] = []
    for bundle in bundles:
        for source in bundle.sources:
            if source not in sources:
                sources.append(source)
        for claim in bundle.claims:
            candidate = GroundingCandidateClaim.from_approved(claim)
            if candidate not in claims:
                claims.append(candidate)
    return GroundingCandidateEvidence(
        sources=tuple(sources),
        claims=tuple(claims),
    )


def filter_evidence(
    evidence: EvidenceBundle,
    predicate: Callable[[FactualClaim], bool],
) -> EvidenceBundle:
    """Return a source-closed subset without changing claim or source values."""
    claims = tuple(claim for claim in evidence.claims if predicate(claim))
    source_ids = {
        source_id
        for claim in claims
        for source_id in claim.supporting_source_ids
    }
    return EvidenceBundle(
        sources=tuple(
            source
            for source in evidence.sources
            if source.source_id in source_ids
        ),
        claims=claims,
    )


def filter_poi_evidence(
    evidence: EvidenceBundle,
    poi_id: str,
) -> EvidenceBundle:
    """Scope strict evidence to claims explicitly attached to one POI."""
    return filter_evidence(
        evidence,
        lambda claim: claim.poi_id == poi_id,
    )


def filter_culture_evidence(
    evidence: EvidenceBundle,
) -> EvidenceBundle:
    """Scope strict evidence to culture and etiquette claim kinds only."""
    accepted = {FactKind.CULTURE, FactKind.ETIQUETTE}
    return filter_evidence(
        evidence,
        lambda claim: claim.fact_kind in accepted,
    )


def build_approved_evidence(
    candidates: GroundingCandidateEvidence,
    review: GroundingReviewOutput,
) -> EvidenceBundle:
    """Build strict evidence from unambiguous reviewer-approved values only."""
    claims: list[FactualClaim] = []
    sources: dict[str, SourceRecord] = {}
    for claim_id in review.approved_claim_ids:
        matches = tuple(
            claim
            for claim in candidates.claims
            if claim.claim_id == claim_id
        )
        if len(matches) != 1:
            raise ValueError("Approved claim identity is ambiguous.")
        candidate = matches[0]
        price = _approved_price(candidate)
        claim = FactualClaim(
            claim_id=candidate.claim_id,
            evidence_id=candidate.evidence_id,
            fact_kind=candidate.fact_kind,
            statement=candidate.statement,
            supporting_source_ids=candidate.supporting_source_ids,
            poi_id=candidate.poi_id,
            freshness_at=candidate.freshness_at,
            price=price,
        )
        for source_id in claim.supporting_source_ids:
            source_matches = tuple(
                source
                for source in candidates.sources
                if source.source_id == source_id
            )
            if len(source_matches) != 1:
                raise ValueError("Approved source identity is ambiguous.")
            sources[source_id] = source_matches[0]
        claims.append(claim)
    return EvidenceBundle(
        sources=tuple(sources[key] for key in sorted(sources)),
        claims=tuple(sorted(claims, key=lambda claim: claim.claim_id)),
    )


def _approved_price(
    claim: GroundingCandidateClaim,
) -> PriceFact | None:
    if claim.fact_kind is not FactKind.PRICE:
        if claim.price is not None:
            raise ValueError("Non-price approved claim contains price data.")
        return None
    price = claim.price
    if (
        price is None
        or price.price_minor_units is None
        or price.currency is None
        or price.source_updated_at is None
    ):
        raise ValueError("Approved price claim is incomplete.")
    return PriceFact(
        price_minor_units=price.price_minor_units,
        currency=price.currency,
        source_updated_at=price.source_updated_at,
    )
