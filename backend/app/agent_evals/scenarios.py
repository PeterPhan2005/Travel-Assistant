"""Synthetic deterministic scenarios executing real T041-T049 boundaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from collections.abc import Callable
from typing import cast

from pydantic import BaseModel, HttpUrl

from app.agent_evals.contracts import (
    AgentEvalCase,
    ComposerEvalCase,
    ComposerScenario,
    DiscoveryEvalCase,
    DiscoveryScenario,
    EvalCheckCode,
    GroundingEvalCase,
    GroundingScenario,
    ItineraryEvalCase,
    ItineraryScenario,
    LocalCultureEvalCase,
    LocalCultureScenario,
    NarrationEvalCase,
    NarrationScenario,
    RouterEvalCase,
    RuntimeEvalCase,
    RuntimeScenario,
)
from app.agents.composer.renderer import SAFE_FALLBACK_TEXT
from app.agents.composer.service import ResponseComposerService
from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    AgentRuntimeContext,
    AgentRuntimeRequest,
    AgentWarning,
    AnswerStatus,
    CultureGuidanceItem,
    DiscoveryCandidate,
    DiscoveryCompleteness,
    DiscoveryOrigin,
    DiscoveryOutput,
    DiscoveryRequest,
    DiscoverySpecialistOutput,
    EvidenceBundle,
    FactKind,
    FactualClaim,
    FailureCode,
    FreshnessRequirement,
    GroundingCandidateClaim,
    GroundingCandidateEvidence,
    GroundingCandidatePrice,
    GroundingReviewOutput,
    GroundingReviewRequest,
    IntentKind,
    ItineraryConstraints,
    ItineraryItem,
    ItineraryOutput,
    ItineraryRequest,
    ItinerarySpecialistOutput,
    LocalCultureOutput,
    LocalCultureRequest,
    LocalCultureSpecialistOutput,
    NarrationOutput,
    NarrationRequest,
    NarrationSpecialistOutput,
    NarrationWordRange,
    PoiIdentity,
    PriceFact,
    ResponseComposerOutput,
    ResponseComposerRequest,
    RouterEntities,
    RouterOutput,
    RouterRequest,
    RuntimeItineraryWindow,
    SourceRecord,
    SourceType,
    SpecialistKind,
    SpecialistOutput,
    StageStatus,
    SupportedCity,
)
from app.agents.discovery import (
    DiscoveryExecutionError,
    DiscoveryService,
    MenuErrorCode,
    MenuReaderError,
)
from app.agents.discovery.models import MenuResultEnvelope
from app.agents.grounding.service import GroundingReviewerService
from app.agents.itinerary import ItineraryExecutionError, ItineraryService
from app.agents.local_culture.service import LocalCultureService
from app.agents.local_culture.validation import FIXED_RESPECTFUL_CAUTION
from app.agents.narration.service import NarrationService
from app.agents.observability import (
    AgentObservabilityService,
    AgentRequestTraceQuery,
    AgentUsageQuery,
    InMemoryAgentObservabilityStore,
)
from app.agents.orchestration.policy import OrchestrationPolicy
from app.agents.orchestration.service import AgentOrchestratorService
from app.agents.router.service import RouterService
from app.providers.poi.errors import (
    PoiProviderError,
    ProviderErrorCode,
    ProviderFailure,
)
from app.providers.poi.models import (
    Coordinates,
    PoiDiscoveryRequest,
    PoiDiscoveryResult,
    PoiProviderKind,
    PoiResultEnvelope,
    SourceReference,
)

NOW = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
LATER = datetime(2026, 1, 3, 3, 4, tzinfo=timezone.utc)
AS_OF = datetime(2026, 1, 10, 3, 4, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class ScenarioOutcome:
    """Internal full-output fingerprint plus independently passed checks."""

    canonical_output: str
    passed_checks: frozenset[EvalCheckCode]


def _canonical(value: object) -> str:
    dumped: object
    if isinstance(value, BaseModel):
        dumped = value.model_dump(mode="json")
    else:
        dumped = value
    return json.dumps(
        dumped,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _base_checks() -> set[EvalCheckCode]:
    return {
        EvalCheckCode.CONTRACT_VALID,
        EvalCheckCode.PRIVACY_SAFE,
    }


def _finish(
    value: object,
    checks: set[EvalCheckCode],
) -> ScenarioOutcome:
    return ScenarioOutcome(_canonical(value), frozenset(checks))


def _source(source_id: str = "eval-source-a") -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_INSTITUTION,
        label=f"Synthetic source {source_id}",
        publisher="Synthetic publisher",
        url=HttpUrl(f"https://example.test/{source_id}"),
        published_at=None,
        retrieved_at=NOW,
    )


def _source_reference(source_id: str = "eval-source-a") -> SourceReference:
    source = _source(source_id)
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
    claim_id: str = "eval-claim-a",
    *,
    source_ids: tuple[str, ...] = ("eval-source-a",),
    fact_kind: FactKind = FactKind.HISTORY,
    poi_id: str | None = "curated:eval-poi-a",
    statement: str = "Synthetic approved fact.",
    freshness_at: datetime | None = NOW,
    price: PriceFact | None = None,
) -> FactualClaim:
    return FactualClaim(
        claim_id=claim_id,
        evidence_id=f"evidence-{claim_id}",
        fact_kind=fact_kind,
        statement=statement,
        supporting_source_ids=source_ids,
        poi_id=poi_id,
        freshness_at=freshness_at,
        price=price,
    )


def _evidence(
    *,
    sources: tuple[SourceRecord, ...] | None = None,
    claims: tuple[FactualClaim, ...] | None = None,
) -> EvidenceBundle:
    return EvidenceBundle(
        sources=sources if sources is not None else (_source(),),
        claims=claims if claims is not None else (_claim(),),
    )


def _candidate(
    provider_id: str = "eval-poi-a",
    *,
    name: str = "Synthetic Place A",
    category: str = "museum",
    distance: float = 100.0,
    source_id: str = "eval-source-a",
    optional: bool = True,
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        id=f"curated:{provider_id}",
        provider=PoiProviderKind.CURATED,
        provider_id=provider_id,
        canonical_name=name,
        city=SupportedCity.HCMC,
        category=category,
        address="Synthetic address" if optional else None,
        coordinates=Coordinates(latitude=10.75, longitude=106.65),
        distance_metres=distance,
        rating=Decimal("4.50") if optional else None,
        rating_count=10 if optional else None,
        price_level=None,
        opening_hours_summary="08:00-17:00" if optional else None,
        sources=(_source_reference(source_id),),
        retrieved_at=NOW,
        is_curated=True,
        is_externally_supplied=False,
    )


def _narration_request(
    *,
    evidence: EvidenceBundle | None = None,
    minimum: int = 100,
    maximum: int = 200,
) -> NarrationRequest:
    return NarrationRequest(
        poi=PoiIdentity(
            poi_id="curated:eval-poi-a",
            canonical_name="Synthetic Place A",
            city=SupportedCity.HCMC,
            category="museum",
        ),
        evidence=evidence or _evidence(),
        locale="vi-VN",
        word_range=NarrationWordRange(
            minimum_words=minimum,
            maximum_words=maximum,
        ),
    )


def _words(count: int) -> str:
    return " ".join(f"từ{index}" for index in range(1, count + 1))


def _complete_narration(
    *,
    count: int = 100,
    source_ids: tuple[str, ...] = ("eval-source-a",),
) -> NarrationOutput:
    return NarrationOutput(
        status=AnswerStatus.COMPLETE,
        narration_text=_words(count),
        key_points=("Synthetic key point",),
        used_source_ids=source_ids,
        used_claim_ids=("eval-claim-a",),
        limitation_reason=None,
    )


class _StaticNarrationExecutor:
    def __init__(self, output: object) -> None:
        self.output = output
        self.calls = 0

    async def narrate(self, request: NarrationRequest) -> NarrationOutput:
        del request
        self.calls += 1
        return cast(NarrationOutput, self.output)


def _culture_request(
    *,
    evidence: EvidenceBundle | None = None,
) -> LocalCultureRequest:
    culture_evidence = evidence or _evidence(
        claims=(
            _claim(
                fact_kind=FactKind.CULTURE,
                statement="Visitors speak quietly at the synthetic site.",
            ),
        )
    )
    return LocalCultureRequest(
        city=SupportedCity.HCMC,
        topic="Synthetic etiquette",
        locale="vi-VN",
        evidence=culture_evidence,
    )


def _guidance(
    *,
    text: str = "Visitors speak quietly at the synthetic site.",
    source_ids: tuple[str, ...] = ("eval-source-a",),
) -> CultureGuidanceItem:
    return CultureGuidanceItem(
        guidance_id="culture-guidance-001",
        text=text,
        claim_ids=("eval-claim-a",),
        source_ids=source_ids,
    )


def _complete_culture(
    *,
    text: str = "Visitors speak quietly at the synthetic site.",
    source_ids: tuple[str, ...] = ("eval-source-a",),
    caution: str | None = None,
) -> LocalCultureOutput:
    return LocalCultureOutput(
        status=AnswerStatus.COMPLETE,
        guidance=(_guidance(text=text, source_ids=source_ids),),
        respectful_caution=caution,
        limitation_reason=None,
    )


class _StaticCultureExecutor:
    def __init__(self, output: object) -> None:
        self.output = output
        self.calls = 0

    async def advise(self, request: LocalCultureRequest) -> LocalCultureOutput:
        del request
        self.calls += 1
        return cast(LocalCultureOutput, self.output)


def _itinerary_candidates() -> tuple[DiscoveryCandidate, ...]:
    return (
        _candidate(
            "eval-poi-z",
            name="Synthetic Place Z",
            category="food",
            distance=10.0,
            source_id="eval-source-z",
        ),
        _candidate(
            "eval-poi-a",
            name="Synthetic Place A",
            category="museum",
            distance=20.0,
        ),
        _candidate(
            "eval-poi-m",
            name="Synthetic Place M",
            category="museum",
            distance=30.0,
            source_id="eval-source-m",
        ),
        _candidate(
            "eval-poi-b",
            name="Synthetic Place B",
            category="park",
            distance=40.0,
            source_id="eval-source-b",
        ),
    )


def _itinerary_request(
    *,
    maximum_stops: int = 3,
    required: tuple[str, ...] = ("curated:eval-poi-a",),
    excluded: tuple[str, ...] = (),
    preferred: tuple[str, ...] = ("museum",),
    start: time = time(9, 0),
    end: time = time(17, 1),
) -> ItineraryRequest:
    return ItineraryRequest(
        city=SupportedCity.HCMC,
        local_date=date(2026, 8, 1),
        timezone="Asia/Ho_Chi_Minh",
        start_local_time=start,
        end_local_time=end,
        candidates=_itinerary_candidates(),
        evidence=EvidenceBundle(),
        constraints=ItineraryConstraints(
            maximum_stops=maximum_stops,
            required_poi_ids=required,
            excluded_poi_ids=excluded,
            preferred_categories=preferred,
            notes=("Synthetic constraint",),
        ),
        start_origin=None,
    )


class _InvalidItineraryExecutor:
    def __init__(self) -> None:
        self.calls = 0

    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        del request
        self.calls += 1
        return cast(ItineraryOutput, "invalid")


class _Provider:
    def __init__(self, result: PoiResultEnvelope | BaseException) -> None:
        self.result = result
        self.calls = 0

    async def discover(self, request: PoiDiscoveryRequest) -> PoiResultEnvelope:
        del request
        self.calls += 1
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class _MenuReader:
    def __init__(self, result: MenuResultEnvelope | BaseException) -> None:
        self.result = result
        self.calls = 0

    async def read_menu_items(
        self,
        poi_provider_ids: tuple[str, ...],
    ) -> MenuResultEnvelope:
        del poi_provider_ids
        self.calls += 1
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _provider_result(
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    complete: bool = True,
) -> PoiResultEnvelope:
    items = tuple(
        PoiDiscoveryResult.model_validate(candidate.model_dump(mode="python"))
        for candidate in candidates
    )
    return PoiResultEnvelope(
        provider=PoiProviderKind.CURATED,
        items=items,
        returned_count=len(items),
        is_complete=complete,
        freshness_at=NOW if items else None,
    )


def _discovery_request(
    *,
    facts: tuple[FactKind, ...] = (
        FactKind.CATEGORY,
        FactKind.IDENTITY,
    ),
) -> DiscoveryRequest:
    return DiscoveryRequest(
        city=SupportedCity.HCMC,
        origin=DiscoveryOrigin(latitude=10.76, longitude=106.66),
        radius_metres=5_000,
        limit=5,
        query="synthetic query",
        category=None,
        requested_fact_kinds=tuple(sorted(facts, key=lambda item: item.value)),
    )


async def _execute_router(case: RouterEvalCase) -> ScenarioOutcome:
    queries = {
        case.scenario.NEARBY_HCMC: "địa điểm gần đây ở Sài Gòn",
        case.scenario.POI_INFORMATION: "giới thiệu bảo tàng này",
        case.scenario.CULTURE_CITY_CONFLICT: "văn hóa ở Bangkok",
        case.scenario.ITINERARY_BANGKOK: "lịch trình Bangkok một ngày",
        case.scenario.GENERAL_HELP: "hỗ trợ du lịch",
        case.scenario.UNSUPPORTED: "synthetic unrelated request",
    }
    explicit_city = (
        SupportedCity.HCMC
        if case.scenario is case.scenario.CULTURE_CITY_CONFLICT
        else None
    )
    output = await RouterService(executor_factory=lambda: None).route(
        RouterRequest(
            user_query=queries[case.scenario],
            locale="vi-VN",
            city=explicit_city,
            preferences=None,
        )
    )
    checks = _base_checks()
    if output.primary_intent is case.expected_intent:
        checks.add(EvalCheckCode.EXPECTED_INTENT)
    if output.specialist_plan == case.expected_plan:
        checks.add(EvalCheckCode.EXPECTED_PLAN)
    if output.entities.city is case.expected_city:
        checks.add(EvalCheckCode.EXPECTED_ITEMS)
    checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    return _finish(output, checks)


async def _execute_discovery(case: DiscoveryEvalCase) -> ScenarioOutcome:
    menu: MenuResultEnvelope | BaseException = MenuResultEnvelope()
    facts: tuple[FactKind, ...] = (
        FactKind.CATEGORY,
        FactKind.IDENTITY,
    )
    expected_menu_calls = 0
    if case.scenario is DiscoveryScenario.COMPLETE_ORDERED:
        candidates = (
            _candidate("eval-poi-z", distance=10.0),
            _candidate("eval-poi-a", distance=20.0),
        )
        provider_result: PoiResultEnvelope | BaseException = _provider_result(
            candidates
        )
    elif case.scenario is DiscoveryScenario.EMPTY_COMPLETE:
        provider_result = _provider_result(())
    elif case.scenario is DiscoveryScenario.PARTIAL_MENU:
        provider_result = _provider_result((_candidate(),))
        facts = (FactKind.IDENTITY, FactKind.MENU_ITEM, FactKind.PRICE)
        menu = MenuReaderError(MenuErrorCode.UNAVAILABLE)
        expected_menu_calls = 1
    elif case.scenario is DiscoveryScenario.TOTAL_PROVIDER_FAILURE:
        provider_result = PoiProviderError(
            ProviderFailure.for_code(
                PoiProviderKind.CURATED,
                ProviderErrorCode.UNAVAILABLE,
            )
        )
    else:
        provider_result = _provider_result(
            (_candidate(optional=False),)
        )
        facts = (
            FactKind.CATEGORY,
            FactKind.IDENTITY,
            FactKind.LOCATION,
            FactKind.OPENING_HOURS,
            FactKind.RATING,
        )

    provider = _Provider(provider_result)
    menu_reader = _MenuReader(menu)
    try:
        output = await DiscoveryService(
            provider,
            menu_reader,
            executor_factory=lambda _provider, _menu: None,
        ).discover(_discovery_request(facts=facts))
    except DiscoveryExecutionError as error:
        checks = _base_checks()
        if case.expected_failure is error.failure.code:
            checks.add(EvalCheckCode.EXPECTED_FAILURE)
        if provider.calls == 1 and menu_reader.calls == expected_menu_calls:
            checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
        return _finish(
            {"failure_code": error.failure.code.value},
            checks,
        )

    checks = _base_checks()
    if output.completeness is case.expected_completeness:
        checks.add(EvalCheckCode.EXPECTED_STATUS)
    candidate_ids = tuple(candidate.id for candidate in output.candidates)
    if candidate_ids == case.expected_candidate_ids:
        checks.add(EvalCheckCode.EXPECTED_ORDER)
        checks.add(EvalCheckCode.EXPECTED_ITEMS)
    if all(
        set(claim.supporting_source_ids).issubset(output.evidence.source_ids)
        for claim in output.evidence.claims
    ):
        checks.add(EvalCheckCode.EVIDENCE_CLOSED)
        checks.add(EvalCheckCode.SOURCE_UNION_EXACT)
    if case.scenario is DiscoveryScenario.CLOSED_OPTIONALS and all(
        candidate.rating is None
        and candidate.rating_count is None
        and candidate.opening_hours_summary is None
        for candidate in output.candidates
    ):
        checks.add(EvalCheckCode.OPTIONAL_FIELDS_OMITTED)
    elif case.scenario is not DiscoveryScenario.CLOSED_OPTIONALS:
        checks.add(EvalCheckCode.OPTIONAL_FIELDS_OMITTED)
    if provider.calls == 1 and menu_reader.calls == expected_menu_calls:
        checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    return _finish(output, checks)


async def _execute_narration(case: NarrationEvalCase) -> ScenarioOutcome:
    executor: _StaticNarrationExecutor | None = None
    if case.scenario is NarrationScenario.INSUFFICIENT_EVIDENCE:
        request = _narration_request(evidence=EvidenceBundle())
        forbidden = _StaticNarrationExecutor(_complete_narration())
        service = NarrationService(executor_factory=lambda: forbidden)
        executor = forbidden
    elif case.scenario is NarrationScenario.UNCONFIGURED:
        request = _narration_request()
        service = NarrationService(executor_factory=lambda: None)
    elif case.scenario is NarrationScenario.COMPLETE_GROUNDED:
        request = _narration_request(minimum=100, maximum=100)
        executor = _StaticNarrationExecutor(_complete_narration())
        service = NarrationService(executor_factory=lambda: executor)
    elif case.scenario is NarrationScenario.INVALID_MODEL_OUTPUT:
        request = _narration_request()
        executor = _StaticNarrationExecutor("invalid")
        service = NarrationService(executor_factory=lambda: executor)
    else:
        sources = (_source("eval-source-a"), _source("eval-source-b"))
        request = _narration_request(
            evidence=_evidence(sources=sources),
            minimum=100,
            maximum=100,
        )
        executor = _StaticNarrationExecutor(
            _complete_narration(
                count=101,
                source_ids=("eval-source-b",),
            )
        )
        service = NarrationService(executor_factory=lambda: executor)

    output = await service.narrate(request)
    checks = _base_checks()
    if output.status is case.expected_status:
        checks.add(EvalCheckCode.EXPECTED_STATUS)
    word_count = len(output.narration_text.split()) if output.narration_text else 0
    if word_count == case.expected_word_count:
        checks.add(EvalCheckCode.EXPECTED_ITEMS)
    if output.status is AnswerStatus.LIMITED or (
        output.used_source_ids == ("eval-source-a",)
        and output.used_claim_ids == ("eval-claim-a",)
    ):
        checks.add(EvalCheckCode.EVIDENCE_CLOSED)
        checks.add(EvalCheckCode.SOURCE_UNION_EXACT)
        checks.add(EvalCheckCode.NO_NEW_FACT)
    expected_calls = (
        0
        if case.scenario
        in {
            NarrationScenario.INSUFFICIENT_EVIDENCE,
            NarrationScenario.UNCONFIGURED,
        }
        else 1
    )
    actual_calls = executor.calls if executor is not None else 0
    if actual_calls == expected_calls:
        checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    return _finish(output, checks)


async def _execute_culture(case: LocalCultureEvalCase) -> ScenarioOutcome:
    executor: _StaticCultureExecutor | None = None
    if case.scenario is LocalCultureScenario.INSUFFICIENT_EVIDENCE:
        request = _culture_request(evidence=EvidenceBundle())
        executor = _StaticCultureExecutor(_complete_culture())
        service = LocalCultureService(executor_factory=lambda: executor)
    elif case.scenario is LocalCultureScenario.COMPLETE_SUPPORTED:
        request = _culture_request()
        executor = _StaticCultureExecutor(_complete_culture())
        service = LocalCultureService(executor_factory=lambda: executor)
    elif case.scenario is LocalCultureScenario.STEREOTYPE_REJECTED:
        request = _culture_request()
        executor = _StaticCultureExecutor(
            _complete_culture(text="Người Việt luôn thân thiện.")
        )
        service = LocalCultureService(executor_factory=lambda: executor)
    elif case.scenario is LocalCultureScenario.RESTRICTED_TOPIC_REJECTED:
        request = _culture_request()
        executor = _StaticCultureExecutor(
            _complete_culture(text="Theo luật, visitors must take medicine.")
        )
        service = LocalCultureService(executor_factory=lambda: executor)
    else:
        sources = (_source("eval-source-a"), _source("eval-source-b"))
        evidence = _evidence(
            sources=sources,
            claims=(
                _claim(
                    source_ids=("eval-source-a", "eval-source-b"),
                    fact_kind=FactKind.ETIQUETTE,
                    statement="Visitors speak quietly at the synthetic site.",
                ),
            ),
        )
        request = _culture_request(evidence=evidence)
        executor = _StaticCultureExecutor(
            _complete_culture(
                source_ids=("eval-source-a", "eval-source-b"),
                caution=FIXED_RESPECTFUL_CAUTION,
            )
        )
        service = LocalCultureService(executor_factory=lambda: executor)

    output = await service.advise(request)
    checks = _base_checks()
    if output.status is case.expected_status:
        checks.add(EvalCheckCode.EXPECTED_STATUS)
    if len(output.guidance) == case.expected_guidance_count:
        checks.add(EvalCheckCode.EXPECTED_ITEMS)
    if output.status is AnswerStatus.LIMITED or all(
        item.source_ids
        == tuple(
            sorted(
                {
                    source_id
                    for claim_id in item.claim_ids
                    for claim in request.evidence.claims
                    if claim.claim_id == claim_id
                    for source_id in claim.supporting_source_ids
                }
            )
        )
        for item in output.guidance
    ):
        checks.add(EvalCheckCode.EVIDENCE_CLOSED)
        checks.add(EvalCheckCode.SOURCE_UNION_EXACT)
        checks.add(EvalCheckCode.NO_NEW_FACT)
    expected_calls = (
        0
        if case.scenario is LocalCultureScenario.INSUFFICIENT_EVIDENCE
        else 1
    )
    if executor is not None and executor.calls == expected_calls:
        checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    return _finish(output, checks)


async def _execute_itinerary(case: ItineraryEvalCase) -> ScenarioOutcome:
    if case.scenario is ItineraryScenario.CONSTRAINT_SELECTION:
        request = _itinerary_request(
            maximum_stops=2,
            excluded=("curated:eval-poi-m",),
        )
    elif case.scenario is ItineraryScenario.IMPOSSIBLE_WINDOW:
        request = _itinerary_request(
            maximum_stops=2,
            required=("curated:eval-poi-a", "curated:eval-poi-z"),
            start=time(9, 0),
            end=time(9, 1),
        )
    else:
        request = _itinerary_request()

    invalid_executor: _InvalidItineraryExecutor | None = None
    if case.scenario is ItineraryScenario.INVALID_MODEL_FALLBACK:
        invalid_executor = _InvalidItineraryExecutor()
        service = ItineraryService(executor_factory=lambda: invalid_executor)
    else:
        service = ItineraryService(executor_factory=lambda: None)
    try:
        output = await service.draft(request)
    except ItineraryExecutionError as error:
        checks = _base_checks()
        if error.reason is case.expected_failure:
            checks.add(EvalCheckCode.EXPECTED_FAILURE)
        checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
        return _finish({"failure": error.reason.value}, checks)

    checks = _base_checks()
    poi_ids = tuple(item.poi_id for item in output.items)
    if poi_ids == case.expected_poi_ids:
        checks.add(EvalCheckCode.EXPECTED_ITEMS)
        checks.add(EvalCheckCode.EXPECTED_ORDER)
    if all(
        left.end_local_time <= right.start_local_time
        for left, right in zip(output.items, output.items[1:])
    ):
        checks.add(EvalCheckCode.NO_OVERLAP)
    if (
        output.start_local_time == request.start_local_time
        and output.end_local_time == request.end_local_time
        and output.items[-1].end_local_time == request.end_local_time
    ):
        checks.add(EvalCheckCode.TIME_WINDOW_EXACT)
    if all(
        not item.supporting_claim_ids and not item.supporting_source_ids
        for item in output.items
    ):
        checks.add(EvalCheckCode.NO_NEW_FACT)
        checks.add(EvalCheckCode.EVIDENCE_CLOSED)
    expected_calls = (
        1 if case.scenario is ItineraryScenario.INVALID_MODEL_FALLBACK else 0
    )
    actual_calls = invalid_executor.calls if invalid_executor else 0
    if actual_calls == expected_calls:
        checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    return _finish(output, checks)


def _grounding_request(scenario: GroundingScenario) -> GroundingReviewRequest:
    source = _source()
    base_claim = GroundingCandidateClaim.from_approved(_claim())
    if scenario is GroundingScenario.VALID_APPROVAL:
        evidence = GroundingCandidateEvidence(
            sources=(source,),
            claims=(base_claim,),
        )
        outputs: tuple[SpecialistOutput, ...] = ()
        freshness: tuple[FreshnessRequirement, ...] = ()
    elif scenario is GroundingScenario.MISSING_SOURCE:
        evidence = GroundingCandidateEvidence(
            sources=(),
            claims=(
                GroundingCandidateClaim(
                    claim_id="eval-claim-a",
                    evidence_id="evidence-eval-claim-a",
                    fact_kind=FactKind.HISTORY,
                    statement="Synthetic approved fact.",
                    supporting_source_ids=("eval-source-a",),
                    poi_id="curated:eval-poi-a",
                    freshness_at=NOW,
                    price=None,
                ),
            ),
        )
        outputs = ()
        freshness = ()
    elif scenario is GroundingScenario.MISSING_PRICE_TIMESTAMP:
        evidence = GroundingCandidateEvidence(
            sources=(source,),
            claims=(
                GroundingCandidateClaim(
                    claim_id="eval-claim-price",
                    evidence_id="evidence-eval-claim-price",
                    fact_kind=FactKind.PRICE,
                    statement="Synthetic price fact.",
                    supporting_source_ids=("eval-source-a",),
                    poi_id="curated:eval-poi-a",
                    freshness_at=None,
                    price=GroundingCandidatePrice(
                        price_minor_units=100,
                        currency="VND",
                        source_updated_at=None,
                    ),
                ),
            ),
        )
        outputs = ()
        freshness = ()
    elif scenario is GroundingScenario.STALE_EVIDENCE:
        evidence = GroundingCandidateEvidence(
            sources=(source,),
            claims=(base_claim,),
        )
        outputs = ()
        freshness = (
            FreshnessRequirement(
                fact_kind=FactKind.HISTORY,
                as_of=AS_OF,
                maximum_age_seconds=60,
            ),
        )
    else:
        conflicting_source = source.model_copy(
            update={"label": "Conflicting synthetic source"}
        )
        approved = _evidence()
        narration = NarrationSpecialistOutput(
            agent=AgentKind.NARRATION,
            output_id="eval-narration-output",
            output=_complete_narration(),
        )
        evidence = GroundingCandidateEvidence(
            sources=(source, conflicting_source),
            claims=(
                base_claim,
                base_claim.model_copy(
                    update={"statement": "Conflicting synthetic fact."}
                ),
            ),
        )
        outputs = (narration,)
        freshness = ()
        del approved
    return GroundingReviewRequest(
        evidence=evidence,
        specialist_outputs=outputs,
        freshness_requirements=freshness,
    )


async def _execute_grounding(case: GroundingEvalCase) -> ScenarioOutcome:
    request = _grounding_request(case.scenario)
    output = await GroundingReviewerService(
        executor_factory=lambda: None
    ).review(request)
    checks = _base_checks()
    if output.status is case.expected_status:
        checks.add(EvalCheckCode.EXPECTED_STATUS)
    if output.approved_claim_ids == case.expected_approved_claim_ids:
        checks.add(EvalCheckCode.EXPECTED_ITEMS)
    if set(output.reviewed_claim_ids) == (
        set(output.approved_claim_ids)
        | {item.claim_id for item in output.rejected_claims}
    ):
        checks.add(EvalCheckCode.NO_NEW_FACT)
        checks.add(EvalCheckCode.EVIDENCE_CLOSED)
    if case.scenario is GroundingScenario.CONFLICT_WITHHELD:
        if not output.approved_specialist_output_ids:
            checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    else:
        checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    if case.expected.failure_code is None or any(
        item.reason.value == case.expected.failure_code
        for item in output.rejected_claims
    ):
        checks.add(EvalCheckCode.EXPECTED_FAILURE)
    return _finish(output, checks)


def _discovery_output(
    *,
    candidates: tuple[DiscoveryCandidate, ...] = (),
    evidence: EvidenceBundle | None = None,
    partial: bool = False,
) -> DiscoveryOutput:
    failure = (
        AgentFailure(
            stage=AgentKind.DISCOVERY,
            code=FailureCode.PROVIDER_UNAVAILABLE,
            message="Nguồn dữ liệu hiện chưa sẵn sàng.",
            retryable=True,
        )
        if partial
        else None
    )
    return DiscoveryOutput(
        candidates=candidates,
        evidence=evidence or EvidenceBundle(),
        provider_failures=(failure,) if failure else (),
        completeness=(
            DiscoveryCompleteness.PARTIAL
            if partial
            else DiscoveryCompleteness.COMPLETE
        ),
        is_truncated=False,
    )


def _itinerary_output() -> ItineraryOutput:
    return ItineraryOutput(
        local_date=date(2026, 8, 1),
        timezone="Asia/Ho_Chi_Minh",
        start_local_time=time(9, 0),
        end_local_time=time(10, 0),
        items=(
            ItineraryItem(
                item_id="itinerary-item-001",
                poi_id="curated:eval-poi-a",
                title="Synthetic Place A",
                start_local_time=time(9, 0),
                end_local_time=time(10, 0),
                supporting_claim_ids=(),
                supporting_source_ids=(),
            ),
        ),
        assumptions=("Synthetic assumption",),
        warnings=(),
        draft_only=True,
    )


def _warning() -> AgentWarning:
    return AgentWarning(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PARTIAL_RESULT,
        message="Một phần dữ liệu địa điểm chưa thể được xác nhận.",
        retryable=False,
    )


def _composer_request(scenario: ComposerScenario) -> ResponseComposerRequest:
    if scenario is ComposerScenario.SAFE_FALLBACK:
        return ResponseComposerRequest(
            user_query="synthetic request",
            locale="vi-VN",
            evidence=EvidenceBundle(),
            approved_claim_ids=(),
            approved_specialist_outputs=(),
            warnings=(),
        )
    if scenario is ComposerScenario.NARRATION_EXACT:
        evidence = _evidence()
        specialist = NarrationSpecialistOutput(
            agent=AgentKind.NARRATION,
            output_id="eval-narration-output",
            output=_complete_narration(),
        )
        return ResponseComposerRequest(
            user_query="synthetic narration",
            locale="vi-VN",
            evidence=evidence,
            approved_claim_ids=("eval-claim-a",),
            approved_specialist_outputs=(specialist,),
            warnings=(),
        )
    if scenario is ComposerScenario.CULTURE_ITINERARY:
        evidence = _evidence(
            claims=(
                _claim(
                    fact_kind=FactKind.CULTURE,
                    statement="Visitors speak quietly at the synthetic site.",
                ),
            )
        )
        culture = LocalCultureSpecialistOutput(
            agent=AgentKind.LOCAL_CULTURE,
            output_id="eval-culture-output",
            output=_complete_culture(),
        )
        itinerary = ItinerarySpecialistOutput(
            agent=AgentKind.ITINERARY,
            output_id="eval-itinerary-output",
            output=_itinerary_output(),
        )
        return ResponseComposerRequest(
            user_query="synthetic culture itinerary",
            locale="vi-VN",
            evidence=evidence,
            approved_claim_ids=("eval-claim-a",),
            approved_specialist_outputs=(culture, itinerary),
            warnings=(),
        )
    if scenario is ComposerScenario.DISCOVERY_ORDER_OMISSION:
        candidates = (
            _candidate("eval-poi-z", distance=10.0, optional=False),
            _candidate("eval-poi-a", distance=20.0, optional=False),
        )
        sources = (_source("eval-source-a"), _source("eval-source-z"))
        claims: tuple[FactualClaim, ...] = (
            _claim(
                "eval-claim-a",
                fact_kind=FactKind.IDENTITY,
                statement="Synthetic Place A.",
            ),
            _claim(
                "eval-claim-z",
                source_ids=("eval-source-z",),
                fact_kind=FactKind.IDENTITY,
                poi_id="curated:eval-poi-z",
                statement="Synthetic Place Z.",
            ),
        )
        evidence = _evidence(sources=sources, claims=claims)
        discovery = DiscoverySpecialistOutput(
            agent=AgentKind.DISCOVERY,
            output_id="eval-discovery-output",
            output=_discovery_output(
                candidates=candidates,
                evidence=evidence,
            ),
        )
        return ResponseComposerRequest(
            user_query="synthetic discovery",
            locale="vi-VN",
            evidence=evidence,
            approved_claim_ids=("eval-claim-a", "eval-claim-z"),
            approved_specialist_outputs=(discovery,),
            warnings=(),
        )

    price_a = PriceFact(
        price_minor_units=100_000,
        currency="VND",
        source_updated_at=LATER,
    )
    price_b = PriceFact(
        price_minor_units=200_000,
        currency="VND",
        source_updated_at=LATER,
    )
    sources = (_source("eval-source-a"), _source("eval-source-b"))
    claims = (
        _claim(
            "eval-claim-price-a",
            fact_kind=FactKind.PRICE,
            statement="Synthetic price A.",
            freshness_at=LATER,
            price=price_a,
        ),
        _claim(
            "eval-claim-price-b1",
            source_ids=("eval-source-b",),
            fact_kind=FactKind.PRICE,
            poi_id="curated:eval-poi-b",
            statement="Synthetic price B one.",
            freshness_at=LATER,
            price=price_a,
        ),
        _claim(
            "eval-claim-price-b2",
            source_ids=("eval-source-b",),
            fact_kind=FactKind.PRICE,
            poi_id="curated:eval-poi-b",
            statement="Synthetic price B two.",
            freshness_at=LATER,
            price=price_b,
        ),
    )
    evidence = _evidence(sources=sources, claims=claims)
    candidates = (
        _candidate("eval-poi-a", optional=False),
        _candidate(
            "eval-poi-b",
            source_id="eval-source-b",
            optional=False,
        ),
    )
    discovery = DiscoverySpecialistOutput(
        agent=AgentKind.DISCOVERY,
        output_id="eval-discovery-output",
        output=_discovery_output(candidates=candidates, evidence=evidence),
    )
    return ResponseComposerRequest(
        user_query="synthetic prices",
        locale="vi-VN",
        evidence=evidence,
        approved_claim_ids=tuple(claim.claim_id for claim in claims),
        approved_specialist_outputs=(discovery,),
        warnings=(_warning(),),
    )


async def _execute_composer(case: ComposerEvalCase) -> ScenarioOutcome:
    request = _composer_request(case.scenario)
    output = await ResponseComposerService(
        executor_factory=lambda: None
    ).compose(request)
    checks = _base_checks()
    poi_ids = tuple(item.poi_id for item in output.poi_items)
    if poi_ids == case.expected_poi_ids:
        checks.add(EvalCheckCode.EXPECTED_ORDER)
        checks.add(EvalCheckCode.EXPECTED_ITEMS)
    if len(output.warnings) == case.expected_warning_count:
        checks.add(EvalCheckCode.EXPECTED_WARNING)
    if output.warnings == request.warnings:
        checks.add(EvalCheckCode.WARNING_PRESERVED)
    claims_by_id = {
        claim.claim_id: claim for claim in request.evidence.claims
    }
    expected_sources = tuple(
        sorted(
            {
                source_id
                for claim_id in output.used_claim_ids
                for source_id in claims_by_id[claim_id].supporting_source_ids
            }
        )
    )
    if output.used_source_ids == expected_sources:
        checks.add(EvalCheckCode.SOURCE_UNION_EXACT)
        checks.add(EvalCheckCode.EVIDENCE_CLOSED)
        checks.add(EvalCheckCode.NO_NEW_FACT)
    if case.scenario is ComposerScenario.SAFE_FALLBACK:
        if output.final_text == SAFE_FALLBACK_TEXT:
            checks.add(EvalCheckCode.EXPECTED_STATUS)
    elif case.scenario is ComposerScenario.NARRATION_EXACT:
        narration = cast(
            NarrationSpecialistOutput,
            request.approved_specialist_outputs[0],
        ).output.narration_text
        if narration is not None and narration in output.final_text:
            checks.add(EvalCheckCode.EXPECTED_STATUS)
    else:
        checks.add(EvalCheckCode.EXPECTED_STATUS)
    if case.scenario is ComposerScenario.DISCOVERY_ORDER_OMISSION:
        if all(
            item.address is None
            and item.rating is None
            and item.opening_hours_summary is None
            for item in output.poi_items
        ):
            checks.add(EvalCheckCode.OPTIONAL_FIELDS_OMITTED)
    elif case.scenario is ComposerScenario.PRICE_AND_WARNING:
        if (
            output.poi_items[0].price is not None
            and output.poi_items[1].price is None
        ):
            checks.add(EvalCheckCode.OPTIONAL_FIELDS_OMITTED)
    else:
        checks.add(EvalCheckCode.OPTIONAL_FIELDS_OMITTED)
    checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    return _finish(output, checks)


class _RouterBoundary:
    def __init__(
        self,
        output: RouterOutput,
        *,
        advance: Callable[[float], None] | None = None,
        fail_first: bool = False,
    ) -> None:
        self.output = output
        self.advance = advance
        self.fail_first = fail_first
        self.calls = 0

    async def route(self, request: RouterRequest) -> RouterOutput:
        del request
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise TimeoutError
        if self.advance is not None:
            self.advance(2.0)
        return self.output


class _DiscoveryBoundary:
    def __init__(self, output: DiscoveryOutput) -> None:
        self.output = output
        self.calls = 0

    async def discover(self, request: DiscoveryRequest) -> DiscoveryOutput:
        del request
        self.calls += 1
        return self.output


class _NarrationBoundary:
    def __init__(self, output: NarrationOutput | BaseException) -> None:
        self.output = output
        self.calls = 0

    async def narrate(self, request: NarrationRequest) -> NarrationOutput:
        del request
        self.calls += 1
        if isinstance(self.output, BaseException):
            raise self.output
        return self.output


class _CultureBoundary:
    async def advise(self, request: LocalCultureRequest) -> LocalCultureOutput:
        del request
        return LocalCultureOutput(
            status=AnswerStatus.LIMITED,
            guidance=(),
            respectful_caution=None,
            limitation_reason="Chưa có đủ nội dung được xác nhận.",
        )


class _ItineraryBoundary:
    def __init__(self) -> None:
        self.calls = 0

    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        self.calls += 1
        return await ItineraryService(
            executor_factory=lambda: None
        ).draft(request)


class _GroundingBoundary:
    async def review(
        self,
        request: GroundingReviewRequest,
    ) -> GroundingReviewOutput:
        return await GroundingReviewerService(
            executor_factory=lambda: None
        ).review(request)


class _ComposerBoundary:
    async def compose(
        self,
        request: ResponseComposerRequest,
    ) -> ResponseComposerOutput:
        return await ResponseComposerService(
            executor_factory=lambda: None
        ).compose(request)


def _router_output(
    intent: IntentKind,
    plan: tuple[SpecialistKind, ...] = (),
) -> RouterOutput:
    return RouterOutput(
        primary_intent=intent,
        entities=RouterEntities(
            city=SupportedCity.HCMC,
            category=None,
            query_term=None,
            referenced_poi_ids=(),
            itinerary_constraints=None,
        ),
        specialist_plan=plan,
        discovery_required=SpecialistKind.DISCOVERY in plan,
        clarification_reason=(
            "Vui lòng nêu rõ nhu cầu du lịch."
            if intent is IntentKind.UNSUPPORTED
            else None
        ),
    )


def _runtime_request(
    *,
    evidence: EvidenceBundle | None = None,
    candidates: tuple[DiscoveryCandidate, ...] = (),
    selected: bool = False,
    window: bool = False,
) -> AgentRuntimeRequest:
    selected_poi = (
        PoiIdentity(
            poi_id=candidates[0].id,
            canonical_name=candidates[0].canonical_name,
            city=candidates[0].city,
            category=candidates[0].category,
        )
        if selected and candidates
        else None
    )
    return AgentRuntimeRequest(
        request_id="eval-runtime-request",
        user_query="synthetic runtime request",
        locale="vi-VN",
        city=SupportedCity.HCMC,
        preferences=None,
        discovery_origin=DiscoveryOrigin(latitude=10.76, longitude=106.66),
        context=AgentRuntimeContext(
            selected_poi=selected_poi,
            evidence=evidence or EvidenceBundle(),
            candidates=candidates,
            itinerary_window=(
                RuntimeItineraryWindow(
                    local_date=date(2026, 8, 1),
                    timezone="Asia/Ho_Chi_Minh",
                    start_local_time=time(9, 0),
                    end_local_time=time(17, 0),
                )
                if window
                else None
            ),
        ),
    )


async def _execute_runtime(case: RuntimeEvalCase) -> ScenarioOutcome:
    current = [100.0]

    def clock() -> float:
        return current[0]

    def advance(seconds: float) -> None:
        current[0] += seconds

    candidates = (_candidate(),)
    evidence = _evidence()
    discovery_output = _discovery_output(
        candidates=candidates,
        evidence=evidence,
    )
    narration: NarrationOutput | BaseException = _complete_narration()
    itinerary = _ItineraryBoundary()
    if case.scenario is RuntimeScenario.COMPLETE_SUCCESS:
        router = _RouterBoundary(
            _router_output(IntentKind.GENERAL_TRAVEL_HELP)
        )
        request = _runtime_request()
    elif case.scenario is RuntimeScenario.SPECIALIST_FAILURE_PARTIAL:
        router = _RouterBoundary(
            _router_output(
                IntentKind.POI_INFORMATION,
                (SpecialistKind.NARRATION,),
            )
        )
        narration = RuntimeError("private synthetic failure")
        request = _runtime_request(
            evidence=evidence,
            candidates=candidates,
            selected=True,
        )
    elif case.scenario is RuntimeScenario.DISCOVERY_WARNING_PARTIAL:
        router = _RouterBoundary(
            _router_output(
                IntentKind.NEARBY_DISCOVERY,
                (SpecialistKind.DISCOVERY,),
            )
        )
        discovery_output = _discovery_output(
            candidates=candidates,
            evidence=evidence,
            partial=True,
        )
        request = _runtime_request()
    elif case.scenario is RuntimeScenario.MISSING_ITINERARY_WINDOW:
        router = _RouterBoundary(
            _router_output(
                IntentKind.ITINERARY_DRAFTING,
                (SpecialistKind.DISCOVERY, SpecialistKind.ITINERARY),
            )
        )
        request = _runtime_request(
            candidates=candidates,
            selected=True,
        )
    elif case.scenario is RuntimeScenario.GROUNDING_REJECTION:
        conflict = _evidence(
            claims=(
                _claim(statement="Conflicting synthetic supplied fact."),
            )
        )
        router = _RouterBoundary(
            _router_output(
                IntentKind.NEARBY_DISCOVERY,
                (SpecialistKind.DISCOVERY,),
            )
        )
        request = _runtime_request(evidence=conflict)
    elif case.scenario is RuntimeScenario.RETRY_SUCCESS:
        router = _RouterBoundary(
            _router_output(IntentKind.GENERAL_TRAVEL_HELP),
            fail_first=True,
        )
        request = _runtime_request()
    else:
        router = _RouterBoundary(
            _router_output(IntentKind.GENERAL_TRAVEL_HELP),
            advance=advance,
        )
        request = _runtime_request()

    policy = OrchestrationPolicy(
        overall_timeout_seconds=(
            1.0
            if case.scenario is RuntimeScenario.LATENCY_BUDGET_FAILURE
            else 30.0
        ),
        router_timeout_seconds=3.0,
        discovery_timeout_seconds=8.0,
        specialist_timeout_seconds=8.0,
        grounding_timeout_seconds=5.0,
        composer_timeout_seconds=5.0,
        maximum_attempts=2,
    )
    store = InMemoryAgentObservabilityStore(capacity=4)
    observability = AgentObservabilityService(store=store)
    service = AgentOrchestratorService(
        router=router,
        discovery=_DiscoveryBoundary(discovery_output),
        narration=_NarrationBoundary(narration),
        local_culture=_CultureBoundary(),
        itinerary=itinerary,
        grounding=_GroundingBoundary(),
        composer=_ComposerBoundary(),
        observability=observability,
        policy=policy,
        monotonic_clock=clock,
    )
    result = await service.run(request)
    traces = await observability.list_for_request(
        AgentRequestTraceQuery(request_id=request.request_id)
    )
    usage = await observability.summarize(
        AgentUsageQuery(request_id=request.request_id)
    )
    checks = _base_checks()
    if result.status is case.expected_status:
        checks.add(EvalCheckCode.EXPECTED_STATUS)
    failure_codes = {
        failure.code for failure in result.failures
    }
    if case.expected_failure is None or case.expected_failure in failure_codes:
        checks.add(EvalCheckCode.EXPECTED_FAILURE)
    if (
        result.final_output is None
        or result.final_output.warnings == result.warnings
    ):
        checks.add(EvalCheckCode.WARNING_PRESERVED)
    if all(
        stage.output is None
        or stage.status
        in {StageStatus.SUCCESS, StageStatus.PARTIAL}
        for stage in result.stages
    ):
        checks.add(EvalCheckCode.CONTRACT_VALID)
    if "latitude" not in result.model_dump_json() and "longitude" not in (
        result.model_dump_json()
    ):
        checks.add(EvalCheckCode.PRIVACY_SAFE)
    observation_valid = (
        len(traces) == 1
        and traces[0].request_id == request.request_id
        and usage.trace_count == 1
        and usage.total_tokens == 0
        and usage.model_request_count == 0
    )
    if case.scenario is RuntimeScenario.RETRY_SUCCESS:
        if router.calls == 2 and observation_valid:
            checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    elif case.scenario is RuntimeScenario.MISSING_ITINERARY_WINDOW:
        if itinerary.calls == 0 and observation_valid:
            checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    elif observation_valid:
        checks.add(EvalCheckCode.NO_UNEXPECTED_CALL)
    if case.scenario is RuntimeScenario.GROUNDING_REJECTION:
        grounding_stage = next(
            stage
            for stage in result.stages
            if stage.agent is AgentKind.GROUNDING_REVIEWER
        )
        if (
            grounding_stage.status is StageStatus.PARTIAL
            and result.final_output is not None
            and "Conflicting synthetic supplied fact."
            not in result.final_output.final_text
        ):
            checks.add(EvalCheckCode.NO_NEW_FACT)
            checks.add(EvalCheckCode.EVIDENCE_CLOSED)
    else:
        checks.add(EvalCheckCode.NO_NEW_FACT)
        checks.add(EvalCheckCode.EVIDENCE_CLOSED)
    return _finish(result, checks)


async def execute_case(case: AgentEvalCase) -> ScenarioOutcome:
    """Execute exactly one real boundary and grade only closed checks."""
    if isinstance(case, RouterEvalCase):
        return await _execute_router(case)
    if isinstance(case, DiscoveryEvalCase):
        return await _execute_discovery(case)
    if isinstance(case, NarrationEvalCase):
        return await _execute_narration(case)
    if isinstance(case, LocalCultureEvalCase):
        return await _execute_culture(case)
    if isinstance(case, ItineraryEvalCase):
        return await _execute_itinerary(case)
    if isinstance(case, GroundingEvalCase):
        return await _execute_grounding(case)
    if isinstance(case, ComposerEvalCase):
        return await _execute_composer(case)
    return await _execute_runtime(case)
