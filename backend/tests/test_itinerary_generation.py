"""Application and curated-reader tests for structured itinerary generation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from datetime import date, datetime, time, timezone
from functools import wraps

from pydantic import HttpUrl
import pytest

from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    AgentWarning,
    DiscoveryCandidate,
    DiscoveryCompleteness,
    DiscoveryOutput,
    EvidenceBundle,
    FailureCode,
    ItineraryConstraints,
    ItineraryItem,
    ItineraryOutput,
    ItineraryRequest,
    SourceRecord,
    SupportedCity,
    SourceType,
)
from app.agents.discovery.models import (
    MenuResultEnvelope,
    PoiToolCandidate,
    PoiToolResult,
    ToolCoordinates,
    ToolSource,
)
from app.agents.itinerary.service import ItineraryService
from app.itinerary_generation.candidates import (
    CandidateResolutionError,
    CandidateResolutionErrorCode,
    DefaultItineraryCandidateResolver,
    ResolvedItineraryCandidates,
)
from app.itinerary_generation.contracts import (
    ItineraryDraftFailureCategory,
    ItineraryDraftGenerationRequest,
    ItineraryDraftGenerationStatus,
)
from app.itinerary_generation.service import StructuredItineraryGenerationService
from app.providers.poi.models import (
    Coordinates,
    PoiProviderKind,
    SourceReference,
)

PRIVATE_NOTE = "Yêu cầu riêng tư " + "x" * 450
NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


def run_async_test(
    function: Callable[[], Coroutine[object, object, None]],
) -> Callable[[], None]:
    """Run one coroutine test without adding another test dependency."""

    @wraps(function)
    def wrapper() -> None:
        asyncio.run(function())

    return wrapper


def _request(
    *,
    city: SupportedCity = SupportedCity.HCMC,
    latitude: float | None = None,
    longitude: float | None = None,
    notes: str | None = PRIVATE_NOTE,
) -> ItineraryDraftGenerationRequest:
    return ItineraryDraftGenerationRequest(
        city=city,
        local_date=date(2026, 8, 1),
        timezone=(
            "Asia/Ho_Chi_Minh"
            if city is SupportedCity.HCMC
            else "Asia/Bangkok"
        ),
        start_local_time=time(9, 0),
        end_local_time=time(17, 0),
        maximum_stops=2,
        notes=notes,
        locale="vi-VN",
        client_mode="online",
        latitude=latitude,
        longitude=longitude,
    )


def _source(source_id: str = "source-one") -> SourceReference:
    return SourceReference(
        source_id=source_id,
        source_type="official_operator",
        label="Nguồn chính thức",
        url=HttpUrl("https://example.test/source"),
        retrieved_at=NOW,
    )


def _candidate(
    provider_id: str,
    *,
    city: SupportedCity = SupportedCity.HCMC,
    distance: float | None = None,
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        id=f"curated:{provider_id}",
        provider=PoiProviderKind.CURATED,
        provider_id=provider_id,
        canonical_name=f"Địa điểm {provider_id}",
        city=city,
        category="landmark",
        coordinates=Coordinates(latitude=10.77, longitude=106.7),
        distance_metres=distance,
        sources=(_source(f"source-{provider_id}"),),
        retrieved_at=NOW,
        is_curated=True,
        is_externally_supplied=False,
    )


def _discovery(
    *,
    candidates: tuple[DiscoveryCandidate, ...] | None = None,
    partial: bool = False,
) -> DiscoveryOutput:
    failures = (
        AgentFailure(
            stage=AgentKind.DISCOVERY,
            code=FailureCode.PROVIDER_TIMEOUT,
            message="Một phần dữ liệu tuyển chọn chưa sẵn sàng.",
            retryable=True,
        ),
    ) if partial else ()
    resolved_candidates = candidates or (_candidate("b"), _candidate("a"))
    sources = {
        source.source_id: SourceRecord(
            source_id=source.source_id,
            source_type=SourceType(source.source_type),
            label=source.label,
            publisher=source.publisher,
            url=source.url,
            published_at=source.published_at,
            retrieved_at=source.retrieved_at,
        )
        for candidate in resolved_candidates
        for source in candidate.sources
    }
    return DiscoveryOutput(
        candidates=resolved_candidates,
        evidence=EvidenceBundle(
            sources=tuple(sources[source_id] for source_id in sorted(sources))
        ),
        provider_failures=failures,
        completeness=(
            DiscoveryCompleteness.PARTIAL
            if partial
            else DiscoveryCompleteness.COMPLETE
        ),
        is_truncated=False,
    )


class FakeResolver:
    def __init__(
        self,
        result: DiscoveryOutput | CandidateResolutionError,
    ) -> None:
        self.result = result
        self.requests: list[ItineraryDraftGenerationRequest] = []

    async def resolve(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ResolvedItineraryCandidates:
        self.requests.append(request)
        if isinstance(self.result, CandidateResolutionError):
            raise self.result
        return ResolvedItineraryCandidates(discovery=self.result)


class CapturingItinerary:
    def __init__(self, output: ItineraryOutput | None = None) -> None:
        self.output = output
        self.requests: list[ItineraryRequest] = []

    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        self.requests.append(request)
        return self.output or _output(request)


class CancellingResolver:
    async def resolve(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ResolvedItineraryCandidates:
        del request
        raise asyncio.CancelledError


class CancellingItinerary:
    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        del request
        raise asyncio.CancelledError


def _output(
    request: ItineraryRequest,
    *,
    warnings: tuple[AgentWarning, ...] = (),
) -> ItineraryOutput:
    midpoint = time(13, 0)
    return ItineraryOutput(
        local_date=request.local_date,
        timezone=request.timezone,
        start_local_time=request.start_local_time,
        end_local_time=request.end_local_time,
        items=(
            ItineraryItem(
                item_id="item-one",
                poi_id=request.candidates[0].id,
                title=request.candidates[0].canonical_name,
                start_local_time=request.start_local_time,
                end_local_time=midpoint,
            ),
            ItineraryItem(
                item_id="item-two",
                poi_id=request.candidates[1].id,
                title=request.candidates[1].canonical_name,
                start_local_time=midpoint,
                end_local_time=request.end_local_time,
            ),
        ),
        assumptions=("Đây là lịch trình nháp.",),
        warnings=warnings,
        draft_only=True,
    )


@run_async_test
async def test_exact_typed_itinerary_mapping_without_query_serialization() -> None:
    resolver = FakeResolver(_discovery())
    itinerary = CapturingItinerary()
    service = StructuredItineraryGenerationService(resolver, itinerary)
    request = _request(latitude=10.776, longitude=106.7)

    response = await service.generate(request)

    assert response.status is ItineraryDraftGenerationStatus.SUCCESS
    mapped = itinerary.requests[0]
    assert mapped.city is request.city
    assert mapped.local_date == request.local_date
    assert mapped.timezone == request.timezone
    assert mapped.start_local_time == request.start_local_time
    assert mapped.end_local_time == request.end_local_time
    assert mapped.constraints.maximum_stops == request.maximum_stops
    assert mapped.constraints.notes == (PRIVATE_NOTE,)
    assert mapped.start_origin is not None
    assert mapped.start_origin.latitude == 10.776
    assert mapped.candidates == _discovery().candidates
    assert not hasattr(mapped, "user_query")


@run_async_test
async def test_deterministic_no_model_fallback_preserves_candidate_order() -> None:
    resolver = FakeResolver(_discovery())
    service = StructuredItineraryGenerationService(
        resolver,
        ItineraryService(executor_factory=lambda: None),
    )
    request = _request(notes=None)

    first = await service.generate(request)
    second = await service.generate(request)

    assert first == second
    assert [item.title for item in first.items] == [
        "Địa điểm b",
        "Địa điểm a",
    ]


@run_async_test
async def test_partial_preserves_all_safe_warnings() -> None:
    itinerary_warning = AgentWarning(
        stage=AgentKind.ITINERARY,
        code=FailureCode.PARTIAL_RESULT,
        message="Hãy kiểm tra điều kiện thực tế trước khi đi.",
        retryable=False,
    )
    resolver = FakeResolver(_discovery(partial=True))
    itinerary = CapturingItinerary()
    request = _request()
    itinerary.output = _output(
        ItineraryRequest(
            city=request.city,
            local_date=request.local_date,
            timezone=request.timezone,
            start_local_time=request.start_local_time,
            end_local_time=request.end_local_time,
            candidates=_discovery().candidates,
            evidence=EvidenceBundle(),
            constraints=ItineraryConstraints(
                maximum_stops=2,
                notes=(PRIVATE_NOTE,),
            ),
        ),
        warnings=(itinerary_warning,),
    )

    response = await StructuredItineraryGenerationService(
        resolver,
        itinerary,
    ).generate(request)

    assert response.status is ItineraryDraftGenerationStatus.PARTIAL
    assert response.warnings == (
        "Một phần dữ liệu tuyển chọn chưa sẵn sàng.",
        "Hãy kiểm tra điều kiện thực tế trước khi đi.",
    )
    assert response.retryable is True


@run_async_test
async def test_failed_results_and_invalid_output_fail_closed() -> None:
    unavailable = await StructuredItineraryGenerationService(
        FakeResolver(
            CandidateResolutionError(
                CandidateResolutionErrorCode.TIMEOUT,
                retryable=True,
            )
        ),
        CapturingItinerary(),
    ).generate(_request())
    assert unavailable.status is ItineraryDraftGenerationStatus.FAILED
    assert unavailable.failure_category is (
        ItineraryDraftFailureCategory.CANDIDATE_RESOLUTION_UNAVAILABLE
    )
    assert unavailable.retryable is True

    empty = DiscoveryOutput(
        candidates=(),
        evidence=EvidenceBundle(),
        completeness=DiscoveryCompleteness.COMPLETE,
        is_truncated=False,
    )
    insufficient = await StructuredItineraryGenerationService(
        FakeResolver(empty),
        CapturingItinerary(),
    ).generate(_request())
    assert insufficient.failure_category is (
        ItineraryDraftFailureCategory.INSUFFICIENT_CANDIDATES
    )

    request = _request()
    wrong_window_request = ItineraryRequest(
        city=request.city,
        local_date=request.local_date,
        timezone=request.timezone,
        start_local_time=time(8, 0),
        end_local_time=request.end_local_time,
        candidates=_discovery().candidates,
        evidence=EvidenceBundle(),
        constraints=ItineraryConstraints(maximum_stops=2),
    )
    invalid = await StructuredItineraryGenerationService(
        FakeResolver(_discovery()),
        CapturingItinerary(_output(wrong_window_request)),
    ).generate(request)
    assert invalid.failure_category is (
        ItineraryDraftFailureCategory.INVALID_GENERATION_OUTPUT
    )
    assert invalid.items == ()


@run_async_test
async def test_cancellation_propagates_from_resolution_and_itinerary() -> None:
    with pytest.raises(asyncio.CancelledError):
        await StructuredItineraryGenerationService(
            CancellingResolver(),
            CapturingItinerary(),
        ).generate(_request())
    with pytest.raises(asyncio.CancelledError):
        await StructuredItineraryGenerationService(
            FakeResolver(_discovery()),
            CancellingItinerary(),
        ).generate(_request())


class FakeDiscoveryService:
    def __init__(self, output: DiscoveryOutput) -> None:
        self.output = output
        self.requests: list[object] = []

    async def discover(self, request: object) -> DiscoveryOutput:
        self.requests.append(request)
        return self.output


class FakeCityReader:
    def __init__(self, result: PoiToolResult) -> None:
        self.result = result
        self.calls: list[tuple[SupportedCity, int]] = []

    async def read(self, city: SupportedCity, limit: int) -> PoiToolResult:
        self.calls.append((city, limit))
        return self.result


class FakeMenuReader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    async def read_menu_items(
        self,
        poi_provider_ids: tuple[str, ...],
    ) -> MenuResultEnvelope:
        self.calls.append(poi_provider_ids)
        return MenuResultEnvelope()


def _tool_result() -> PoiToolResult:
    source = ToolSource(
        source_id="source-city",
        source_type=SourceType.OFFICIAL_OPERATOR,
        label="Nguồn thành phố",
        retrieved_at=NOW,
    )
    items = tuple(
        PoiToolCandidate(
            id=f"curated:{provider_id}",
            provider=PoiProviderKind.CURATED,
            provider_id=provider_id,
            canonical_name=f"Địa điểm {provider_id}",
            city=SupportedCity.HCMC,
            category="landmark",
            coordinates=ToolCoordinates(latitude=10.77, longitude=106.7),
            distance_metres=None,
            sources=(source,),
            retrieved_at=NOW,
            is_curated=True,
            is_externally_supplied=False,
        )
        for provider_id in ("a", "b")
    )
    return PoiToolResult(
        provider=PoiProviderKind.CURATED,
        items=items,
        returned_count=2,
        is_complete=True,
        freshness_at=NOW,
    )


@run_async_test
async def test_resolver_uses_real_nearby_order_with_coordinates() -> None:
    discovery = FakeDiscoveryService(
        _discovery(
            candidates=(
                _candidate("near", distance=10.0),
                _candidate("far", distance=20.0),
            )
        )
    )
    city_reader = FakeCityReader(_tool_result())
    menus = FakeMenuReader()
    resolver = DefaultItineraryCandidateResolver(
        discovery,
        city_reader,
        menus,
    )

    resolved = await resolver.resolve(
        _request(latitude=10.776, longitude=106.7)
    )

    assert [item.provider_id for item in resolved.discovery.candidates] == [
        "near",
        "far",
    ]
    assert [item.distance_metres for item in resolved.discovery.candidates] == [
        10.0,
        20.0,
    ]
    assert not city_reader.calls
    assert not menus.calls


@run_async_test
async def test_resolver_city_only_keeps_stable_order_and_absent_distance() -> None:
    discovery = FakeDiscoveryService(_discovery())
    city_reader = FakeCityReader(_tool_result())
    menus = FakeMenuReader()
    resolver = DefaultItineraryCandidateResolver(
        discovery,
        city_reader,
        menus,
    )

    first = await resolver.resolve(_request())
    second = await resolver.resolve(_request())

    assert first == second
    assert city_reader.calls == [
        (SupportedCity.HCMC, 2),
        (SupportedCity.HCMC, 2),
    ]
    assert [item.provider_id for item in first.discovery.candidates] == [
        "a",
        "b",
    ]
    assert all(
        item.distance_metres is None
        for item in first.discovery.candidates
    )
    assert menus.calls == [("a", "b"), ("a", "b")]
    assert first.discovery.evidence.sources
    assert first.discovery.evidence.claims
    assert not discovery.requests
