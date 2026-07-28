"""Strict Grounding Reviewer input/output and discriminated-union contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import AwareDatetime, Field, model_validator

from app.agents.contracts.common import (
    AgentKind,
    AgentWarning,
    ClaimId,
    ContractModel,
    EvidenceBundle,
    FactKind,
    SpecialistOutputId,
    validate_issue_stage,
    validate_references,
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

    evidence: EvidenceBundle
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
        """Close every specialist reference over the candidate registry."""
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

        source_by_id = {
            source.source_id: source for source in self.evidence.sources
        }
        claim_by_id = {
            claim.claim_id: claim for claim in self.evidence.claims
        }
        for specialist in self.specialist_outputs:
            if isinstance(specialist, DiscoverySpecialistOutput):
                for source in specialist.output.evidence.sources:
                    if source_by_id.get(source.source_id) != source:
                        raise ValueError(
                            "Discovery source differs from review registry."
                        )
                for claim in specialist.output.evidence.claims:
                    if claim_by_id.get(claim.claim_id) != claim:
                        raise ValueError(
                            "Discovery claim differs from review registry."
                        )
            elif isinstance(specialist, NarrationSpecialistOutput):
                validate_references(
                    used_claim_ids=specialist.output.used_claim_ids,
                    used_source_ids=specialist.output.used_source_ids,
                    evidence=self.evidence,
                )
            elif isinstance(specialist, LocalCultureSpecialistOutput):
                for guidance_item in specialist.output.guidance:
                    validate_references(
                        used_claim_ids=guidance_item.claim_ids,
                        used_source_ids=guidance_item.source_ids,
                        evidence=self.evidence,
                    )
            else:
                for itinerary_item in specialist.output.items:
                    if itinerary_item.supporting_claim_ids:
                        validate_references(
                            used_claim_ids=(
                                itinerary_item.supporting_claim_ids
                            ),
                            used_source_ids=(
                                itinerary_item.supporting_source_ids
                            ),
                            evidence=self.evidence,
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
