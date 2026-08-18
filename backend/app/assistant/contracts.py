"""Strict transport-specific assistant request and response contracts."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictFloat,
    StrictInt,
    model_validator,
)

from app.agents.contracts import (
    AgentFailure,
    AgentRuntimeContext,
    AgentRuntimeRequest,
    AgentRuntimeResult,
    AgentWarning,
    AnswerStatus,
    DiscoveryOrigin,
    DiscoveryStageOutcome,
    GroundingStageOutcome,
    IntentKind,
    ItineraryStageOutcome,
    LocaleCode,
    NarrationStageOutcome,
    RouterStageOutcome,
)
from app.agents.contracts.common import NormalizedQuery
from app.preferences.contracts import AgentPreferenceProjectionV1

_FAILED_MESSAGE = "Chưa thể tạo câu trả lời an toàn cho yêu cầu này."
_NARRATION_OUTPUT_ID = "runtime-narration"
_ITINERARY_OUTPUT_ID = "runtime-itinerary"


class AssistantTransportModel(BaseModel):
    """Immutable strict-by-shape assistant HTTP model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        validate_default=True,
        revalidate_instances="always",
    )


class AssistantQueryRequest(AssistantTransportModel):
    """Confirmed text plus explicitly available request-scoped context."""

    text: NormalizedQuery
    locale: LocaleCode
    latitude: Annotated[
        StrictFloat,
        Field(ge=-90, le=90, allow_inf_nan=False),
    ] | None = None
    longitude: Annotated[
        StrictFloat,
        Field(ge=-180, le=180, allow_inf_nan=False),
    ] | None = None
    trip_id: Literal[None] = None
    client_mode: Literal["online"]

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> AssistantQueryRequest:
        """Require both WGS84 coordinates or neither coordinate."""
        if (self.latitude is None) is not (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must be supplied together."
            )
        return self

    def to_runtime_request(
        self,
        request_id: str,
        preference_projection: AgentPreferenceProjectionV1 | None = None,
    ) -> AgentRuntimeRequest:
        """Map only validated transport fields into the strict runtime."""
        origin = (
            DiscoveryOrigin(
                latitude=self.latitude,
                longitude=self.longitude,
            )
            if self.latitude is not None and self.longitude is not None
            else None
        )
        return AgentRuntimeRequest(
            request_id=request_id,
            user_query=self.text,
            locale=self.locale,
            city=None,
            preference_projection=preference_projection,
            discovery_origin=origin,
            context=AgentRuntimeContext(),
        )


class AssistantPublicStatus(StrEnum):
    """Closed public result taxonomy."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class AssistantPriceResponse(AssistantTransportModel):
    """Exact approved price and freshness without internal claim identity."""

    minor_units: Annotated[StrictInt, Field(ge=0)]
    currency: Annotated[
        str,
        Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"),
    ]
    updated_at: AwareDatetime


class AssistantPoiResponse(AssistantTransportModel):
    """Coordinate-free composer-approved POI presentation."""

    name: Annotated[str, Field(min_length=1, max_length=200)]
    category: Annotated[str, Field(min_length=1, max_length=200)]
    address: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    distance_metres: Annotated[
        StrictFloat,
        Field(ge=0, allow_inf_nan=False),
    ] | None = None
    rating: Annotated[Decimal, Field(ge=0, le=5)] | None = None
    rating_count: Annotated[StrictInt, Field(ge=0)] | None = None
    price: AssistantPriceResponse | None = None
    opening_hours_summary: Annotated[
        str,
        Field(min_length=1, max_length=240),
    ] | None = None


class AssistantSourceResponse(AssistantTransportModel):
    """Approved public source metadata without internal source IDs."""

    label: Annotated[str, Field(min_length=1, max_length=200)]
    publisher: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    url: HttpUrl | None = None
    published_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime | None = None


class AssistantWarningResponse(AssistantTransportModel):
    """Bounded safe issue text without agent or failure-code details."""

    message: Annotated[str, Field(min_length=1, max_length=240)]
    retryable: bool


class AssistantNarrationResponse(AssistantTransportModel):
    """Approved narration content without evidence identities."""

    text: Annotated[str, Field(min_length=1, max_length=6000)]
    key_points: Annotated[
        tuple[Annotated[str, Field(min_length=1, max_length=240)], ...],
        Field(max_length=10),
    ] = ()


class AssistantItineraryItemResponse(AssistantTransportModel):
    """One approved draft stop without POI, claim, or source IDs."""

    title: Annotated[str, Field(min_length=1, max_length=240)]
    start_local_time: time
    end_local_time: time


class AssistantItineraryResponse(AssistantTransportModel):
    """Approved draft-only itinerary presentation."""

    local_date: date
    timezone: Annotated[str, Field(min_length=1, max_length=64)]
    items: Annotated[
        tuple[AssistantItineraryItemResponse, ...],
        Field(min_length=1, max_length=20),
    ]
    assumptions: Annotated[
        tuple[Annotated[str, Field(min_length=1, max_length=240)], ...],
        Field(max_length=10),
    ] = ()
    draft_only: Literal[True]


class AssistantQueryResponse(AssistantTransportModel):
    """Safe public subset of one internal orchestrator result."""

    request_id: Annotated[str, Field(min_length=1, max_length=128)]
    status: AssistantPublicStatus
    intent: IntentKind | None
    message: Annotated[str, Field(min_length=1, max_length=6000)]
    poi_results: Annotated[
        tuple[AssistantPoiResponse, ...],
        Field(max_length=20),
    ] = ()
    narration: AssistantNarrationResponse | None = None
    itinerary: AssistantItineraryResponse | None = None
    sources: Annotated[
        tuple[AssistantSourceResponse, ...],
        Field(max_length=100),
    ] = ()
    warnings: Annotated[
        tuple[AssistantWarningResponse, ...],
        Field(max_length=30),
    ] = ()
    retryable: bool

    @classmethod
    def from_runtime(
        cls,
        result: AgentRuntimeResult,
        *,
        request_id: str,
    ) -> AssistantQueryResponse:
        """Map validated runtime output without exposing internal structures."""
        if result.request_id != request_id:
            raise ValueError("Runtime request correlation changed.")

        final_output = result.final_output
        intent = _router_intent(result)
        warnings = _public_warnings(result)
        approved_output_ids = (
            _approved_output_ids(result)
            if final_output is not None
            else frozenset()
        )
        return cls(
            request_id=request_id,
            status=AssistantPublicStatus(result.status.value),
            intent=intent,
            message=(
                final_output.final_text
                if final_output is not None
                else _FAILED_MESSAGE
            ),
            poi_results=(
                tuple(
                    AssistantPoiResponse(
                        name=item.canonical_name,
                        category=item.category,
                        address=item.address,
                        distance_metres=item.distance_metres,
                        rating=item.rating,
                        rating_count=item.rating_count,
                        price=(
                            AssistantPriceResponse(
                                minor_units=item.price.price_minor_units,
                                currency=item.price.currency,
                                updated_at=item.price.source_updated_at,
                            )
                            if item.price is not None
                            else None
                        ),
                        opening_hours_summary=item.opening_hours_summary,
                    )
                    for item in final_output.poi_items
                )
                if final_output is not None
                else ()
            ),
            narration=_public_narration(result, approved_output_ids),
            itinerary=_public_itinerary(result, approved_output_ids),
            sources=_public_sources(result),
            warnings=warnings,
            retryable=any(issue.retryable for issue in warnings),
        )


def _router_intent(result: AgentRuntimeResult) -> IntentKind | None:
    for stage in result.stages:
        if isinstance(stage, RouterStageOutcome):
            return (
                stage.output.primary_intent
                if stage.output is not None
                else None
            )
    return None


def _approved_output_ids(result: AgentRuntimeResult) -> frozenset[str]:
    for stage in result.stages:
        if isinstance(stage, GroundingStageOutcome) and stage.output is not None:
            return frozenset(stage.output.approved_specialist_output_ids)
    return frozenset()


def _public_narration(
    result: AgentRuntimeResult,
    approved_output_ids: frozenset[str],
) -> AssistantNarrationResponse | None:
    if _NARRATION_OUTPUT_ID not in approved_output_ids:
        return None
    for stage in result.stages:
        if (
            isinstance(stage, NarrationStageOutcome)
            and stage.output is not None
            and stage.output.status is AnswerStatus.COMPLETE
            and stage.output.narration_text is not None
        ):
            return AssistantNarrationResponse(
                text=stage.output.narration_text,
                key_points=stage.output.key_points,
            )
    return None


def _public_itinerary(
    result: AgentRuntimeResult,
    approved_output_ids: frozenset[str],
) -> AssistantItineraryResponse | None:
    if _ITINERARY_OUTPUT_ID not in approved_output_ids:
        return None
    for stage in result.stages:
        if isinstance(stage, ItineraryStageOutcome) and stage.output is not None:
            return AssistantItineraryResponse(
                local_date=stage.output.local_date,
                timezone=stage.output.timezone,
                items=tuple(
                    AssistantItineraryItemResponse(
                        title=item.title,
                        start_local_time=item.start_local_time,
                        end_local_time=item.end_local_time,
                    )
                    for item in stage.output.items
                ),
                assumptions=stage.output.assumptions,
                draft_only=True,
            )
    return None


def _public_sources(
    result: AgentRuntimeResult,
) -> tuple[AssistantSourceResponse, ...]:
    final_output = result.final_output
    if final_output is None or not final_output.used_source_ids:
        return ()
    source_by_id = {}
    for stage in result.stages:
        if isinstance(stage, DiscoveryStageOutcome) and stage.output is not None:
            source_by_id.update(
                {
                    source.source_id: source
                    for source in stage.output.evidence.sources
                }
            )
    return tuple(
        AssistantSourceResponse(
            label=source_by_id[source_id].label,
            publisher=source_by_id[source_id].publisher,
            url=source_by_id[source_id].url,
            published_at=source_by_id[source_id].published_at,
            retrieved_at=source_by_id[source_id].retrieved_at,
        )
        for source_id in final_output.used_source_ids
        if source_id in source_by_id
    )


def _public_warnings(
    result: AgentRuntimeResult,
) -> tuple[AssistantWarningResponse, ...]:
    issues: tuple[AgentWarning | AgentFailure, ...] = (
        *result.warnings,
        *result.failures,
    )
    warnings: list[AssistantWarningResponse] = []
    seen: set[tuple[str, bool]] = set()
    for issue in issues:
        key = (issue.message, issue.retryable)
        if key in seen:
            continue
        seen.add(key)
        warnings.append(
            AssistantWarningResponse(
                message=issue.message,
                retryable=issue.retryable,
            )
        )
    return tuple(warnings[:30])
