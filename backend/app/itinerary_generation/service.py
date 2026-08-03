"""FastAPI-independent structured itinerary generation service."""

from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable

from pydantic import ValidationError

from app.agents.contracts import (
    DiscoveryCompleteness,
    DiscoveryOrigin,
    DiscoveryOutput,
    ItineraryConstraints,
    ItineraryOutput,
    ItineraryRequest,
)
from app.agents.itinerary.errors import ItineraryExecutionError
from app.agents.itinerary.service import ItineraryService
from app.itinerary_generation.candidates import (
    CandidateResolutionError,
    ItineraryCandidateResolver,
)
from app.itinerary_generation.contracts import (
    ItineraryDraftFailureCategory,
    ItineraryDraftGenerationRequest,
    ItineraryDraftGenerationResponse,
    ItineraryDraftGenerationStatus,
    ItineraryDraftItemResponse,
)

_TRUNCATED_WARNING = (
    "Chỉ một tập hợp địa điểm được tuyển chọn có giới hạn được dùng cho bản nháp."
)


@runtime_checkable
class ItineraryDraftExecutor(Protocol):
    """Existing T045-compatible itinerary execution boundary."""

    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        """Return one validated T045 draft."""
        ...


@runtime_checkable
class StructuredItineraryGenerator(Protocol):
    """Generate one safe structured result without persistence."""

    async def generate(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ItineraryDraftGenerationResponse:
        """Resolve candidates and create one transport-neutral result."""
        ...


class StructuredItineraryGenerationService:
    """Map a structured form directly into curated discovery and T045."""

    def __init__(
        self,
        candidates: ItineraryCandidateResolver,
        itinerary: ItineraryDraftExecutor | None = None,
    ) -> None:
        self._candidates = candidates
        self._itinerary = itinerary or ItineraryService()

    async def generate(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ItineraryDraftGenerationResponse:
        try:
            resolved = await self._candidates.resolve(request)
        except asyncio.CancelledError:
            raise
        except CandidateResolutionError as error:
            return _failed_response(
                request,
                ItineraryDraftFailureCategory.CANDIDATE_RESOLUTION_UNAVAILABLE,
                retryable=error.retryable,
            )

        discovery = resolved.discovery
        if not discovery.candidates:
            return _failed_response(
                request,
                ItineraryDraftFailureCategory.INSUFFICIENT_CANDIDATES,
                retryable=False,
            )
        itinerary_request = ItineraryRequest(
            city=request.city,
            local_date=request.local_date,
            timezone=request.timezone,
            start_local_time=request.start_local_time,
            end_local_time=request.end_local_time,
            candidates=discovery.candidates,
            evidence=discovery.evidence,
            constraints=ItineraryConstraints(
                maximum_stops=request.maximum_stops,
                notes=(request.notes,) if request.notes is not None else (),
            ),
            start_origin=(
                DiscoveryOrigin(
                    latitude=request.latitude,
                    longitude=request.longitude,
                )
                if request.latitude is not None
                and request.longitude is not None
                else None
            ),
        )
        try:
            output = await self._itinerary.draft(itinerary_request)
        except asyncio.CancelledError:
            raise
        except ItineraryExecutionError:
            return _failed_response(
                request,
                ItineraryDraftFailureCategory.GENERATION_UNAVAILABLE,
                retryable=False,
            )
        try:
            validated = ItineraryOutput.model_validate(
                output.model_dump(mode="python")
            ).validate_against(itinerary_request)
            warnings = _safe_warnings(discovery, validated)
            response = ItineraryDraftGenerationResponse(
                status=(
                    ItineraryDraftGenerationStatus.PARTIAL
                    if warnings
                    else ItineraryDraftGenerationStatus.SUCCESS
                ),
                city=request.city,
                local_date=request.local_date,
                timezone=request.timezone,
                start_local_time=request.start_local_time,
                end_local_time=request.end_local_time,
                items=tuple(
                    ItineraryDraftItemResponse(
                        start_local_time=item.start_local_time,
                        end_local_time=item.end_local_time,
                        title=item.title,
                    )
                    for item in validated.items
                ),
                assumptions=validated.assumptions,
                warnings=warnings,
                retryable=any(
                    failure.retryable
                    for failure in discovery.provider_failures
                )
                or any(warning.retryable for warning in validated.warnings),
            )
            return response.validate_against(request)
        except (AttributeError, TypeError, ValueError, ValidationError):
            return _failed_response(
                request,
                ItineraryDraftFailureCategory.INVALID_GENERATION_OUTPUT,
                retryable=False,
            )


def _safe_warnings(
    discovery: DiscoveryOutput,
    itinerary: ItineraryOutput,
) -> tuple[str, ...]:
    values = [failure.message for failure in discovery.provider_failures]
    if (
        discovery.completeness is DiscoveryCompleteness.PARTIAL
        and not discovery.provider_failures
    ):
        values.append(_TRUNCATED_WARNING)
    values.extend(warning.message for warning in itinerary.warnings)
    return tuple(dict.fromkeys(values))


def _failed_response(
    request: ItineraryDraftGenerationRequest,
    category: ItineraryDraftFailureCategory,
    *,
    retryable: bool,
) -> ItineraryDraftGenerationResponse:
    return ItineraryDraftGenerationResponse(
        status=ItineraryDraftGenerationStatus.FAILED,
        city=request.city,
        local_date=request.local_date,
        timezone=request.timezone,
        start_local_time=request.start_local_time,
        end_local_time=request.end_local_time,
        failure_category=category,
        retryable=retryable,
    ).validate_against(request)
