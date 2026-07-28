"""Strict source-grounded Narration Agent contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from app.agents.contracts.common import (
    ClaimId,
    ContractModel,
    EvidenceBundle,
    LocaleCode,
    MediumText,
    PlainOutputText,
    PlainShortText,
    PoiIdentity,
    SourceId,
    validate_references,
)

MIN_NARRATION_WORDS = 100
MAX_NARRATION_WORDS = 200


class AnswerStatus(StrEnum):
    """Whether a specialist answer is usable or evidence-limited."""

    COMPLETE = "complete"
    LIMITED = "limited"


class NarrationWordRange(ContractModel):
    """Accepted inclusive narration range inside the product 100–200 words."""

    minimum_words: Annotated[
        int,
        Field(strict=True, ge=MIN_NARRATION_WORDS, le=MAX_NARRATION_WORDS),
    ]
    maximum_words: Annotated[
        int,
        Field(strict=True, ge=MIN_NARRATION_WORDS, le=MAX_NARRATION_WORDS),
    ]

    @model_validator(mode="after")
    def validate_order(self) -> NarrationWordRange:
        """Require a nonempty inclusive range."""
        if self.minimum_words > self.maximum_words:
            raise ValueError("Minimum words must not exceed maximum words.")
        return self


class NarrationRequest(ContractModel):
    """One-POI narration input containing only approved evidence and locale."""

    poi: PoiIdentity
    evidence: EvidenceBundle
    locale: LocaleCode
    word_range: NarrationWordRange

    @model_validator(mode="after")
    def validate_poi_claims(self) -> NarrationRequest:
        """Prevent evidence for a different POI from entering narration."""
        for claim in self.evidence.claims:
            if claim.poi_id is not None and claim.poi_id != self.poi.poi_id:
                raise ValueError("Narration evidence belongs to another POI.")
        return self


class NarrationOutput(ContractModel):
    """Plain narration plus exact claim/source references, or a limited result."""

    status: AnswerStatus
    narration_text: PlainOutputText | None = None
    key_points: Annotated[
        tuple[PlainShortText, ...],
        Field(max_length=10),
    ] = ()
    used_source_ids: Annotated[
        tuple[SourceId, ...],
        Field(max_length=100),
    ] = ()
    used_claim_ids: Annotated[
        tuple[ClaimId, ...],
        Field(max_length=200),
    ] = ()
    limitation_reason: MediumText | None = None

    @model_validator(mode="after")
    def validate_answer_shape(self) -> NarrationOutput:
        """Enforce word boundaries and explicit fail-closed limited output."""
        if len(self.key_points) != len(set(self.key_points)):
            raise ValueError("Narration key points must not be duplicated.")
        if self.status is AnswerStatus.COMPLETE:
            if self.narration_text is None:
                raise ValueError("Complete narration requires text.")
            word_count = len(self.narration_text.split())
            if not MIN_NARRATION_WORDS <= word_count <= MAX_NARRATION_WORDS:
                raise ValueError("Narration must contain 100 to 200 words.")
            if not self.key_points:
                raise ValueError("Complete narration requires key points.")
            if not self.used_claim_ids or not self.used_source_ids:
                raise ValueError("Complete narration requires evidence.")
            if self.limitation_reason is not None:
                raise ValueError(
                    "Complete narration cannot have a limitation reason."
                )
        else:
            if self.narration_text is not None or self.key_points:
                raise ValueError(
                    "Limited narration must not fabricate narrative content."
                )
            if self.used_claim_ids or self.used_source_ids:
                raise ValueError(
                    "Limited narration must not claim unsupported evidence."
                )
            if self.limitation_reason is None:
                raise ValueError(
                    "Limited narration requires an explicit safe reason."
                )
        return self

    def validate_against(self, request: NarrationRequest) -> Self:
        """Close output references and word range over the exact request."""
        if self.status is AnswerStatus.COMPLETE:
            validate_references(
                used_claim_ids=self.used_claim_ids,
                used_source_ids=self.used_source_ids,
                evidence=request.evidence,
            )
            if self.narration_text is None:
                raise ValueError("Complete narration requires text.")
            word_count = len(self.narration_text.split())
            if not (
                request.word_range.minimum_words
                <= word_count
                <= request.word_range.maximum_words
            ):
                raise ValueError(
                    "Narration is outside the requested word range."
                )
        return self
