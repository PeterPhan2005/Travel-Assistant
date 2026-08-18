"""Focused valid/invalid tests for all T040 public agent contracts."""

from __future__ import annotations

import inspect
import math
from datetime import date, datetime, time, timezone
from typing import Any, get_args, get_origin

import pytest
from pydantic import BaseModel, HttpUrl, ValidationError

import app.agents.contracts as contracts
from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    AgentRuntimeContext,
    AgentRuntimeRequest,
    AgentRuntimeResult,
    AgentWarning,
    AnswerStatus,
    ClaimRejectionReason,
    ComposerStageOutcome,
    CultureGuidanceItem,
    DiscoveryCandidate,
    DiscoveryCompleteness,
    DiscoveryOrigin,
    DiscoveryOutput,
    DiscoveryRequest,
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
    GroundingReviewStatus,
    ItineraryConstraints,
    ItineraryItem,
    ItineraryOutput,
    ItineraryRequest,
    NarrationOutput,
    NarrationRequest,
    NarrationSpecialistOutput,
    NarrationWordRange,
    PoiIdentity,
    PoiPresentationItem,
    PriceFact,
    RejectedClaim,
    ResponseComposerOutput,
    ResponseComposerRequest,
    RouterEntities,
    RouterOutput,
    RouterRequest,
    RouterStageOutcome,
    RuntimeItineraryWindow,
    RuntimeResultStatus,
    SourceRecord,
    SourceType,
    SpecialistKind,
    StageStatus,
    SupportedCity,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.providers.poi.models import (
    Coordinates,
    PoiProviderKind,
    SourceReference,
)
from pydantic import SecretStr

NOW = datetime(2026, 7, 28, 2, 0, tzinfo=timezone.utc)
PUBLIC_MODELS = tuple(
    value
    for name in contracts.__all__
    if inspect.isclass(value := getattr(contracts, name))
    and issubclass(value, BaseModel)
)


def _source(
    source_id: str = "source-a",
    *,
    retrieved_at: datetime | None = NOW,
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_INSTITUTION,
        label="Nguồn chính thức",
        publisher="Đơn vị quản lý",
        url=HttpUrl("https://example.test/source"),
        published_at=None,
        retrieved_at=retrieved_at,
    )


def _claim(
    claim_id: str,
    fact_kind: FactKind,
    statement: str,
    *,
    source_id: str = "source-a",
    poi_id: str = "curated:poi-a",
    price: PriceFact | None = None,
) -> FactualClaim:
    return FactualClaim(
        claim_id=claim_id,
        evidence_id=f"evidence-{claim_id}",
        fact_kind=fact_kind,
        statement=statement,
        supporting_source_ids=(source_id,),
        poi_id=poi_id,
        freshness_at=price.source_updated_at if price is not None else NOW,
        price=price,
    )


def _evidence() -> EvidenceBundle:
    price = PriceFact(
        price_minor_units=50_000,
        currency="VND",
        source_updated_at=NOW,
    )
    return EvidenceBundle(
        sources=(_source(),),
        claims=(
            _claim(
                "claim-culture",
                FactKind.CULTURE,
                "Đây là một thực hành văn hóa có nguồn.",
            ),
            _claim(
                "claim-history",
                FactKind.HISTORY,
                "Địa điểm có lịch sử được nguồn xác nhận.",
            ),
            _claim(
                "claim-price",
                FactKind.PRICE,
                "Giá niêm yết là 50.000 đồng.",
                price=price,
            ),
        ),
    )


def _culture_evidence() -> EvidenceBundle:
    return EvidenceBundle(
        sources=(_source(),),
        claims=(
            _claim(
                "claim-culture",
                FactKind.CULTURE,
                "Đây là một thực hành văn hóa có nguồn.",
            ),
        ),
    )


def _candidate() -> DiscoveryCandidate:
    provider = PoiProviderKind.CURATED
    source = SourceReference(
        source_id="source-a",
        source_type="official_institution",
        label="Nguồn chính thức",
        publisher="Đơn vị quản lý",
        url=HttpUrl("https://example.test/source"),
        published_at=None,
        retrieved_at=NOW,
    )
    return DiscoveryCandidate(
        id="curated:poi-a",
        provider=provider,
        provider_id="poi-a",
        canonical_name="Điểm tham quan A",
        city=SupportedCity.HCMC,
        category="museum",
        address=None,
        coordinates=Coordinates(latitude=10.77, longitude=106.69),
        distance_metres=125.5,
        rating=None,
        rating_count=None,
        price_level=None,
        opening_hours_summary=None,
        sources=(source,),
        retrieved_at=NOW,
        is_curated=True,
        is_externally_supplied=False,
    )


def _discovery_output(
    *,
    completeness: DiscoveryCompleteness = DiscoveryCompleteness.COMPLETE,
    failures: tuple[AgentFailure, ...] = (),
    is_truncated: bool = False,
) -> DiscoveryOutput:
    return DiscoveryOutput(
        candidates=(_candidate(),),
        evidence=_evidence(),
        provider_failures=failures,
        completeness=completeness,
        is_truncated=is_truncated,
    )


def _narration_request() -> NarrationRequest:
    return NarrationRequest(
        poi=PoiIdentity(
            poi_id="curated:poi-a",
            canonical_name="Điểm tham quan A",
            city=SupportedCity.HCMC,
            category="museum",
        ),
        evidence=_evidence(),
        locale="vi-VN",
        word_range=NarrationWordRange(
            minimum_words=100,
            maximum_words=200,
        ),
    )


def _words(count: int) -> str:
    return " ".join(f"từ{index}" for index in range(count))


def _narration_output(count: int = 100) -> NarrationOutput:
    return NarrationOutput(
        status=AnswerStatus.COMPLETE,
        narration_text=_words(count),
        key_points=("Lịch sử có nguồn",),
        used_source_ids=("source-a",),
        used_claim_ids=("claim-history",),
        limitation_reason=None,
    )


def _warning(
    stage: AgentKind = AgentKind.DISCOVERY,
) -> AgentWarning:
    return AgentWarning(
        stage=stage,
        code=FailureCode.PARTIAL_RESULT,
        message="Một nguồn tạm thời chưa phản hồi.",
        retryable=True,
    )


def _failure(
    stage: AgentKind = AgentKind.DISCOVERY,
) -> AgentFailure:
    return AgentFailure(
        stage=stage,
        code=FailureCode.PROVIDER_TIMEOUT,
        message="Nguồn dữ liệu phản hồi quá thời hạn.",
        retryable=True,
    )


def _itinerary_request() -> ItineraryRequest:
    return ItineraryRequest(
        city=SupportedCity.HCMC,
        local_date=date(2026, 8, 1),
        timezone="Asia/Ho_Chi_Minh",
        start_local_time=time(9, 0),
        end_local_time=time(17, 0),
        candidates=(_candidate(),),
        evidence=_evidence(),
        constraints=ItineraryConstraints(
            maximum_stops=2,
            required_poi_ids=("curated:poi-a",),
            excluded_poi_ids=(),
            preferred_categories=("museum",),
            notes=("Ưu tiên đi bộ ít",),
        ),
        start_origin=None,
    )


def _itinerary_output() -> ItineraryOutput:
    return ItineraryOutput(
        local_date=date(2026, 8, 1),
        timezone="Asia/Ho_Chi_Minh",
        start_local_time=time(9, 0),
        end_local_time=time(17, 0),
        items=(
            ItineraryItem(
                item_id="item-a",
                poi_id="curated:poi-a",
                title="Tham quan bảo tàng",
                start_local_time=time(9, 0),
                end_local_time=time(10, 0),
                supporting_claim_ids=("claim-history",),
                supporting_source_ids=("source-a",),
            ),
        ),
        assumptions=("Thời gian di chuyển chưa được ước tính.",),
        warnings=(),
        draft_only=True,
    )


def _specialist_output() -> NarrationSpecialistOutput:
    return NarrationSpecialistOutput(
        agent=AgentKind.NARRATION,
        output_id="output-narration",
        output=_narration_output(),
    )


def _composer_request(
    *,
    warnings: tuple[AgentWarning, ...] = (),
) -> ResponseComposerRequest:
    return ResponseComposerRequest(
        user_query="Hãy giới thiệu địa điểm này",
        locale="vi-VN",
        evidence=_evidence(),
        approved_claim_ids=("claim-history",),
        approved_specialist_outputs=(_specialist_output(),),
        warnings=warnings,
    )


def _composer_output(
    *,
    warnings: tuple[AgentWarning, ...] = (),
) -> ResponseComposerOutput:
    return ResponseComposerOutput(
        final_text="Đây là phần giới thiệu tiếng Việt đã được kiểm chứng.",
        poi_items=(
            PoiPresentationItem(
                poi_id="curated:poi-a",
                canonical_name="Điểm tham quan A",
                category="museum",
                address=None,
                distance_metres=125.5,
                rating=None,
                rating_count=None,
                price=None,
                opening_hours_summary=None,
            ),
        ),
        warnings=warnings,
        used_claim_ids=("claim-history",),
        used_source_ids=("source-a",),
    )


def _router_output() -> RouterOutput:
    return RouterOutput(
        primary_intent=contracts.IntentKind.NEARBY_DISCOVERY,
        entities=RouterEntities(
            city=SupportedCity.HCMC,
            category="museum",
            query_term=None,
            referenced_poi_ids=(),
            itinerary_constraints=None,
        ),
        specialist_plan=(SpecialistKind.DISCOVERY,),
        discovery_required=True,
        clarification_reason=None,
    )


def test_every_public_model_is_strict_frozen_documented_and_schema_capable() -> None:
    assert PUBLIC_MODELS
    for model in PUBLIC_MODELS:
        assert model.model_config.get("extra") == "forbid", model.__name__
        assert model.model_config.get("frozen") is True, model.__name__
        assert model.model_config.get("strict") is True, model.__name__
        assert inspect.getdoc(model), model.__name__
        schema = model.model_json_schema()
        assert schema["title"], model.__name__


def test_unknown_fields_frozen_instances_and_strict_scalars_fail() -> None:
    request = RouterRequest(
        user_query="Tìm bảo tàng gần đây",
        locale="vi-VN",
        city=SupportedCity.HCMC,
    )
    with pytest.raises(ValidationError):
        RouterRequest.model_validate(
            {
                **request.model_dump(),
                "reasoning": "not allowed",
            }
        )
    with pytest.raises(ValidationError):
        request.user_query = "changed"
    with pytest.raises(ValidationError):
        RouterRequest.model_validate(
            {
                "user_query": 123,
                "locale": "vi-VN",
            }
        )
    with pytest.raises(ValidationError):
        ItineraryConstraints.model_validate({"maximum_stops": "2"})


@pytest.mark.parametrize(
    "identifier",
    ["", " ", "../secret", "a/../b", "line\nbreak", "x" * 129],
)
def test_identifiers_reject_blank_traversal_control_and_oversize(
    identifier: str,
) -> None:
    with pytest.raises(ValidationError):
        SourceRecord(
            source_id=identifier,
            source_type=SourceType.OFFICIAL_INSTITUTION,
            label="Nguồn",
        )


def test_aware_datetime_finite_numbers_and_safe_messages_are_required() -> None:
    with pytest.raises(ValidationError):
        _source(retrieved_at=datetime(2026, 1, 1))
    with pytest.raises(ValidationError):
        DiscoveryOrigin(latitude=math.nan, longitude=106.7)
    candidate = _candidate()
    with pytest.raises(ValidationError):
        DiscoveryCandidate(
            id=candidate.id,
            provider=candidate.provider,
            provider_id=candidate.provider_id,
            canonical_name=candidate.canonical_name,
            city=candidate.city,
            category=candidate.category,
            address=candidate.address,
            coordinates=candidate.coordinates,
            distance_metres=math.inf,
            rating=candidate.rating,
            rating_count=candidate.rating_count,
            price_level=candidate.price_level,
            opening_hours_summary=candidate.opening_hours_summary,
            sources=candidate.sources,
            retrieved_at=candidate.retrieved_at,
            is_curated=candidate.is_curated,
            is_externally_supplied=candidate.is_externally_supplied,
        )
    with pytest.raises(ValidationError):
        AgentFailure(
            stage=AgentKind.DISCOVERY,
            code=FailureCode.INTERNAL,
            message="Bearer token leaked in stack trace",
            retryable=False,
        )


def test_evidence_bundle_rejects_duplicate_ids_missing_sources_and_bad_price() -> None:
    source = _source()
    claim = _claim(
        "claim-history",
        FactKind.HISTORY,
        "Lịch sử có nguồn.",
    )
    with pytest.raises(ValidationError):
        EvidenceBundle(sources=(source, source), claims=(claim,))
    with pytest.raises(ValidationError):
        EvidenceBundle(
            sources=(source,),
            claims=(
                _claim(
                    "claim-missing",
                    FactKind.HISTORY,
                    "Nguồn không tồn tại.",
                    source_id="source-missing",
                ),
            ),
        )
    with pytest.raises(ValidationError):
        FactualClaim(
            claim_id="claim-empty",
            evidence_id="evidence-empty",
            fact_kind=FactKind.HISTORY,
            statement="Không có nguồn.",
            supporting_source_ids=(),
            poi_id=None,
            freshness_at=None,
            price=None,
        )
    with pytest.raises(ValidationError):
        FactualClaim(
            claim_id="claim-price",
            evidence_id="evidence-price",
            fact_kind=FactKind.PRICE,
            statement="Giá niêm yết.",
            supporting_source_ids=("source-a",),
            poi_id="curated:poi-a",
            freshness_at=NOW,
            price=None,
        )
    with pytest.raises(ValidationError):
        PriceFact(
            price_minor_units=125_000,
            currency="VND",
            source_updated_at=None,  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        PriceFact.model_validate(
            {
                "price_minor_units": 12.5,
                "currency": "VND",
                "source_updated_at": NOW,
            }
        )


def test_grounding_candidates_represent_reviewable_failures_normally() -> None:
    incomplete_price = GroundingCandidatePrice(
        price_minor_units=125_000,
        currency="VND",
        source_updated_at=None,
    )
    empty_sources = GroundingCandidateClaim(
        claim_id="claim-empty",
        evidence_id="evidence-empty",
        fact_kind=FactKind.HISTORY,
        statement="Ứng viên không có nguồn.",
        supporting_source_ids=(),
        poi_id=None,
        freshness_at=None,
        price=None,
    )
    unknown_source = GroundingCandidateClaim(
        claim_id="claim-unknown-source",
        evidence_id="evidence-shared",
        fact_kind=FactKind.HISTORY,
        statement="Ứng viên trỏ đến nguồn chưa biết.",
        supporting_source_ids=("source-unknown",),
        poi_id=None,
        freshness_at=NOW,
        price=None,
    )
    incomplete_price_claim = GroundingCandidateClaim(
        claim_id="claim-price",
        evidence_id="evidence-shared",
        fact_kind=FactKind.PRICE,
        statement="Ứng viên giá chưa đủ thời điểm.",
        supporting_source_ids=("source-a",),
        poi_id=None,
        freshness_at=None,
        price=incomplete_price,
    )
    source = _source()
    conflicting_source = SourceRecord(
        source_id="source-a",
        source_type=SourceType.OFFICIAL_INSTITUTION,
        label="Nguồn xung đột nhưng hợp lệ",
        publisher="Đơn vị quản lý",
        url=HttpUrl("https://example.test/source"),
        published_at=None,
        retrieved_at=NOW,
    )
    conflicting_claim = GroundingCandidateClaim(
        claim_id="claim-empty",
        evidence_id="evidence-conflict",
        fact_kind=FactKind.HISTORY,
        statement="Ứng viên trùng ID nhưng khác nội dung.",
        supporting_source_ids=("source-a",),
        poi_id=None,
        freshness_at=NOW,
        price=None,
    )

    request = GroundingReviewRequest(
        evidence=GroundingCandidateEvidence(
            sources=(source, source, conflicting_source),
            claims=(
                empty_sources,
                conflicting_claim,
                unknown_source,
                incomplete_price_claim,
            ),
        ),
    )

    assert request.evidence.claims[0].supporting_source_ids == ()
    assert request.evidence.claims[2].supporting_source_ids == (
        "source-unknown",
    )
    assert request.evidence.claims[3].price is not None
    assert request.evidence.claims[3].price.source_updated_at is None


def test_grounding_candidate_boundary_stays_strict_and_schema_capable() -> None:
    with pytest.raises(ValidationError):
        GroundingCandidatePrice(
            price_minor_units=12.5,  # type: ignore[arg-type]
            currency="VND",
            source_updated_at=NOW,
        )
    with pytest.raises(ValidationError):
        GroundingCandidatePrice(
            price_minor_units=125_000,
            currency="vnd",
            source_updated_at=NOW,
        )
    with pytest.raises(ValidationError):
        GroundingCandidatePrice(
            price_minor_units=125_000,
            currency="VND",
            source_updated_at=datetime(2026, 7, 28, 2, 0),
        )
    with pytest.raises(ValidationError):
        GroundingReviewRequest.model_validate(
            {
                "evidence": {"sources": (), "claims": ()},
                "unexpected": True,
            }
        )
    with pytest.raises(ValidationError):
        GroundingCandidateClaim(
            claim_id="../claim",
            evidence_id="evidence-invalid",
            fact_kind=FactKind.HISTORY,
            statement="ID không hợp lệ.",
            supporting_source_ids=(),
        )

    candidate_evidence = GroundingCandidateEvidence.from_approved(_evidence())
    specialist = _specialist_output()
    requirement = FreshnessRequirement(
        fact_kind=FactKind.PRICE,
        as_of=NOW,
        maximum_age_seconds=86_400,
    )
    with pytest.raises(ValidationError):
        GroundingReviewRequest(
            evidence=candidate_evidence,
            specialist_outputs=(specialist, specialist),
        )
    with pytest.raises(ValidationError):
        GroundingReviewRequest(
            evidence=candidate_evidence,
            freshness_requirements=(requirement, requirement),
        )

    schema = GroundingReviewRequest.model_json_schema()
    assert "GroundingCandidateEvidence" in schema["$defs"]
    assert candidate_evidence.claims


def test_unicode_json_round_trip_and_missing_optionals_are_preserved() -> None:
    request = RouterRequest(
        user_query="Tìm phở ngon ở Thành phố Hồ Chí Minh",
        locale="vi-VN",
        city=SupportedCity.HCMC,
    )
    restored = RouterRequest.model_validate_json(request.model_dump_json())
    assert restored == request
    candidate_json = _candidate().model_dump(mode="json", exclude_none=True)
    assert "address" not in candidate_json
    assert "rating" not in candidate_json
    assert "opening_hours_summary" not in candidate_json


def test_public_fields_have_no_escape_hatch_or_sensitive_identity() -> None:
    forbidden_fields = {
        "raw",
        "payload",
        "metadata",
        "extra",
        "uid",
        "token",
        "email",
        "password",
        "transcript",
        "session",
    }
    for model in PUBLIC_MODELS:
        assert forbidden_fields.isdisjoint(model.model_fields), model.__name__
        for field in model.model_fields.values():
            assert not _annotation_contains_any(field.annotation), (
                model.__name__,
                field.annotation,
            )


def _annotation_contains_any(annotation: object) -> bool:
    if annotation is Any:
        return True
    origin = get_origin(annotation)
    return any(_annotation_contains_any(item) for item in get_args(annotation)) if (
        origin is not None
    ) else False


def test_runtime_context_is_narrow_strict_and_backward_compatible() -> None:
    original_fields = {
        "request_id",
        "user_query",
        "locale",
        "city",
        "preference_projection",
        "discovery_origin",
    }
    assert set(AgentRuntimeRequest.model_fields) == original_fields | {
        "context"
    }
    legacy = AgentRuntimeRequest(
        request_id="request-legacy",
        user_query="Tìm địa điểm gần đây",
        locale="vi-VN",
        city=SupportedCity.HCMC,
    )
    assert legacy.context == AgentRuntimeContext()
    with pytest.raises(ValidationError):
        AgentRuntimeContext.model_validate({"metadata": {}})


def test_runtime_context_preserves_candidate_order_and_rejects_duplicates() -> None:
    first = _candidate()
    second = first.model_copy(
        update={
            "id": "curated:poi-b",
            "provider_id": "poi-b",
            "canonical_name": "Điểm tham quan B",
            "distance_metres": 250.0,
        }
    )
    context = AgentRuntimeContext(candidates=(second, first))
    assert tuple(candidate.id for candidate in context.candidates) == (
        "curated:poi-b",
        "curated:poi-a",
    )
    with pytest.raises(ValidationError, match="unique"):
        AgentRuntimeContext(candidates=(first, first))


def test_runtime_context_rejects_city_and_selected_identity_conflicts() -> None:
    candidate = _candidate()
    with pytest.raises(ValidationError, match="Selected POI identity"):
        AgentRuntimeContext(
            selected_poi=PoiIdentity(
                poi_id=candidate.id,
                canonical_name="Tên không khớp",
                city=candidate.city,
                category=candidate.category,
            ),
            candidates=(candidate,),
        )
    bangkok = candidate.model_copy(
        update={
            "id": "curated:poi-bkk",
            "provider_id": "poi-bkk",
            "city": SupportedCity.BANGKOK,
        }
    )
    with pytest.raises(ValidationError, match="one city"):
        AgentRuntimeContext(candidates=(candidate, bangkok))
    with pytest.raises(ValidationError, match="request city"):
        AgentRuntimeRequest(
            request_id="request-city-conflict",
            user_query="Lập lịch trình",
            locale="vi-VN",
            city=SupportedCity.HCMC,
            context=AgentRuntimeContext(candidates=(bangkok,)),
        )


def test_runtime_itinerary_window_requires_iana_zone_and_naive_ordered_times() -> None:
    window = RuntimeItineraryWindow(
        local_date=date(2026, 8, 1),
        timezone="Asia/Ho_Chi_Minh",
        start_local_time=time(9, 0),
        end_local_time=time(17, 0),
    )
    assert window.local_date == date(2026, 8, 1)
    with pytest.raises(ValidationError, match="Timezone"):
        RuntimeItineraryWindow(
            local_date=date(2026, 8, 1),
            timezone="Mars/Olympus",
            start_local_time=time(9, 0),
            end_local_time=time(17, 0),
        )
    with pytest.raises(ValidationError, match="naive"):
        RuntimeItineraryWindow(
            local_date=date(2026, 8, 1),
            timezone="Asia/Ho_Chi_Minh",
            start_local_time=time(9, 0, tzinfo=timezone.utc),
            end_local_time=time(17, 0),
        )
    with pytest.raises(ValidationError, match="before"):
        RuntimeItineraryWindow(
            local_date=date(2026, 8, 1),
            timezone="Asia/Ho_Chi_Minh",
            start_local_time=time(17, 0),
            end_local_time=time(9, 0),
        )


@pytest.mark.parametrize(
    ("intent", "plan", "discovery_required"),
    [
        (
            contracts.IntentKind.NEARBY_DISCOVERY,
            (SpecialistKind.DISCOVERY,),
            True,
        ),
        (
            contracts.IntentKind.POI_INFORMATION,
            (SpecialistKind.NARRATION,),
            False,
        ),
        (
            contracts.IntentKind.LOCAL_CULTURE,
            (SpecialistKind.LOCAL_CULTURE,),
            False,
        ),
        (
            contracts.IntentKind.ITINERARY_DRAFTING,
            (SpecialistKind.DISCOVERY, SpecialistKind.ITINERARY),
            True,
        ),
        (contracts.IntentKind.GENERAL_TRAVEL_HELP, (), False),
    ],
)
def test_router_accepts_each_supported_mvp_intent(
    intent: contracts.IntentKind,
    plan: tuple[SpecialistKind, ...],
    discovery_required: bool,
) -> None:
    output = RouterOutput(
        primary_intent=intent,
        entities=RouterEntities(),
        specialist_plan=plan,
        discovery_required=discovery_required,
        clarification_reason=None,
    )
    assert output.primary_intent is intent


def test_router_unsupported_and_plan_consistency_fail_closed() -> None:
    unsupported = RouterOutput(
        primary_intent=contracts.IntentKind.UNSUPPORTED,
        entities=RouterEntities(),
        specialist_plan=(),
        discovery_required=False,
        clarification_reason="Yêu cầu nằm ngoài phạm vi hỗ trợ.",
    )
    assert unsupported.specialist_plan == ()
    with pytest.raises(ValidationError):
        RouterOutput(
            primary_intent=contracts.IntentKind.UNSUPPORTED,
            entities=RouterEntities(),
            specialist_plan=(SpecialistKind.DISCOVERY,),
            discovery_required=True,
            clarification_reason="Không hỗ trợ.",
        )
    with pytest.raises(ValidationError):
        RouterOutput(
            primary_intent=contracts.IntentKind.ITINERARY_DRAFTING,
            entities=RouterEntities(),
            specialist_plan=(
                SpecialistKind.ITINERARY,
                SpecialistKind.DISCOVERY,
            ),
            discovery_required=True,
            clarification_reason=None,
        )
    with pytest.raises(ValidationError):
        RouterOutput(
            primary_intent=contracts.IntentKind.NEARBY_DISCOVERY,
            entities=RouterEntities(),
            specialist_plan=(
                SpecialistKind.DISCOVERY,
                SpecialistKind.DISCOVERY,
            ),
            discovery_required=True,
            clarification_reason=None,
        )


def test_discovery_retains_metres_and_supports_safe_partial_failure() -> None:
    request = DiscoveryRequest(
        city=SupportedCity.HCMC,
        origin=DiscoveryOrigin(latitude=10.77, longitude=106.69),
        radius_metres=2_000,
        limit=5,
        query="bảo tàng",
        category="museum",
        requested_fact_kinds=(FactKind.CATEGORY, FactKind.DISTANCE),
    )
    assert request.radius_metres == 2_000
    output = _discovery_output()
    assert output.candidates[0].distance_metres == 125.5
    assert output.candidates[0].rating is None
    partial = _discovery_output(
        completeness=DiscoveryCompleteness.PARTIAL,
        failures=(_failure(),),
    )
    assert partial.candidates
    assert partial.provider_failures[0].retryable
    with pytest.raises(ValidationError):
        DiscoveryOutput(
            candidates=(),
            evidence=_evidence(),
            provider_failures=(_failure(),),
            completeness=DiscoveryCompleteness.PARTIAL,
            is_truncated=False,
        )
    assert "origin" not in DiscoveryOutput.model_fields
    assert "origin" not in AgentRuntimeResult.model_fields


@pytest.mark.parametrize("count", [100, 200])
def test_narration_accepts_inclusive_word_boundaries(count: int) -> None:
    output = _narration_output(count)
    assert output.validate_against(_narration_request()) is output


@pytest.mark.parametrize("count", [99, 201])
def test_narration_rejects_out_of_range_word_counts(count: int) -> None:
    with pytest.raises(ValidationError):
        _narration_output(count)


def test_narration_rejects_unknown_refs_html_and_allows_limited_result() -> None:
    request = _narration_request()
    unknown = _narration_output().model_copy(
        update={"used_claim_ids": ("claim-unknown",)}
    )
    with pytest.raises(ValueError):
        unknown.validate_against(request)
    with pytest.raises(ValidationError):
        NarrationOutput(
            status=AnswerStatus.COMPLETE,
            narration_text="<p>" + _words(100) + "</p>",
            key_points=("Điểm chính",),
            used_source_ids=("source-a",),
            used_claim_ids=("claim-history",),
        )
    limited = NarrationOutput(
        status=AnswerStatus.LIMITED,
        narration_text=None,
        key_points=(),
        used_source_ids=(),
        used_claim_ids=(),
        limitation_reason="Chưa có đủ bằng chứng để thuyết minh.",
    )
    assert limited.validate_against(request) is limited


def test_local_culture_requires_evidence_and_rejects_duplicate_guidance() -> None:
    request = contracts.LocalCultureRequest(
        city=SupportedCity.HCMC,
        topic="Ứng xử khi vào nơi thờ tự",
        locale="vi-VN",
        evidence=_culture_evidence(),
    )
    item = CultureGuidanceItem(
        guidance_id="guidance-a",
        text="Giữ giọng nói vừa phải tại nơi thờ tự.",
        claim_ids=("claim-culture",),
        source_ids=("source-a",),
    )
    output = contracts.LocalCultureOutput(
        status=AnswerStatus.COMPLETE,
        guidance=(item,),
        respectful_caution="Tôn trọng hướng dẫn tại địa điểm.",
        limitation_reason=None,
    )
    assert output.validate_against(request) is output
    with pytest.raises(ValidationError):
        CultureGuidanceItem(
            guidance_id="guidance-a",
            text="Nội dung không có nguồn.",
            claim_ids=(),
            source_ids=(),
        )
    with pytest.raises(ValidationError):
        contracts.LocalCultureOutput(
            status=AnswerStatus.COMPLETE,
            guidance=(item, item),
            respectful_caution=None,
            limitation_reason=None,
        )
    limited = contracts.LocalCultureOutput(
        status=AnswerStatus.LIMITED,
        guidance=(),
        respectful_caution=None,
        limitation_reason="Chưa có đủ bằng chứng văn hóa.",
    )
    assert limited.validate_against(request) is limited


def test_itinerary_accepts_ordered_draft_and_rejects_overlap_or_unknown_poi() -> None:
    request = _itinerary_request()
    output = _itinerary_output()
    assert output.draft_only is True
    assert output.validate_against(request) is output
    overlapping = {
        **output.model_dump(),
        "items": (
            output.items[0],
            ItineraryItem(
                item_id="item-b",
                poi_id="curated:poi-a",
                title="Dừng chân",
                start_local_time=time(9, 30),
                end_local_time=time(10, 30),
            ),
        ),
    }
    with pytest.raises(ValidationError):
        ItineraryOutput.model_validate(overlapping)
    with pytest.raises(ValidationError):
        ItineraryItem(
            item_id="item-b",
            poi_id="curated:poi-a",
            title="Sai thời gian",
            start_local_time=time(11, 0),
            end_local_time=time(10, 0),
        )
    unknown = output.model_copy(
        update={
            "items": (
                output.items[0].model_copy(
                    update={"poi_id": "curated:poi-unknown"}
                ),
            )
        }
    )
    with pytest.raises(ValueError):
        unknown.validate_against(request)


def test_grounding_review_is_disjoint_complete_and_closed_to_request() -> None:
    request = GroundingReviewRequest(
        evidence=GroundingCandidateEvidence.from_approved(_evidence()),
        specialist_outputs=(_specialist_output(),),
        freshness_requirements=(
            FreshnessRequirement(
                fact_kind=FactKind.PRICE,
                as_of=NOW,
                maximum_age_seconds=86_400,
            ),
        ),
    )
    approved = GroundingReviewOutput(
        status=GroundingReviewStatus.APPROVED,
        reviewed_claim_ids=("claim-history",),
        approved_claim_ids=("claim-history",),
        rejected_claims=(),
        approved_specialist_output_ids=("output-narration",),
        warnings=(),
    )
    assert approved.validate_against(request) is approved
    with pytest.raises(ValidationError):
        GroundingReviewOutput(
            status=GroundingReviewStatus.PARTIAL,
            reviewed_claim_ids=("claim-history",),
            approved_claim_ids=("claim-history",),
            rejected_claims=(
                RejectedClaim(
                    claim_id="claim-history",
                    reason=ClaimRejectionReason.UNSUPPORTED_CLAIM,
                ),
            ),
            approved_specialist_output_ids=(),
            warnings=(),
        )
    with pytest.raises(ValidationError):
        GroundingReviewOutput(
            status=GroundingReviewStatus.PARTIAL,
            reviewed_claim_ids=("claim-history", "claim-price"),
            approved_claim_ids=("claim-history",),
            rejected_claims=(),
            approved_specialist_output_ids=(),
            warnings=(),
        )
    unknown = GroundingReviewOutput(
        status=GroundingReviewStatus.REJECTED,
        reviewed_claim_ids=("claim-unknown",),
        approved_claim_ids=(),
        rejected_claims=(
            RejectedClaim(
                claim_id="claim-unknown",
                reason=ClaimRejectionReason.UNSUPPORTED_CLAIM,
            ),
        ),
        approved_specialist_output_ids=(),
        warnings=(),
    )
    with pytest.raises(ValueError):
        unknown.validate_against(request)


@pytest.mark.parametrize(
    "reason",
    [
        ClaimRejectionReason.UNSUPPORTED_CLAIM,
        ClaimRejectionReason.MISSING_SOURCE,
        ClaimRejectionReason.MISSING_PRICE_TIMESTAMP,
    ],
)
def test_grounding_has_typed_fail_closed_rejection_reasons(
    reason: ClaimRejectionReason,
) -> None:
    output = GroundingReviewOutput(
        status=GroundingReviewStatus.REJECTED,
        reviewed_claim_ids=("claim-price",),
        approved_claim_ids=(),
        rejected_claims=(
            RejectedClaim(claim_id="claim-price", reason=reason),
        ),
        approved_specialist_output_ids=(),
        warnings=(),
    )
    assert output.rejected_claims[0].reason is reason
    assert "statement" not in RejectedClaim.model_fields


def test_composer_uses_only_approved_claims_and_preserves_warnings() -> None:
    warning = _warning()
    request = _composer_request(warnings=(warning,))
    output = _composer_output(warnings=(warning,))
    assert output.validate_against(request) is output
    unknown = output.model_copy(
        update={"used_claim_ids": ("claim-price",)}
    )
    with pytest.raises(ValueError):
        unknown.validate_against(request)
    dropped = output.model_copy(update={"warnings": ()})
    with pytest.raises(ValueError):
        dropped.validate_against(request)
    with pytest.raises(ValidationError):
        ResponseComposerOutput(
            final_text="grounding_reviewer báo lỗi exception.",
            poi_items=(),
            warnings=(),
            used_claim_ids=(),
            used_source_ids=(),
        )
    serialized_item = output.poi_items[0].model_dump(
        mode="json",
        exclude_none=True,
    )
    assert "address" not in serialized_item
    assert "rating" not in serialized_item
    assert "origin" not in output.model_dump_json()


def test_orchestration_success_partial_and_failed_consistency() -> None:
    final = _composer_output()
    router_stage = RouterStageOutcome(
        agent=AgentKind.ROUTER,
        status=StageStatus.SUCCESS,
        duration_ms=10.5,
        output=_router_output(),
        warning=None,
        failure=None,
    )
    composer_stage = ComposerStageOutcome(
        agent=AgentKind.RESPONSE_COMPOSER,
        status=StageStatus.SUCCESS,
        duration_ms=20.0,
        output=final,
        warning=None,
        failure=None,
    )
    success = AgentRuntimeResult(
        request_id="request-001",
        status=RuntimeResultStatus.SUCCESS,
        final_output=final,
        stages=(router_stage, composer_stage),
        warnings=(),
        failures=(),
    )
    assert success.status is RuntimeResultStatus.SUCCESS

    warning = _warning()
    partial_final = _composer_output(warnings=(warning,))
    failed_discovery = contracts.DiscoveryStageOutcome(
        agent=AgentKind.DISCOVERY,
        status=StageStatus.FAILED,
        duration_ms=5.0,
        output=None,
        warning=None,
        failure=_failure(),
    )
    partial_composer = ComposerStageOutcome(
        agent=AgentKind.RESPONSE_COMPOSER,
        status=StageStatus.SUCCESS,
        duration_ms=12.0,
        output=partial_final,
        warning=None,
        failure=None,
    )
    partial = AgentRuntimeResult(
        request_id="request-002",
        status=RuntimeResultStatus.PARTIAL,
        final_output=partial_final,
        stages=(failed_discovery, partial_composer),
        warnings=(warning,),
        failures=(_failure(),),
    )
    assert partial.final_output is not None

    with pytest.raises(ValidationError):
        AgentRuntimeResult(
            request_id="request-003",
            status=RuntimeResultStatus.PARTIAL,
            final_output=final,
            stages=(),
            warnings=(),
            failures=(),
        )
    with pytest.raises(ValidationError):
        AgentRuntimeResult(
            request_id="request-004",
            status=RuntimeResultStatus.SUCCESS,
            final_output=final,
            stages=(),
            warnings=(),
            failures=(_failure(),),
        )
    with pytest.raises(ValidationError):
        AgentRuntimeResult(
            request_id="request-005",
            status=RuntimeResultStatus.FAILED,
            final_output=final,
            stages=(),
            warnings=(),
            failures=(_failure(),),
        )
    failed = AgentRuntimeResult(
        request_id="request-006",
        status=RuntimeResultStatus.FAILED,
        final_output=None,
        stages=(failed_discovery,),
        warnings=(),
        failures=(_failure(),),
    )
    assert failed.final_output is None


def test_orchestration_duration_and_unknown_stage_variant_fail() -> None:
    with pytest.raises(ValidationError):
        RouterStageOutcome(
            agent=AgentKind.ROUTER,
            status=StageStatus.SUCCESS,
            duration_ms=float("inf"),
            output=_router_output(),
        )
    valid = AgentRuntimeResult(
        request_id="request-007",
        status=RuntimeResultStatus.FAILED,
        final_output=None,
        stages=(
            RouterStageOutcome(
                agent=AgentKind.ROUTER,
                status=StageStatus.FAILED,
                duration_ms=1.0,
                output=None,
                warning=None,
                failure=AgentFailure(
                    stage=AgentKind.ROUTER,
                    code=FailureCode.INVALID_OUTPUT,
                    message="Kết quả định tuyến không hợp lệ.",
                    retryable=False,
                ),
            ),
        ),
        warnings=(),
        failures=(
            AgentFailure(
                stage=AgentKind.ROUTER,
                code=FailureCode.INVALID_OUTPUT,
                message="Kết quả định tuyến không hợp lệ.",
                retryable=False,
            ),
        ),
    )
    payload = valid.model_dump(mode="json")
    payload["stages"] = [
        {
            "agent": "orchestrator",
            "status": "failed",
            "duration_ms": 1.0,
            "output": None,
            "failure": {
                "stage": "router",
                "code": "internal",
                "message": "Không thể hoàn tất yêu cầu.",
                "retryable": False,
            },
        }
    ]
    with pytest.raises(ValidationError):
        AgentRuntimeResult.model_validate(payload)


def test_runtime_request_contains_origin_only_as_input() -> None:
    request = AgentRuntimeRequest(
        request_id="request-origin",
        user_query="Tìm địa điểm gần đây",
        locale="vi-VN",
        city=SupportedCity.HCMC,
        preference_projection=None,
        discovery_origin=DiscoveryOrigin(
            latitude=10.77,
            longitude=106.69,
        ),
    )
    assert request.discovery_origin is not None
    result_fields = AgentRuntimeResult.model_fields
    assert "discovery_origin" not in result_fields
    assert "origin" not in result_fields


def test_no_agent_route_or_openai_dependency_was_added() -> None:
    settings = Settings(
        database_url=SecretStr(
            "postgresql+asyncpg://unused:never-connect@"
            "database.invalid:9999/unused"
        ),
        firebase_project_id="travel-assistant-test",
        application_environment=ApplicationEnvironment.TEST,
    )
    paths = set(create_app(settings).openapi()["paths"])
    assert {"/health", "/auth/me", "/preferences", "/pois/nearby"}.issubset(
        paths
    )
    assert not any(
        path.startswith(("/agent", "/assistant"))
        for path in paths
    )
    module_sources = "\n".join(
        inspect.getsource(module)
        for module in (
            contracts,
            contracts.common,
            contracts.router,
            contracts.discovery,
            contracts.narration,
            contracts.local_culture,
            contracts.itinerary,
            contracts.grounding,
            contracts.composer,
            contracts.orchestration,
        )
    )
    assert "openai" not in module_sources.casefold()
    assert "fastapi" not in module_sources.casefold()
