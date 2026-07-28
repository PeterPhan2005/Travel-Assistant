"""Strict evidence-linked Local Culture Agent contracts."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, model_validator

from app.agents.contracts.common import (
    ClaimId,
    ContractModel,
    EvidenceBundle,
    FactKind,
    GuidanceItemId,
    LocaleCode,
    MediumText,
    PlainShortText,
    SourceId,
    SupportedCity,
    validate_references,
    validate_sorted_unique,
)
from app.agents.contracts.narration import AnswerStatus


class LocalCultureRequest(ContractModel):
    """City/topic input with approved cultural or etiquette evidence only."""

    city: SupportedCity
    topic: PlainShortText
    locale: LocaleCode
    evidence: EvidenceBundle

    @model_validator(mode="after")
    def validate_evidence_scope(self) -> LocalCultureRequest:
        """Exclude unrelated or safety-critical claim categories."""
        if any(
            claim.fact_kind not in {FactKind.CULTURE, FactKind.ETIQUETTE}
            for claim in self.evidence.claims
        ):
            raise ValueError(
                "Local-culture evidence must be culture or etiquette."
            )
        return self


class CultureGuidanceItem(ContractModel):
    """One bounded factual guidance item with exact evidence references."""

    guidance_id: GuidanceItemId
    text: PlainShortText
    claim_ids: Annotated[
        tuple[ClaimId, ...],
        Field(min_length=1, max_length=20),
    ]
    source_ids: Annotated[
        tuple[SourceId, ...],
        Field(min_length=1, max_length=20),
    ]

    @model_validator(mode="after")
    def validate_reference_order(self) -> CultureGuidanceItem:
        """Keep claim and source identity order deterministic."""
        validate_sorted_unique(self.claim_ids, label="Guidance claim IDs")
        validate_sorted_unique(self.source_ids, label="Guidance source IDs")
        return self


class LocalCultureOutput(ContractModel):
    """Evidence-linked guidance or an explicit insufficient-evidence result."""

    status: AnswerStatus
    guidance: Annotated[
        tuple[CultureGuidanceItem, ...],
        Field(max_length=12),
    ] = ()
    respectful_caution: PlainShortText | None = None
    limitation_reason: MediumText | None = None

    @model_validator(mode="after")
    def validate_answer_shape(self) -> LocalCultureOutput:
        """Reject duplicate guidance and fabricated limited answers."""
        guidance_ids = tuple(item.guidance_id for item in self.guidance)
        if guidance_ids != tuple(sorted(set(guidance_ids))):
            raise ValueError(
                "Guidance items must be unique and sorted by ID."
            )
        if len({item.text.casefold() for item in self.guidance}) != len(
            self.guidance
        ):
            raise ValueError("Guidance text must not be duplicated.")
        if self.status is AnswerStatus.COMPLETE:
            if not self.guidance:
                raise ValueError("Complete culture output requires guidance.")
            if self.limitation_reason is not None:
                raise ValueError(
                    "Complete culture output cannot have a limitation reason."
                )
        else:
            if self.guidance or self.respectful_caution is not None:
                raise ValueError(
                    "Limited culture output must not fabricate guidance."
                )
            if self.limitation_reason is None:
                raise ValueError(
                    "Limited culture output requires an explicit reason."
                )
        return self

    def validate_against(self, request: LocalCultureRequest) -> Self:
        """Close every guidance item over the exact request evidence."""
        for item in self.guidance:
            validate_references(
                used_claim_ids=item.claim_ids,
                used_source_ids=item.source_ids,
                evidence=request.evidence,
            )
        return self
