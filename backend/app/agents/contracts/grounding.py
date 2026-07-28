"""Strict Grounding Reviewer input/output and discriminated-union contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import AwareDatetime, Field, StrictInt, model_validator

from app.agents.contracts.common import (
    MAX_CLAIMS,
    MAX_REFERENCES,
    MAX_SOURCES,
    AgentKind,
    AgentWarning,
    ClaimId,
    ContractModel,
    CurrencyCode,
    EvidenceBundle,
    EvidenceId,
    FactKind,
    FactualClaim,
    MediumText,
    PoiId,
    PriceFact,
    SourceId,
    SourceRecord,
    SpecialistOutputId,
    validate_issue_stage,
    validate_sorted_unique,
)
from app.agents.contracts.discovery import DiscoveryOutput
from app.agents.contracts.itinerary import ItineraryOutput
from app.agents.contracts.local_culture import LocalCultureOutput
from app.agents.contracts.narration import NarrationOutput


class DiscoverySpecialistOutput(ContractModel):
    """Typed Discovery Agent output at the grounding boundary."""

    agent: Literal[AgentKind.DISCOVERY]
    output_id: SpecialistOutputId
    output: DiscoveryOutput


class NarrationSpecialistOutput(ContractModel):
    """Typed Narration Agent output at the grounding boundary."""

    agent: Literal[AgentKind.NARRATION]
    output_id: SpecialistOutputId
    output: NarrationOutput


class LocalCultureSpecialistOutput(ContractModel):
    """Typed Local Culture Agent output at the grounding boundary."""

    agent: Literal[AgentKind.LOCAL_CULTURE]
    output_id: SpecialistOutputId
    output: LocalCultureOutput


class ItinerarySpecialistOutput(ContractModel):
    """Typed Itinerary Agent output at the grounding boundary."""

    agent: Literal[AgentKind.ITINERARY]
    output_id: SpecialistOutputId
    output: ItineraryOutput


SpecialistOutput: TypeAlias = Annotated[
    DiscoverySpecialistOutput
    | NarrationSpecialistOutput
    | LocalCultureSpecialistOutput
    | ItinerarySpecialistOutput,
    Field(discriminator="agent"),
]


class GroundingCandidatePrice(ContractModel):
    """Untrusted price fields presented to the grounding reviewer."""

    price_minor_units: Annotated[
        StrictInt,
        Field(ge=0, le=9_223_372_036_854_775_807),
    ] | None = None
    currency: CurrencyCode | None = None
    source_updated_at: AwareDatetime | None = None

    @classmethod
    def from_approved(cls, price: PriceFact) -> Self:
        """Copy complete approved price data into the candidate boundary."""
        return cls(
            price_minor_units=price.price_minor_units,
            currency=price.currency,
            source_updated_at=price.source_updated_at,
        )


class GroundingCandidateClaim(ContractModel):
    """A structurally valid claim that may still fail grounding review."""

    claim_id: ClaimId
    evidence_id: EvidenceId
    fact_kind: FactKind
    statement: MediumText
    supporting_source_ids: Annotated[
        tuple[SourceId, ...],
        Field(max_length=MAX_REFERENCES),
    ] = ()
    poi_id: PoiId | None = None
    freshness_at: AwareDatetime | None = None
    price: GroundingCandidatePrice | None = None

    @model_validator(mode="after")
    def validate_source_order(self) -> GroundingCandidateClaim:
        """Keep individual source references deterministic when present."""
        validate_sorted_unique(
            self.supporting_source_ids,
            label="Supporting source IDs",
        )
        return self

    @classmethod
    def from_approved(cls, claim: FactualClaim) -> Self:
        """Copy one validated claim without weakening its source contract."""
        return cls(
            claim_id=claim.claim_id,
            evidence_id=claim.evidence_id,
            fact_kind=claim.fact_kind,
            statement=claim.statement,
            supporting_source_ids=claim.supporting_source_ids,
            poi_id=claim.poi_id,
            freshness_at=claim.freshness_at,
            price=(
                GroundingCandidatePrice.from_approved(claim.price)
                if claim.price is not None
                else None
            ),
        )


class GroundingCandidateEvidence(ContractModel):
    """Untrusted registry whose semantic defects are reviewer decisions."""

    sources: Annotated[
        tuple[SourceRecord, ...],
        Field(max_length=MAX_SOURCES),
    ] = ()
    claims: Annotated[
        tuple[GroundingCandidateClaim, ...],
        Field(max_length=MAX_CLAIMS),
    ] = ()

    @property
    def source_ids(self) -> frozenset[str]:
        """Return candidate source identities without hiding duplicates."""
        return frozenset(source.source_id for source in self.sources)

    @property
    def claim_ids(self) -> frozenset[str]:
        """Return canonical candidate claim identities."""
        return frozenset(claim.claim_id for claim in self.claims)

    @classmethod
    def from_approved(cls, evidence: EvidenceBundle) -> Self:
        """Copy validated evidence into the reviewer candidate boundary."""
        return cls(
            sources=evidence.sources,
            claims=tuple(
                GroundingCandidateClaim.from_approved(claim)
                for claim in evidence.claims
            ),
        )


class FreshnessRequirement(ContractModel):
    """Maximum accepted source age for one freshness-sensitive fact kind."""

    fact_kind: FactKind
    as_of: AwareDatetime
    maximum_age_seconds: Annotated[
        int,
        Field(strict=True, gt=0, le=31_536_000),
    ]


class GroundingReviewRequest(ContractModel):
    """Candidate evidence and typed specialist outputs to review independently."""

    evidence: GroundingCandidateEvidence
    specialist_outputs: Annotated[
        tuple[SpecialistOutput, ...],
        Field(max_length=20),
    ] = ()
    freshness_requirements: Annotated[
        tuple[FreshnessRequirement, ...],
        Field(max_length=len(FactKind)),
    ] = ()

    @model_validator(mode="after")
    def validate_review_input(self) -> GroundingReviewRequest:
        """Validate request-level identities without pre-judging evidence."""
        output_ids = tuple(
            output.output_id for output in self.specialist_outputs
        )
        validate_sorted_unique(output_ids, label="Specialist output IDs")
        requirement_kinds = tuple(
            requirement.fact_kind.value
            for requirement in self.freshness_requirements
        )
        validate_sorted_unique(
            requirement_kinds,
            label="Freshness fact kinds",
        )

        return self


class ClaimRejectionReason(StrEnum):
    """Closed reviewer rejection reasons; no replacement prose is allowed."""

    MISSING_SOURCE = "missing_source"
    MISSING_PRICE_TIMESTAMP = "missing_price_timestamp"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    STALE_EVIDENCE = "stale_evidence"
    INCONSISTENT_EVIDENCE = "inconsistent_evidence"


class RejectedClaim(ContractModel):
    """Claim identity and stable reason only, without rewritten factual text."""

    claim_id: ClaimId
    reason: ClaimRejectionReason


class GroundingReviewStatus(StrEnum):
    """Overall claim-review disposition."""

    APPROVED = "approved"
    PARTIAL = "partial"
    REJECTED = "rejected"


class GroundingReviewOutput(ContractModel):
    """Fail-closed claim decisions that cannot author replacement facts."""

    status: GroundingReviewStatus
    reviewed_claim_ids: Annotated[
        tuple[ClaimId, ...],
        Field(max_length=200),
    ]
    approved_claim_ids: Annotated[
        tuple[ClaimId, ...],
        Field(max_length=200),
    ] = ()
    rejected_claims: Annotated[
        tuple[RejectedClaim, ...],
        Field(max_length=200),
    ] = ()
    approved_specialist_output_ids: Annotated[
        tuple[SpecialistOutputId, ...],
        Field(max_length=20),
    ] = ()
    warnings: Annotated[
        tuple[AgentWarning, ...],
        Field(max_length=20),
    ] = ()

    @model_validator(mode="after")
    def validate_review_decisions(self) -> GroundingReviewOutput:
        """Require disjoint decisions that exactly cover the reviewed set."""
        validate_sorted_unique(
            self.reviewed_claim_ids,
            label="Reviewed claim IDs",
        )
        validate_sorted_unique(
            self.approved_claim_ids,
            label="Approved claim IDs",
        )
        rejected_ids = tuple(
            rejection.claim_id for rejection in self.rejected_claims
        )
        validate_sorted_unique(rejected_ids, label="Rejected claim IDs")
        validate_sorted_unique(
            self.approved_specialist_output_ids,
            label="Approved specialist output IDs",
        )
        if set(self.approved_claim_ids) & set(rejected_ids):
            raise ValueError("Approved and rejected claim IDs must be disjoint.")
        if set(self.reviewed_claim_ids) != (
            set(self.approved_claim_ids) | set(rejected_ids)
        ):
            raise ValueError(
                "Approved and rejected claims must cover reviewed claims."
            )
        if self.status is GroundingReviewStatus.APPROVED:
            if self.rejected_claims:
                raise ValueError("Approved review cannot reject claims.")
        elif self.status is GroundingReviewStatus.PARTIAL:
            if not self.approved_claim_ids or not self.rejected_claims:
                raise ValueError(
                    "Partial review requires approvals and rejections."
                )
        elif self.approved_claim_ids or self.approved_specialist_output_ids:
            raise ValueError(
                "Rejected review cannot approve claims or specialist output."
            )
        for warning in self.warnings:
            validate_issue_stage(warning, AgentKind.GROUNDING_REVIEWER)
        return self

    def validate_against(self, request: GroundingReviewRequest) -> Self:
        """Reject decisions or approvals not present in the review request."""
        if not set(self.reviewed_claim_ids).issubset(
            request.evidence.claim_ids
        ):
            raise ValueError("Reviewer introduced an unknown claim ID.")
        outputs_by_id = {
            output.output_id: output for output in request.specialist_outputs
        }
        if not set(self.approved_specialist_output_ids).issubset(
            outputs_by_id
        ):
            raise ValueError("Reviewer approved an unknown specialist output.")
        approved_claims = set(self.approved_claim_ids)
        for output_id in self.approved_specialist_output_ids:
            referenced = _specialist_claim_ids(outputs_by_id[output_id])
            if not referenced.issubset(approved_claims):
                raise ValueError(
                    "Approved specialist output contains a rejected claim."
                )
        return self


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
