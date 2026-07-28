"""Strict approved-evidence Response Composer contracts."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Self

from pydantic import Field, StrictFloat, StrictInt, model_validator

from app.agents.contracts.common import (
    AgentKind,
    AgentWarning,
    ClaimId,
    ContractModel,
    EvidenceBundle,
    LocaleCode,
    NormalizedQuery,
    PlainOutputText,
    PlainShortText,
    PoiId,
    PriceFact,
    ShortText,
    SourceId,
    validate_references,
    validate_sorted_unique,
)
from app.agents.contracts.grounding import (
    SpecialistOutput,
    _specialist_claim_ids,
)


class ResponseComposerRequest(ContractModel):
    """Only approved claims, content, locale, and safe partial warnings."""

    user_query: NormalizedQuery
    locale: LocaleCode
    evidence: EvidenceBundle
    approved_claim_ids: Annotated[
        tuple[ClaimId, ...],
        Field(max_length=200),
    ]
    approved_specialist_outputs: Annotated[
        tuple[SpecialistOutput, ...],
        Field(max_length=20),
    ] = ()
    warnings: Annotated[
        tuple[AgentWarning, ...],
        Field(max_length=20),
    ] = ()

    @model_validator(mode="after")
    def validate_approved_input(self) -> ResponseComposerRequest:
        """Reject unknown claims or specialist content using unapproved facts."""
        validate_sorted_unique(
            self.approved_claim_ids,
            label="Composer approved claim IDs",
        )
        if not set(self.approved_claim_ids).issubset(
            self.evidence.claim_ids
        ):
            raise ValueError("Composer received an unknown approved claim.")
        output_ids = tuple(
            output.output_id for output in self.approved_specialist_outputs
        )
        validate_sorted_unique(
            output_ids,
            label="Approved specialist output IDs",
        )
        approved = set(self.approved_claim_ids)
        for output in self.approved_specialist_outputs:
            if not _specialist_claim_ids(output).issubset(approved):
                raise ValueError(
                    "Composer specialist content uses an unapproved claim."
                )
        return self


class PoiPresentationItem(ContractModel):
    """Coordinate-free normalized POI presentation with optional facts omitted."""

    poi_id: PoiId
    canonical_name: ShortText
    category: ShortText
    address: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=500),
    ] | None = None
    distance_metres: Annotated[
        StrictFloat,
        Field(ge=0, allow_inf_nan=False),
    ] | None = None
    rating: Annotated[Decimal, Field(ge=0, le=5)] | None = None
    rating_count: Annotated[StrictInt, Field(ge=0)] | None = None
    price: PriceFact | None = None
    opening_hours_summary: PlainShortText | None = None


class ResponseComposerOutput(ContractModel):
    """Plain Vietnamese-facing response using approved claim/source IDs only."""

    final_text: PlainOutputText
    poi_items: Annotated[
        tuple[PoiPresentationItem, ...],
        Field(max_length=20),
    ] = ()
    warnings: Annotated[
        tuple[AgentWarning, ...],
        Field(max_length=20),
    ] = ()
    used_claim_ids: Annotated[
        tuple[ClaimId, ...],
        Field(max_length=200),
    ] = ()
    used_source_ids: Annotated[
        tuple[SourceId, ...],
        Field(max_length=100),
    ] = ()

    @model_validator(mode="after")
    def validate_output_shape(self) -> ResponseComposerOutput:
        """Reject duplicate POIs and internal runtime terminology."""
        poi_ids = tuple(item.poi_id for item in self.poi_items)
        validate_sorted_unique(poi_ids, label="Presented POI IDs")
        lowered = self.final_text.casefold()
        internal_terms = {
            AgentKind.ROUTER.value,
            AgentKind.DISCOVERY.value,
            AgentKind.NARRATION.value,
            AgentKind.LOCAL_CULTURE.value,
            AgentKind.ITINERARY.value,
            AgentKind.GROUNDING_REVIEWER.value,
            AgentKind.RESPONSE_COMPOSER.value,
            "prompt",
            "exception",
        }
        if any(term in lowered for term in internal_terms):
            raise ValueError("Final text exposes internal runtime details.")
        if bool(self.used_claim_ids) is not bool(self.used_source_ids):
            raise ValueError(
                "Composer claim/source references must be paired."
            )
        return self

    def validate_against(self, request: ResponseComposerRequest) -> Self:
        """Close final references and require exact warning preservation."""
        if self.warnings != request.warnings:
            raise ValueError("Composer must preserve all input warnings.")
        if not set(self.used_claim_ids).issubset(
            set(request.approved_claim_ids)
        ):
            raise ValueError("Composer introduced an unapproved claim.")
        if self.used_claim_ids:
            validate_references(
                used_claim_ids=self.used_claim_ids,
                used_source_ids=self.used_source_ids,
                evidence=request.evidence,
            )
        return self
