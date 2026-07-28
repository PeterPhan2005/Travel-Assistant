"""T048 strict application-code orchestration and isolation tests."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Coroutine
from datetime import date, datetime, time, timezone
from decimal import Decimal
from functools import wraps
from pathlib import Path

import pytest
from pydantic import HttpUrl, ValidationError

from app.agents.composer.renderer import build_deterministic_response
from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    AgentRuntimeContext,
    AgentRuntimeRequest,
    AnswerStatus,
    CultureGuidanceItem,
    DiscoveryCandidate,
    DiscoveryCompleteness,
    DiscoveryOrigin,
    DiscoveryOutput,
    EvidenceBundle,
    FactKind,
    FactualClaim,
    FailureCode,
    GroundingCandidateClaim,
    GroundingCandidateEvidence,
    GroundingReviewOutput,
    GroundingReviewRequest,
    GroundingReviewStatus,
    IntentKind,
    ItineraryItem,
    ItineraryOutput,
    LocalCultureOutput,
    NarrationOutput,
    PoiIdentity,
    PriceFact,
    ResponseComposerOutput,
    ResponseComposerRequest,
    RouterEntities,
    RouterItineraryConstraints,
    RouterOutput,
    RuntimeItineraryWindow,
    RuntimeResultStatus,
    SourceRecord,
    SourceType,
    SpecialistKind,
    StageStatus,
    SupportedCity,
)
from app.agents.discovery.errors import DiscoveryExecutionError
from app.agents.grounding.reviewer import build_deterministic_review
from app.agents.orchestration import (
    AgentOrchestratorService,
    OrchestrationPolicy,
)
from app.agents.orchestration.evidence import build_approved_evidence
from app.agents.orchestration.service import (
    ComposerBoundary,
    DiscoveryBoundary,
    GroundingBoundary,
    ItineraryBoundary,
    LocalCultureBoundary,
    NarrationBoundary,
    RouterBoundary,
)
from app.agents.contracts import (
    DiscoveryRequest,
    ItineraryRequest,
    LocalCultureRequest,
    NarrationRequest,
    RouterRequest,
)
from app.providers.poi.models import (
    Coordinates,
    PoiProviderKind,
    SourceReference,
)

BACKEND = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 28, 4, 0, tzinfo=timezone.utc)
NARRATION_TEXT = " ".join(f"nội_dung_{index}" for index in range(100))


def _run_async_test(
    test: Callable[[], Coroutine[object, object, None]],
) -> Callable[[], None]:
    @wraps(test)
    def wrapper() -> None:
        asyncio.run(test())

    return wrapper


def _source(
    source_id: str = "source-a",
    *,
    label: str = "Nguồn chính thức",
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_INSTITUTION,
        label=label,
        publisher="Đơn vị quản lý",
        url=HttpUrl(f"https://example.test/{source_id}"),
        retrieved_at=NOW,
    )


def _source_reference(source: SourceRecord) -> SourceReference:
    return SourceReference(
        source_id=source.source_id,
        source_type=source.source_type.value,
        label=source.label,
        publisher=source.publisher,
        url=source.url,
        published_at=source.published_at,
        retrieved_at=source.retrieved_at,
    )


def _claim(
    claim_id: str,
    fact_kind: FactKind,
    statement: str,
    *,
    source_id: str = "source-a",
    price: PriceFact | None = None,
) -> FactualClaim:
    return FactualClaim(
        claim_id=claim_id,
        evidence_id=f"evidence-{claim_id}",
        fact_kind=fact_kind,
        statement=statement,
        supporting_source_ids=(source_id,),
        poi_id="curated:poi-a",
        freshness_at=price.source_updated_at if price is not None else NOW,
        price=price,
    )


def _evidence() -> EvidenceBundle:
    return EvidenceBundle(
        sources=(_source(),),
        claims=(
            _claim(
                "claim-culture",
                FactKind.CULTURE,
                "Giữ giọng nói vừa phải tại địa điểm.",
            ),
            _claim(
                "claim-history",
                FactKind.HISTORY,
                "Địa điểm có lịch sử được nguồn xác nhận.",
            ),
        ),
    )


def _candidate() -> DiscoveryCandidate:
    source = _source()
    return DiscoveryCandidate(
        id="curated:poi-a",
        provider=PoiProviderKind.CURATED,
        provider_id="poi-a",
        canonical_name="Bảo tàng A",
        city=SupportedCity.HCMC,
        category="museum",
        address="Địa chỉ đã xác nhận",
        coordinates=Coordinates(latitude=10.77, longitude=106.69),
        distance_metres=125.0,
        rating=Decimal("4.5"),
        rating_count=100,
        price_level=None,
        opening_hours_summary="Mở cửa theo lịch công bố",
        sources=(_source_reference(source),),
        retrieved_at=NOW,
        is_curated=True,
        is_externally_supplied=False,
    )


def _discovery_output(
    *,
    partial: bool = False,
) -> DiscoveryOutput:
    failure = AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PROVIDER_TIMEOUT,
        message="Một nguồn dữ liệu phản hồi quá thời hạn.",
        retryable=True,
    )
    return DiscoveryOutput(
        candidates=(_candidate(),),
        evidence=_evidence(),
        provider_failures=(failure,) if partial else (),
        completeness=(
            DiscoveryCompleteness.PARTIAL
            if partial
            else DiscoveryCompleteness.COMPLETE
        ),
        is_truncated=False,
    )


def _narration_output() -> NarrationOutput:
    return NarrationOutput(
        status=AnswerStatus.COMPLETE,
        narration_text=NARRATION_TEXT,
        key_points=("Lịch sử đã được xác nhận.",),
        used_source_ids=("source-a",),
        used_claim_ids=("claim-history",),
        limitation_reason=None,
    )


def _limited_narration() -> NarrationOutput:
    return NarrationOutput(
        status=AnswerStatus.LIMITED,
        narration_text=None,
        key_points=(),
        used_source_ids=(),
        used_claim_ids=(),
        limitation_reason="Chưa có đủ bằng chứng phù hợp.",
    )


def _culture_output() -> LocalCultureOutput:
    return LocalCultureOutput(
        status=AnswerStatus.COMPLETE,
        guidance=(
            CultureGuidanceItem(
                guidance_id="culture-guidance-001",
                text="Giữ giọng nói vừa phải tại địa điểm.",
                claim_ids=("claim-culture",),
                source_ids=("source-a",),
            ),
        ),
        respectful_caution="Hãy quan sát hướng dẫn tại chỗ.",
        limitation_reason=None,
    )


def _itinerary_output() -> ItineraryOutput:
    return ItineraryOutput(
        local_date=date(2026, 8, 1),
        timezone="Asia/Ho_Chi_Minh",
        start_local_time=time(9, 0),
        end_local_time=time(17, 0),
        items=(
            ItineraryItem(
                item_id="itinerary-item-001",
                poi_id="curated:poi-a",
                title="Bảo tàng A",
                start_local_time=time(9, 0),
                end_local_time=time(17, 0),
                supporting_claim_ids=("claim-history",),
                supporting_source_ids=("source-a",),
            ),
        ),
        assumptions=(
            "Đây là lịch trình nháp và thời lượng được chia theo khung giờ.",
            "Chưa tính thời gian di chuyển hoặc tình trạng thực tế.",
        ),
        warnings=(),
        draft_only=True,
    )


def _all_router_output() -> RouterOutput:
    return RouterOutput(
        primary_intent=IntentKind.ITINERARY_DRAFTING,
        entities=RouterEntities(
            city=SupportedCity.HCMC,
            category="museum",
            query_term="bảo tàng",
            referenced_poi_ids=("curated:poi-a",),
            itinerary_constraints=RouterItineraryConstraints(
                maximum_stops=2,
                notes=("Ưu tiên nhịp độ chậm",),
            ),
        ),
        specialist_plan=(
            SpecialistKind.DISCOVERY,
            SpecialistKind.NARRATION,
            SpecialistKind.LOCAL_CULTURE,
            SpecialistKind.ITINERARY,
        ),
        discovery_required=True,
        clarification_reason=None,
    )


def _router_output(
    *,
    intent: IntentKind,
    plan: tuple[SpecialistKind, ...],
) -> RouterOutput:
    return RouterOutput(
        primary_intent=intent,
        entities=RouterEntities(
            city=SupportedCity.HCMC,
            referenced_poi_ids=(),
        ),
        specialist_plan=plan,
        discovery_required=SpecialistKind.DISCOVERY in plan,
        clarification_reason=(
            "Yêu cầu nằm ngoài phạm vi hỗ trợ."
            if intent is IntentKind.UNSUPPORTED
            else None
        ),
    )


def _runtime_request(
    *,
    context: AgentRuntimeContext | None = None,
) -> AgentRuntimeRequest:
    candidate = _candidate()
    return AgentRuntimeRequest(
        request_id="request-t048",
        user_query="Hãy giới thiệu văn hóa và lập lịch trình",
        locale="vi-VN",
        city=SupportedCity.HCMC,
        preferences=None,
        discovery_origin=DiscoveryOrigin(
            latitude=10.76,
            longitude=106.68,
        ),
        context=context
        or AgentRuntimeContext(
            selected_poi=PoiIdentity(
                poi_id=candidate.id,
                canonical_name=candidate.canonical_name,
                city=candidate.city,
                category=candidate.category,
            ),
            candidates=(candidate,),
            itinerary_window=RuntimeItineraryWindow(
                local_date=date(2026, 8, 1),
                timezone="Asia/Ho_Chi_Minh",
                start_local_time=time(9, 0),
                end_local_time=time(17, 0),
            ),
        ),
    )


class _FanoutProbe:
    def __init__(self, expected: int) -> None:
        self.expected = expected
        self.active = 0
        self.maximum_active = 0
        self.started: list[str] = []
        self.finished: list[str] = []
        self.all_started = asyncio.Event()

    async def enter(self, name: str) -> None:
        self.started.append(name)
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        if len(self.started) == self.expected:
            self.all_started.set()
        await self.all_started.wait()

    def leave(self, name: str) -> None:
        self.active -= 1
        self.finished.append(name)


class _RouterService:
    def __init__(
        self,
        result: RouterOutput | BaseException,
        events: list[str] | None = None,
    ) -> None:
        self.result = result
        self.events = events
        self.calls: list[RouterRequest] = []

    async def route(self, request: RouterRequest) -> RouterOutput:
        self.calls.append(request)
        if self.events is not None:
            self.events.append("router")
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class _DiscoveryService:
    def __init__(
        self,
        results: list[DiscoveryOutput | BaseException],
        events: list[str] | None = None,
    ) -> None:
        self.results = results
        self.events = events
        self.calls: list[DiscoveryRequest] = []

    async def discover(self, request: DiscoveryRequest) -> DiscoveryOutput:
        self.calls.append(request)
        if self.events is not None:
            self.events.append("discovery")
        result = self.results[min(len(self.calls) - 1, len(self.results) - 1)]
        if isinstance(result, BaseException):
            raise result
        return result


class _NarrationService:
    def __init__(
        self,
        result: NarrationOutput | BaseException,
        probe: _FanoutProbe | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.result = result
        self.probe = probe
        self.events = events
        self.calls: list[NarrationRequest] = []

    async def narrate(self, request: NarrationRequest) -> NarrationOutput:
        self.calls.append(request)
        if self.events is not None:
            self.events.append("narration-start")
        if self.probe is not None:
            await self.probe.enter("narration")
        try:
            if isinstance(self.result, BaseException):
                raise self.result
            return self.result
        finally:
            if self.probe is not None:
                self.probe.leave("narration")
            if self.events is not None:
                self.events.append("narration-end")


class _CultureService:
    def __init__(
        self,
        result: LocalCultureOutput | BaseException,
        probe: _FanoutProbe | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.result = result
        self.probe = probe
        self.events = events
        self.calls: list[LocalCultureRequest] = []

    async def advise(
        self,
        request: LocalCultureRequest,
    ) -> LocalCultureOutput:
        self.calls.append(request)
        if self.events is not None:
            self.events.append("culture-start")
        if self.probe is not None:
            await self.probe.enter("culture")
        try:
            if isinstance(self.result, BaseException):
                raise self.result
            return self.result
        finally:
            if self.probe is not None:
                self.probe.leave("culture")
            if self.events is not None:
                self.events.append("culture-end")


class _ItineraryService:
    def __init__(
        self,
        result: ItineraryOutput | BaseException,
        probe: _FanoutProbe | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.result = result
        self.probe = probe
        self.events = events
        self.calls: list[ItineraryRequest] = []

    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        self.calls.append(request)
        if self.events is not None:
            self.events.append("itinerary-start")
        if self.probe is not None:
            await self.probe.enter("itinerary")
        try:
            if isinstance(self.result, BaseException):
                raise self.result
            return self.result
        finally:
            if self.probe is not None:
                self.probe.leave("itinerary")
            if self.events is not None:
                self.events.append("itinerary-end")


class _GroundingService:
    def __init__(
        self,
        factory: Callable[
            [GroundingReviewRequest],
            GroundingReviewOutput,
        ] = build_deterministic_review,
        events: list[str] | None = None,
        failure: BaseException | None = None,
    ) -> None:
        self.factory = factory
        self.events = events
        self.failure = failure
        self.calls: list[GroundingReviewRequest] = []

    async def review(
        self,
        request: GroundingReviewRequest,
    ) -> GroundingReviewOutput:
        self.calls.append(request)
        if self.events is not None:
            self.events.append("grounding")
        if self.failure is not None:
            raise self.failure
        return self.factory(request)


class _ComposerService:
    def __init__(
        self,
        events: list[str] | None = None,
        failure: BaseException | None = None,
    ) -> None:
        self.events = events
        self.failure = failure
        self.calls: list[ResponseComposerRequest] = []

    async def compose(
        self,
        request: ResponseComposerRequest,
    ) -> ResponseComposerOutput:
        self.calls.append(request)
        if self.events is not None:
            self.events.append("composer")
        if self.failure is not None:
            raise self.failure
        return build_deterministic_response(request)


def _orchestrator(
    *,
    router: RouterBoundary,
    discovery: DiscoveryBoundary | None = None,
    narration: NarrationBoundary | None = None,
    culture: LocalCultureBoundary | None = None,
    itinerary: ItineraryBoundary | None = None,
    grounding: GroundingBoundary | None = None,
    composer: ComposerBoundary | None = None,
    policy: OrchestrationPolicy | None = None,
    clock: Callable[[], float] | None = None,
) -> AgentOrchestratorService:
    return AgentOrchestratorService(
        router=router,
        discovery=discovery or _DiscoveryService([_discovery_output()]),
        narration=narration or _NarrationService(_narration_output()),
        local_culture=culture or _CultureService(_culture_output()),
        itinerary=itinerary or _ItineraryService(_itinerary_output()),
        grounding=grounding or _GroundingService(),
        composer=composer or _ComposerService(),
        policy=policy,
        **({"monotonic_clock": clock} if clock is not None else {}),
    )


@_run_async_test
async def test_complete_graph_maps_scoped_inputs_and_fans_out_concurrently() -> None:
    events: list[str] = []
    probe = _FanoutProbe(expected=3)
    router = _RouterService(_all_router_output(), events)
    discovery = _DiscoveryService([_discovery_output()], events)
    narration = _NarrationService(_narration_output(), probe, events)
    culture = _CultureService(_culture_output(), probe, events)
    itinerary = _ItineraryService(_itinerary_output(), probe, events)
    grounding = _GroundingService(events=events)
    composer = _ComposerService(events=events)

    result = await _orchestrator(
        router=router,
        discovery=discovery,
        narration=narration,
        culture=culture,
        itinerary=itinerary,
        grounding=grounding,
        composer=composer,
    ).run(_runtime_request())

    assert result.status is RuntimeResultStatus.SUCCESS
    assert tuple(stage.agent for stage in result.stages) == (
        AgentKind.ROUTER,
        AgentKind.DISCOVERY,
        AgentKind.NARRATION,
        AgentKind.LOCAL_CULTURE,
        AgentKind.ITINERARY,
        AgentKind.GROUNDING_REVIEWER,
        AgentKind.RESPONSE_COMPOSER,
    )
    assert probe.maximum_active == 3
    assert len(router.calls) == len(discovery.calls) == 1
    assert len(narration.calls) == len(culture.calls) == 1
    assert len(itinerary.calls) == len(grounding.calls) == 1
    assert len(composer.calls) == 1
    assert events.index("router") < events.index("discovery")
    assert events.index("discovery") < events.index("narration-start")
    assert events.index("grounding") > max(
        events.index("narration-end"),
        events.index("culture-end"),
        events.index("itinerary-end"),
    )
    assert events.index("composer") > events.index("grounding")

    router_request = router.calls[0]
    assert set(type(router_request).model_fields) == {
        "user_query",
        "locale",
        "city",
        "preferences",
    }
    discovery_request = discovery.calls[0]
    assert discovery_request.origin == _runtime_request().discovery_origin
    assert discovery_request.query == "bảo tàng"
    assert discovery_request.category == "museum"
    assert tuple(
        fact.value for fact in discovery_request.requested_fact_kinds
    ) == tuple(
        sorted(
            {
                "category",
                "culture",
                "description",
                "distance",
                "etiquette",
                "history",
                "identity",
                "itinerary_constraint",
                "location",
                "opening_hours",
                "price",
                "rating",
            }
        )
    )
    narration_request = narration.calls[0]
    assert narration_request.poi.poi_id == "curated:poi-a"
    assert {
        claim.poi_id for claim in narration_request.evidence.claims
    } == {"curated:poi-a"}
    culture_request = culture.calls[0]
    assert {
        claim.fact_kind for claim in culture_request.evidence.claims
    } == {FactKind.CULTURE}
    itinerary_request = itinerary.calls[0]
    assert itinerary_request.local_date == date(2026, 8, 1)
    assert itinerary_request.timezone == "Asia/Ho_Chi_Minh"
    assert itinerary_request.start_local_time == time(9, 0)
    assert itinerary_request.end_local_time == time(17, 0)
    assert itinerary_request.constraints.maximum_stops == 2
    assert itinerary_request.constraints.required_poi_ids == (
        "curated:poi-a",
    )
    assert itinerary_request.start_origin == _runtime_request().discovery_origin
    assert "origin" not in result.model_dump_json()


@_run_async_test
async def test_one_specialist_failure_keeps_other_approved_content_partial() -> None:
    router = _RouterService(_all_router_output())
    grounding = _GroundingService()
    composer = _ComposerService()
    result = await _orchestrator(
        router=router,
        narration=_NarrationService(RuntimeError("private detail")),
        grounding=grounding,
        composer=composer,
    ).run(_runtime_request())

    assert result.status is RuntimeResultStatus.PARTIAL
    assert result.final_output is not None
    narration_stage = next(
        stage
        for stage in result.stages
        if stage.agent is AgentKind.NARRATION
    )
    assert narration_stage.status is StageStatus.FAILED
    assert narration_stage.failure is not None
    assert narration_stage.failure.code is FailureCode.SPECIALIST_FAILED
    assert "private detail" not in result.model_dump_json()
    reviewed_ids = {
        output.output_id
        for output in grounding.calls[0].specialist_outputs
    }
    assert "runtime-narration" not in reviewed_ids
    assert "runtime-local-culture" in reviewed_ids
    assert composer.calls[0].warnings == result.warnings


@_run_async_test
async def test_partial_discovery_warning_is_preserved_exactly() -> None:
    router = _RouterService(
        _router_output(
            intent=IntentKind.NEARBY_DISCOVERY,
            plan=(SpecialistKind.DISCOVERY,),
        )
    )
    composer = _ComposerService()
    result = await _orchestrator(
        router=router,
        discovery=_DiscoveryService([_discovery_output(partial=True)]),
        composer=composer,
    ).run(_runtime_request())

    assert result.status is RuntimeResultStatus.PARTIAL
    assert result.warnings
    assert result.warnings[0].stage is AgentKind.DISCOVERY
    assert result.warnings[0].code is FailureCode.PARTIAL_RESULT
    assert composer.calls[0].warnings == result.warnings
    assert result.final_output is not None
    assert result.final_output.warnings == result.warnings


@_run_async_test
async def test_missing_itinerary_window_fails_without_inventing_time() -> None:
    candidate = _candidate()
    request = _runtime_request(
        context=AgentRuntimeContext(
            selected_poi=PoiIdentity(
                poi_id=candidate.id,
                canonical_name=candidate.canonical_name,
                city=candidate.city,
                category=candidate.category,
            ),
            candidates=(candidate,),
        )
    )
    itinerary = _ItineraryService(_itinerary_output())
    result = await _orchestrator(
        router=_RouterService(_all_router_output()),
        itinerary=itinerary,
    ).run(request)

    assert result.status is RuntimeResultStatus.PARTIAL
    assert result.final_output is not None
    assert itinerary.calls == []
    itinerary_stage = next(
        stage
        for stage in result.stages
        if stage.agent is AgentKind.ITINERARY
    )
    assert itinerary_stage.status is StageStatus.FAILED
    assert itinerary_stage.failure is not None
    assert itinerary_stage.failure.code is FailureCode.INVALID_INPUT
    narration_stage = next(
        stage
        for stage in result.stages
        if stage.agent is AgentKind.NARRATION
    )
    assert narration_stage.status is StageStatus.SUCCESS


@_run_async_test
async def test_unsupported_intent_runs_no_specialist_and_returns_safe_partial() -> None:
    unsupported = _router_output(
        intent=IntentKind.UNSUPPORTED,
        plan=(),
    )
    discovery = _DiscoveryService([_discovery_output()])
    narration = _NarrationService(_narration_output())
    composer = _ComposerService()
    result = await _orchestrator(
        router=_RouterService(unsupported),
        discovery=discovery,
        narration=narration,
        composer=composer,
    ).run(
        _runtime_request(
            context=AgentRuntimeContext(evidence=_evidence())
        )
    )

    assert result.status is RuntimeResultStatus.PARTIAL
    assert result.final_output is not None
    assert tuple(stage.agent for stage in result.stages) == (
        AgentKind.ROUTER,
        AgentKind.GROUNDING_REVIEWER,
        AgentKind.RESPONSE_COMPOSER,
    )
    assert discovery.calls == []
    assert narration.calls == []
    assert result.warnings[0].code is FailureCode.UNSUPPORTED_INTENT
    assert composer.calls[0].evidence == EvidenceBundle()


class _TimeoutThenRouter:
    def __init__(self, output: RouterOutput) -> None:
        self.output = output
        self.calls = 0

    async def route(self, request: RouterRequest) -> RouterOutput:
        del request
        self.calls += 1
        if self.calls == 1:
            await asyncio.sleep(1)
        return self.output


@_run_async_test
async def test_retryable_stage_timeout_retries_once_with_fresh_call() -> None:
    router = _TimeoutThenRouter(
        _router_output(
            intent=IntentKind.GENERAL_TRAVEL_HELP,
            plan=(),
        )
    )
    policy = OrchestrationPolicy(
        overall_timeout_seconds=1.0,
        router_timeout_seconds=0.01,
        discovery_timeout_seconds=0.1,
        specialist_timeout_seconds=0.1,
        grounding_timeout_seconds=0.1,
        composer_timeout_seconds=0.1,
        maximum_attempts=2,
    )
    result = await _orchestrator(
        router=router,
        policy=policy,
    ).run(_runtime_request())

    assert router.calls == 2
    assert result.final_output is not None
    assert result.status is RuntimeResultStatus.SUCCESS
    assert result.stages[0].duration_ms >= 0


@_run_async_test
async def test_retryable_typed_failure_retries_once_and_never_thrice() -> None:
    failure = AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PROVIDER_UNAVAILABLE,
        message="Nguồn dữ liệu hiện chưa sẵn sàng.",
        retryable=True,
    )
    discovery = _DiscoveryService(
        [
            DiscoveryExecutionError(failure),
            _discovery_output(),
            _discovery_output(),
        ]
    )
    router = _RouterService(
        _router_output(
            intent=IntentKind.NEARBY_DISCOVERY,
            plan=(SpecialistKind.DISCOVERY,),
        )
    )
    result = await _orchestrator(
        router=router,
        discovery=discovery,
    ).run(_runtime_request())

    assert len(discovery.calls) == 2
    discovery_stage = next(
        stage
        for stage in result.stages
        if stage.agent is AgentKind.DISCOVERY
    )
    assert discovery_stage.status is StageStatus.SUCCESS


class _AdvancingFailedDiscovery:
    def __init__(
        self,
        failure: AgentFailure,
        advance: Callable[[float], None],
    ) -> None:
        self.failure = failure
        self.advance = advance
        self.calls = 0

    async def discover(self, request: DiscoveryRequest) -> DiscoveryOutput:
        del request
        self.calls += 1
        self.advance(0.5)
        raise DiscoveryExecutionError(self.failure)


@_run_async_test
async def test_insufficient_remaining_budget_prevents_second_attempt() -> None:
    current = [10.0]

    def clock() -> float:
        return current[0]

    def advance(seconds: float) -> None:
        current[0] += seconds

    failure = AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PROVIDER_UNAVAILABLE,
        message="Nguồn dữ liệu hiện chưa sẵn sàng.",
        retryable=True,
    )
    discovery = _AdvancingFailedDiscovery(failure, advance)
    policy = OrchestrationPolicy(
        overall_timeout_seconds=1.0,
        router_timeout_seconds=0.1,
        discovery_timeout_seconds=0.6,
        specialist_timeout_seconds=0.1,
        grounding_timeout_seconds=0.1,
        composer_timeout_seconds=0.1,
        maximum_attempts=2,
    )
    result = await _orchestrator(
        router=_RouterService(
            _router_output(
                intent=IntentKind.NEARBY_DISCOVERY,
                plan=(SpecialistKind.DISCOVERY,),
            )
        ),
        discovery=discovery,
        policy=policy,
        clock=clock,
    ).run(_runtime_request())

    assert discovery.calls == 1
    discovery_stage = next(
        stage
        for stage in result.stages
        if stage.agent is AgentKind.DISCOVERY
    )
    assert discovery_stage.failure == failure


@_run_async_test
async def test_single_attempt_stage_timeout_maps_to_specialist_timeout() -> None:
    router = _TimeoutThenRouter(
        _router_output(
            intent=IntentKind.GENERAL_TRAVEL_HELP,
            plan=(),
        )
    )
    policy = OrchestrationPolicy(
        overall_timeout_seconds=1.0,
        router_timeout_seconds=0.01,
        discovery_timeout_seconds=0.1,
        specialist_timeout_seconds=0.1,
        grounding_timeout_seconds=0.1,
        composer_timeout_seconds=0.1,
        maximum_attempts=1,
    )
    result = await _orchestrator(
        router=router,
        policy=policy,
    ).run(_runtime_request())

    assert router.calls == 1
    assert result.status is RuntimeResultStatus.PARTIAL
    assert result.stages[0].failure is not None
    assert (
        result.stages[0].failure.code
        is FailureCode.SPECIALIST_TIMEOUT
    )


@_run_async_test
async def test_nonretryable_failure_and_limited_output_each_call_once() -> None:
    router = _RouterService(
        _router_output(
            intent=IntentKind.POI_INFORMATION,
            plan=(SpecialistKind.NARRATION,),
        )
    )
    failed = _NarrationService(RuntimeError("private"))
    failed_result = await _orchestrator(
        router=router,
        narration=failed,
    ).run(_runtime_request())
    assert len(failed.calls) == 1
    assert failed_result.status is RuntimeResultStatus.PARTIAL

    limited = _NarrationService(_limited_narration())
    limited_result = await _orchestrator(
        router=router,
        narration=limited,
    ).run(_runtime_request())
    assert len(limited.calls) == 1
    assert limited_result.status is RuntimeResultStatus.PARTIAL
    assert limited_result.warnings[0].code is FailureCode.INSUFFICIENT_EVIDENCE


class _BlockingSpecialist:
    def __init__(self, started: asyncio.Event) -> None:
        self.started = started
        self.cancelled = False
        self.calls = 0

    async def wait(self) -> None:
        self.calls += 1
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class _BlockingNarration(_BlockingSpecialist):
    async def narrate(self, request: NarrationRequest) -> NarrationOutput:
        del request
        await self.wait()
        raise AssertionError("Blocking narration unexpectedly completed.")


class _BlockingCulture(_BlockingSpecialist):
    async def advise(
        self,
        request: LocalCultureRequest,
    ) -> LocalCultureOutput:
        del request
        await self.wait()
        raise AssertionError("Blocking culture unexpectedly completed.")


class _BlockingItinerary(_BlockingSpecialist):
    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        del request
        await self.wait()
        raise AssertionError("Blocking itinerary unexpectedly completed.")


@_run_async_test
async def test_caller_cancellation_cancels_all_siblings_and_propagates() -> None:
    narration_started = asyncio.Event()
    culture_started = asyncio.Event()
    itinerary_started = asyncio.Event()
    narration = _BlockingNarration(narration_started)
    culture = _BlockingCulture(culture_started)
    itinerary = _BlockingItinerary(itinerary_started)
    grounding = _GroundingService()
    composer = _ComposerService()
    task = asyncio.create_task(
        _orchestrator(
            router=_RouterService(_all_router_output()),
            narration=narration,
            culture=culture,
            itinerary=itinerary,
            grounding=grounding,
            composer=composer,
        ).run(_runtime_request())
    )
    await asyncio.gather(
        narration_started.wait(),
        culture_started.wait(),
        itinerary_started.wait(),
    )

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert narration.cancelled
    assert culture.cancelled
    assert itinerary.cancelled
    assert grounding.calls == []
    assert composer.calls == []


class _SlowNarration:
    def __init__(self) -> None:
        self.cancelled = False

    async def narrate(self, request: NarrationRequest) -> NarrationOutput:
        del request
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return _narration_output()


@_run_async_test
async def test_overall_deadline_retains_completed_sibling_and_stops_new_stages() -> None:
    router_output = _router_output(
        intent=IntentKind.POI_INFORMATION,
        plan=(
            SpecialistKind.NARRATION,
            SpecialistKind.LOCAL_CULTURE,
        ),
    )
    slow = _SlowNarration()
    grounding = _GroundingService()
    composer = _ComposerService()
    policy = OrchestrationPolicy(
        overall_timeout_seconds=0.03,
        router_timeout_seconds=0.01,
        discovery_timeout_seconds=0.01,
        specialist_timeout_seconds=1.0,
        grounding_timeout_seconds=0.01,
        composer_timeout_seconds=0.01,
        maximum_attempts=1,
    )
    candidate = _candidate()
    result = await _orchestrator(
        router=_RouterService(router_output),
        narration=slow,
        culture=_CultureService(_culture_output()),
        grounding=grounding,
        composer=composer,
        policy=policy,
    ).run(
        _runtime_request(
            context=AgentRuntimeContext(
                selected_poi=PoiIdentity(
                    poi_id=candidate.id,
                    canonical_name=candidate.canonical_name,
                    city=candidate.city,
                    category=candidate.category,
                ),
                evidence=_evidence(),
                candidates=(candidate,),
            )
        )
    )

    assert result.status is RuntimeResultStatus.FAILED
    culture_stage = next(
        stage
        for stage in result.stages
        if stage.agent is AgentKind.LOCAL_CULTURE
    )
    narration_stage = next(
        stage
        for stage in result.stages
        if stage.agent is AgentKind.NARRATION
    )
    assert culture_stage.status is StageStatus.SUCCESS
    assert culture_stage.output == _culture_output()
    assert narration_stage.status is StageStatus.FAILED
    assert narration_stage.failure is not None
    assert (
        narration_stage.failure.code
        is FailureCode.LATENCY_BUDGET_EXCEEDED
    )
    assert slow.cancelled
    assert grounding.calls == []
    assert composer.calls == []


class _AdvancingRouter:
    def __init__(
        self,
        output: RouterOutput,
        advance: Callable[[float], None],
    ) -> None:
        self.output = output
        self.advance = advance
        self.calls = 0

    async def route(self, request: RouterRequest) -> RouterOutput:
        del request
        self.calls += 1
        self.advance(2.0)
        return self.output


@_run_async_test
async def test_injected_monotonic_clock_enforces_budget_without_wall_clock() -> None:
    current = [100.0]

    def clock() -> float:
        return current[0]

    def advance(seconds: float) -> None:
        current[0] += seconds

    router = _AdvancingRouter(
        _router_output(
            intent=IntentKind.GENERAL_TRAVEL_HELP,
            plan=(),
        ),
        advance,
    )
    grounding = _GroundingService()
    composer = _ComposerService()
    policy = OrchestrationPolicy(
        overall_timeout_seconds=1.0,
        router_timeout_seconds=0.5,
        discovery_timeout_seconds=0.5,
        specialist_timeout_seconds=0.5,
        grounding_timeout_seconds=0.5,
        composer_timeout_seconds=0.5,
        maximum_attempts=1,
    )
    result = await _orchestrator(
        router=router,
        grounding=grounding,
        composer=composer,
        policy=policy,
        clock=clock,
    ).run(_runtime_request())

    assert result.status is RuntimeResultStatus.FAILED
    assert result.final_output is None
    assert all(
        stage.failure is not None
        and stage.failure.code is FailureCode.LATENCY_BUDGET_EXCEEDED
        for stage in result.stages
    )
    assert all(stage.duration_ms >= 0 for stage in result.stages)
    assert grounding.calls == []
    assert composer.calls == []


@_run_async_test
async def test_router_failure_can_reach_safe_evidence_free_composer() -> None:
    composer = _ComposerService()
    result = await _orchestrator(
        router=_RouterService(RuntimeError("private routing failure")),
        composer=composer,
    ).run(_runtime_request(context=AgentRuntimeContext()))

    assert result.status is RuntimeResultStatus.PARTIAL
    assert result.final_output is not None
    assert result.failures[0].stage is AgentKind.ROUTER
    assert composer.calls[0].evidence == EvidenceBundle()
    assert composer.calls[0].approved_specialist_outputs == ()
    assert "private routing failure" not in result.model_dump_json()


@_run_async_test
async def test_grounding_failure_passes_no_unreviewed_facts_to_composer() -> None:
    composer = _ComposerService()
    result = await _orchestrator(
        router=_RouterService(
            _router_output(
                intent=IntentKind.GENERAL_TRAVEL_HELP,
                plan=(),
            )
        ),
        grounding=_GroundingService(
            failure=RuntimeError("private review failure")
        ),
        composer=composer,
    ).run(
        _runtime_request(
            context=AgentRuntimeContext(evidence=_evidence())
        )
    )

    assert result.status is RuntimeResultStatus.PARTIAL
    assert result.final_output is not None
    assert composer.calls[0].evidence == EvidenceBundle()
    assert composer.calls[0].approved_claim_ids == ()
    assert composer.calls[0].approved_specialist_outputs == ()
    assert "private review failure" not in result.model_dump_json()


@_run_async_test
async def test_grounding_rejection_removes_conflicting_claim_and_wrapper() -> None:
    conflicting = EvidenceBundle(
        sources=(_source(),),
        claims=(
            _claim(
                "claim-history",
                FactKind.HISTORY,
                "Nội dung xung đột.",
            ),
        ),
    )
    composer = _ComposerService()
    result = await _orchestrator(
        router=_RouterService(
            _router_output(
                intent=IntentKind.NEARBY_DISCOVERY,
                plan=(SpecialistKind.DISCOVERY,),
            )
        ),
        composer=composer,
    ).run(
        _runtime_request(
            context=AgentRuntimeContext(evidence=conflicting)
        )
    )

    grounding_stage = next(
        stage
        for stage in result.stages
        if stage.agent is AgentKind.GROUNDING_REVIEWER
    )
    assert grounding_stage.status is StageStatus.PARTIAL
    assert grounding_stage.warning is not None
    assert grounding_stage.warning.code is FailureCode.GROUNDING_REJECTED
    assert "claim-history" not in composer.calls[0].approved_claim_ids
    assert composer.calls[0].approved_specialist_outputs == ()
    assert result.final_output is not None
    assert result.final_output.warnings == result.warnings


@_run_async_test
async def test_composer_failure_makes_runtime_failed_with_no_final_output() -> None:
    result = await _orchestrator(
        router=_RouterService(
            _router_output(
                intent=IntentKind.GENERAL_TRAVEL_HELP,
                plan=(),
            )
        ),
        composer=_ComposerService(
            failure=RuntimeError("private composition failure")
        ),
    ).run(_runtime_request(context=AgentRuntimeContext()))

    assert result.status is RuntimeResultStatus.FAILED
    assert result.final_output is None
    assert result.failures[-1].stage is AgentKind.RESPONSE_COMPOSER
    assert "private composition failure" not in result.model_dump_json()


@_run_async_test
async def test_context_price_reaches_composer_unchanged_after_review() -> None:
    price = PriceFact(
        price_minor_units=75_000,
        currency="VND",
        source_updated_at=NOW,
    )
    evidence = EvidenceBundle(
        sources=(_source(),),
        claims=(
            _claim(
                "claim-price",
                FactKind.PRICE,
                "Giá niêm yết là 75.000 đồng.",
                price=price,
            ),
        ),
    )
    composer = _ComposerService()
    result = await _orchestrator(
        router=_RouterService(
            _router_output(
                intent=IntentKind.GENERAL_TRAVEL_HELP,
                plan=(),
            )
        ),
        composer=composer,
    ).run(
        _runtime_request(
            context=AgentRuntimeContext(evidence=evidence)
        )
    )

    assert result.status is RuntimeResultStatus.SUCCESS
    approved = composer.calls[0].evidence.claims[0]
    assert approved.price == price
    assert approved.statement == "Giá niêm yết là 75.000 đồng."
    assert approved.freshness_at == NOW


def test_approved_evidence_conversion_rejects_claim_and_source_conflicts() -> None:
    claim = _claim(
        "claim-history",
        FactKind.HISTORY,
        "Thông tin thứ nhất.",
    )
    conflicting_claim = GroundingCandidateClaim.from_approved(
        claim.model_copy(update={"statement": "Thông tin thứ hai."})
    )
    review = GroundingReviewOutput(
        status=GroundingReviewStatus.APPROVED,
        reviewed_claim_ids=("claim-history",),
        approved_claim_ids=("claim-history",),
        rejected_claims=(),
        approved_specialist_output_ids=(),
        warnings=(),
    )
    with pytest.raises(ValueError, match="claim identity"):
        build_approved_evidence(
            GroundingCandidateEvidence(
                sources=(_source(),),
                claims=(
                    GroundingCandidateClaim.from_approved(claim),
                    conflicting_claim,
                ),
            ),
            review,
        )
    with pytest.raises(ValueError, match="source identity"):
        build_approved_evidence(
            GroundingCandidateEvidence(
                sources=(
                    _source(),
                    _source(label="Nguồn xung đột"),
                ),
                claims=(GroundingCandidateClaim.from_approved(claim),),
            ),
            review,
        )


def test_policy_is_strict_bounded_and_has_no_current_time_default() -> None:
    policy = OrchestrationPolicy()
    assert policy.maximum_attempts == 2
    assert policy.discovery_radius_metres == 5_000
    assert policy.discovery_limit == 5
    with pytest.raises(ValidationError):
        OrchestrationPolicy.model_validate({"maximum_attempts": 3})
    with pytest.raises(ValidationError):
        OrchestrationPolicy(overall_timeout_seconds=float("inf"))
    assert not any(
        field in OrchestrationPolicy.model_fields
        for field in ("date", "time", "as_of")
    )


def test_orchestration_package_has_no_direct_sdk_or_transport_dependency() -> None:
    import app.agents.orchestration.evidence as evidence_module
    import app.agents.orchestration.execution as execution_module
    import app.agents.orchestration.policy as policy_module
    import app.agents.orchestration.requests as requests_module
    import app.agents.orchestration.service as service_module

    source = "\n".join(
        inspect.getsource(module)
        for module in (
            evidence_module,
            execution_module,
            policy_module,
            requests_module,
            service_module,
        )
    )
    forbidden = (
        "Runner.run",
        "FastAPI",
        "APIRouter",
        "app.providers",
        "sqlalchemy",
        "firebase",
        "trace_id",
        "token_usage",
        "datetime.now",
        "asyncio.sleep",
    )
    assert not any(term in source for term in forbidden)
    assert "openai-agents==0.18.3" in (
        BACKEND / "requirements.txt"
    ).read_text()
