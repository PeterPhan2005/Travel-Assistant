"""Strict tests for the authenticated assistant transport boundary."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from pydantic import HttpUrl, SecretStr
import pytest

from app.agents.contracts import (
    AnswerStatus,
    AgentFailure,
    AgentKind,
    AgentRuntimeRequest,
    AgentRuntimeResult,
    AgentWarning,
    ComposerStageOutcome,
    DiscoveryCompleteness,
    DiscoveryOrigin,
    DiscoveryOutput,
    DiscoveryStageOutcome,
    EvidenceBundle,
    FactKind,
    FailureCode,
    FactualClaim,
    GroundingReviewOutput,
    GroundingReviewStatus,
    GroundingStageOutcome,
    IntentKind,
    ItineraryItem,
    ItineraryOutput,
    ItineraryStageOutcome,
    NarrationOutput,
    NarrationStageOutcome,
    PoiPresentationItem,
    PriceFact,
    ResponseComposerOutput,
    RouterEntities,
    RouterOutput,
    RouterStageOutcome,
    RuntimeResultStatus,
    SourceRecord,
    SourceType,
    SpecialistKind,
    StageStatus,
)
from app.auth.models import (
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
    InvalidAuthenticationTokenError,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app

TEST_DATABASE_URL = (
    "postgresql+asyncpg://unused:never-connect@database.invalid:9999/unused"
)
TEST_FIREBASE_PROJECT_ID = "travel-assistant-test"
TOKEN_SENTINEL = "private-firebase-token"
UID_SENTINEL = "private-firebase-uid"
QUERY_SENTINEL = "Tôi muốn ăn phở gần đây"
REQUEST_ID = "assistant-request-id"


class TokenVerifier:
    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        assert raw_token == TOKEN_SENTINEL
        return AuthenticatedPrincipal(uid=UID_SENTINEL)


class InvalidTokenVerifier:
    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        del raw_token
        raise InvalidAuthenticationTokenError


class UnavailableTokenVerifier:
    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        assert raw_token == TOKEN_SENTINEL
        raise AuthenticationServiceUnavailableError(
            "InvalidArgumentError project=private-project "
            "credential=/private/adc.json "
            "url=https://identitytoolkit.googleapis.com/v1/accounts:lookup "
            f"uid={UID_SENTINEL} token={TOKEN_SENTINEL}"
        )


class CapturingOrchestrator:
    def __init__(self, result: AgentRuntimeResult | None = None) -> None:
        self.requests: list[AgentRuntimeRequest] = []
        self.result = result

    async def run(
        self,
        request: AgentRuntimeRequest,
    ) -> AgentRuntimeResult:
        self.requests.append(request)
        return self.result or _success_result(request.request_id)


class CancellingOrchestrator:
    async def run(
        self,
        request: AgentRuntimeRequest,
    ) -> AgentRuntimeResult:
        del request
        raise asyncio.CancelledError


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr(TEST_DATABASE_URL),
        firebase_project_id=TEST_FIREBASE_PROJECT_ID,
        application_environment=ApplicationEnvironment.TEST,
    )


def _client(
    orchestrator: object,
    *,
    verifier: object | None = None,
    raise_server_exceptions: bool = False,
) -> TestClient:
    return TestClient(
        create_app(
            _settings(),
            token_verifier=verifier or TokenVerifier(),  # type: ignore[arg-type]
            assistant_orchestrator=orchestrator,  # type: ignore[arg-type]
        ),
        raise_server_exceptions=raise_server_exceptions,
    )


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN_SENTINEL}",
        "X-Request-ID": REQUEST_ID,
    }


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "text": QUERY_SENTINEL,
        "locale": "vi-VN",
        "latitude": 10.776,
        "longitude": 106.7,
        "trip_id": None,
        "client_mode": "online",
    }
    payload.update(overrides)
    return payload


def _router_stage(
    *,
    intent: IntentKind = IntentKind.NEARBY_DISCOVERY,
) -> RouterStageOutcome:
    plan = (
        (SpecialistKind.DISCOVERY,)
        if intent is IntentKind.NEARBY_DISCOVERY
        else ()
    )
    return RouterStageOutcome(
        agent=AgentKind.ROUTER,
        status=StageStatus.SUCCESS,
        duration_ms=1.0,
        output=RouterOutput(
            primary_intent=intent,
            entities=RouterEntities(),
            specialist_plan=plan,
            discovery_required=bool(plan),
        ),
    )


def _source(source_id: str, label: str) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_OPERATOR,
        label=label,
        publisher="Nhà xuất bản",
        url=HttpUrl(f"https://example.com/{source_id}"),
        retrieved_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )


def _output(
    *,
    warnings: tuple[AgentWarning, ...] = (),
    final_text: str = "Có một lựa chọn đã được xác nhận từ nguồn hiện có.",
) -> ResponseComposerOutput:
    return ResponseComposerOutput(
        final_text=final_text,
        poi_items=(
            PoiPresentationItem(
                poi_id="curated:pho-one",
                canonical_name="Phở Một",
                category="restaurant",
                address=None,
                distance_metres=125.5,
                rating=Decimal("4.5"),
                rating_count=None,
                price=PriceFact(
                    price_minor_units=65_000,
                    currency="VND",
                    source_updated_at=datetime(
                        2026,
                        7,
                        1,
                        tzinfo=timezone.utc,
                    ),
                ),
                opening_hours_summary=None,
            ),
        ),
        warnings=warnings,
        used_claim_ids=("claim-one",),
        used_source_ids=("source-one",),
    )


def _success_result(request_id: str) -> AgentRuntimeResult:
    output = _output()
    evidence = EvidenceBundle(
        sources=(
            _source("source-one", "Nguồn được dùng"),
            _source("source-two", "Nguồn không được dùng"),
        ),
        claims=(
            FactualClaim(
                claim_id="claim-one",
                evidence_id="evidence-one",
                fact_kind=FactKind.IDENTITY,
                statement="Phở Một là một địa điểm.",
                supporting_source_ids=("source-one",),
                poi_id="curated:pho-one",
            ),
        ),
    )
    return AgentRuntimeResult(
        request_id=request_id,
        status=RuntimeResultStatus.SUCCESS,
        stages=(
            _router_stage(),
            DiscoveryStageOutcome(
                agent=AgentKind.DISCOVERY,
                status=StageStatus.SUCCESS,
                duration_ms=2.0,
                output=DiscoveryOutput(
                    candidates=(),
                    evidence=evidence,
                    completeness=DiscoveryCompleteness.COMPLETE,
                    is_truncated=False,
                ),
            ),
            ComposerStageOutcome(
                agent=AgentKind.RESPONSE_COMPOSER,
                status=StageStatus.SUCCESS,
                duration_ms=1.0,
                output=output,
            ),
        ),
        final_output=output,
    )


def _partial_result(request_id: str) -> AgentRuntimeResult:
    warning = AgentWarning(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PARTIAL_RESULT,
        message="Một phần dữ liệu chưa thể được xác nhận.",
        retryable=True,
    )
    output = _output(warnings=(warning,))
    return AgentRuntimeResult(
        request_id=request_id,
        status=RuntimeResultStatus.PARTIAL,
        stages=(
            _router_stage(intent=IntentKind.GENERAL_TRAVEL_HELP),
            DiscoveryStageOutcome(
                agent=AgentKind.DISCOVERY,
                status=StageStatus.PARTIAL,
                duration_ms=2.0,
                output=DiscoveryOutput(
                    evidence=EvidenceBundle(),
                    completeness=DiscoveryCompleteness.COMPLETE,
                    is_truncated=False,
                ),
                warning=warning,
            ),
            ComposerStageOutcome(
                agent=AgentKind.RESPONSE_COMPOSER,
                status=StageStatus.SUCCESS,
                duration_ms=1.0,
                output=output,
            ),
        ),
        final_output=output,
        warnings=(warning,),
    )


def _failed_result(request_id: str) -> AgentRuntimeResult:
    failure = AgentFailure(
        stage=AgentKind.ROUTER,
        code=FailureCode.SPECIALIST_FAILED,
        message="Chưa thể phân loại yêu cầu một cách an toàn.",
        retryable=False,
    )
    return AgentRuntimeResult(
        request_id=request_id,
        status=RuntimeResultStatus.FAILED,
        stages=(
            RouterStageOutcome(
                agent=AgentKind.ROUTER,
                status=StageStatus.FAILED,
                duration_ms=1.0,
                failure=failure,
            ),
        ),
        failures=(failure,),
    )


def _specialist_boundary_result(
    request_id: str,
    *,
    composer_succeeds: bool,
) -> AgentRuntimeResult:
    narration_text = " ".join(["xác-nhận"] * 100)
    narration = NarrationOutput(
        status=AnswerStatus.COMPLETE,
        narration_text=narration_text,
        key_points=("Điểm chính đã được xác nhận.",),
        used_source_ids=("source-one",),
        used_claim_ids=("claim-one",),
    )
    itinerary = ItineraryOutput(
        local_date=date(2026, 8, 1),
        timezone="Asia/Ho_Chi_Minh",
        start_local_time=time(9, 0),
        end_local_time=time(10, 0),
        items=(
            ItineraryItem(
                item_id="item-one",
                poi_id="curated:pho-one",
                title="Điểm dừng đã được xác nhận",
                start_local_time=time(9, 0),
                end_local_time=time(10, 0),
                supporting_claim_ids=("claim-one",),
                supporting_source_ids=("source-one",),
            ),
        ),
        assumptions=("Đây là lịch trình nháp.",),
        draft_only=True,
    )
    evidence = EvidenceBundle(
        sources=(_source("source-one", "Nguồn được dùng"),),
        claims=(
            FactualClaim(
                claim_id="claim-one",
                evidence_id="evidence-one",
                fact_kind=FactKind.IDENTITY,
                statement="Phở Một là một địa điểm.",
                supporting_source_ids=("source-one",),
                poi_id="curated:pho-one",
            ),
        ),
    )
    output = _output(
        final_text=(
            f"{narration_text} Điểm dừng đã được xác nhận. "
            "Đây là lịch trình nháp."
        )
    )
    composer_failure = AgentFailure(
        stage=AgentKind.RESPONSE_COMPOSER,
        code=FailureCode.SPECIALIST_FAILED,
        message="Chưa thể hoàn tất câu trả lời an toàn.",
        retryable=False,
    )
    composer_stage = ComposerStageOutcome(
        agent=AgentKind.RESPONSE_COMPOSER,
        status=(
            StageStatus.SUCCESS
            if composer_succeeds
            else StageStatus.FAILED
        ),
        duration_ms=1.0,
        output=output if composer_succeeds else None,
        failure=None if composer_succeeds else composer_failure,
    )
    return AgentRuntimeResult(
        request_id=request_id,
        status=(
            RuntimeResultStatus.SUCCESS
            if composer_succeeds
            else RuntimeResultStatus.FAILED
        ),
        stages=(
            _router_stage(),
            DiscoveryStageOutcome(
                agent=AgentKind.DISCOVERY,
                status=StageStatus.SUCCESS,
                duration_ms=1.0,
                output=DiscoveryOutput(
                    evidence=evidence,
                    completeness=DiscoveryCompleteness.COMPLETE,
                    is_truncated=False,
                ),
            ),
            NarrationStageOutcome(
                agent=AgentKind.NARRATION,
                status=StageStatus.SUCCESS,
                duration_ms=1.0,
                output=narration,
            ),
            ItineraryStageOutcome(
                agent=AgentKind.ITINERARY,
                status=StageStatus.SUCCESS,
                duration_ms=1.0,
                output=itinerary,
            ),
            GroundingStageOutcome(
                agent=AgentKind.GROUNDING_REVIEWER,
                status=StageStatus.SUCCESS,
                duration_ms=1.0,
                output=GroundingReviewOutput(
                    status=GroundingReviewStatus.APPROVED,
                    reviewed_claim_ids=("claim-one",),
                    approved_claim_ids=("claim-one",),
                    approved_specialist_output_ids=(
                        "runtime-itinerary",
                        "runtime-narration",
                    ),
                ),
            ),
            composer_stage,
        ),
        final_output=output if composer_succeeds else None,
        failures=() if composer_succeeds else (composer_failure,),
    )


def test_route_is_registered_and_existing_routes_remain_available() -> None:
    paths = set(
        create_app(
            _settings(),
            token_verifier=TokenVerifier(),
            assistant_orchestrator=CapturingOrchestrator(),
        ).openapi()["paths"]
    )

    assert paths == {
        "/health",
        "/auth/me",
        "/preferences",
        "/pois/nearby",
        "/v1/assistant/query",
        "/v1/itinerary-drafts/generate",
    }


def test_missing_and_invalid_authentication_never_run_orchestrator() -> None:
    missing = CapturingOrchestrator()
    invalid = CapturingOrchestrator()
    with _client(missing) as client:
        missing_response = client.post(
            "/v1/assistant/query",
            json=_payload(),
        )
    with _client(invalid, verifier=InvalidTokenVerifier()) as client:
        invalid_response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )

    assert missing_response.status_code == 401
    assert invalid_response.status_code == 401
    assert (
        missing_response.json()["error"]["code"]
        == "authentication_required"
    )
    assert invalid_response.json()["error"]["code"] == "invalid_token"
    assert missing.requests == []
    assert invalid.requests == []


def test_authentication_provider_failure_is_sanitized_and_not_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    orchestrator = CapturingOrchestrator()
    caplog.set_level(logging.DEBUG)
    with _client(
        orchestrator,
        verifier=UnavailableTokenVerifier(),
    ) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == REQUEST_ID
    assert response.json()["error"] == {
        "code": "authentication_unavailable",
        "message": "Authentication is temporarily unavailable.",
        "request_id": REQUEST_ID,
        "details": None,
    }
    assert orchestrator.requests == []
    combined_logs = "\n".join(
        record.getMessage() for record in caplog.records
    )
    for private_value in (
        "InvalidArgumentError",
        "private-project",
        "/private/adc.json",
        "accounts:lookup",
        UID_SENTINEL,
        TOKEN_SENTINEL,
        "Authorization",
    ):
        assert private_value not in response.text
        assert private_value not in combined_logs


def test_valid_token_maps_exact_strict_runtime_request_without_identity() -> None:
    orchestrator = CapturingOrchestrator()
    with _client(orchestrator) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(text=f"  {QUERY_SENTINEL}  "),
        )

    assert response.status_code == 200
    assert len(orchestrator.requests) == 1
    request = orchestrator.requests[0]
    assert request == AgentRuntimeRequest(
        request_id=REQUEST_ID,
        user_query=QUERY_SENTINEL,
        locale="vi-VN",
        city=None,
        preferences=None,
        discovery_origin=DiscoveryOrigin(
            latitude=10.776,
            longitude=106.7,
        ),
    )
    serialized = str(request.model_dump(mode="json"))
    assert UID_SENTINEL not in serialized
    assert TOKEN_SENTINEL not in serialized
    assert response.headers["X-Request-ID"] == REQUEST_ID
    assert response.json()["request_id"] == REQUEST_ID


@pytest.mark.parametrize(
    "payload",
    [
        _payload(unknown=True),
        _payload(audio="base64"),
        _payload(audio_url="https://example.com/audio"),
        _payload(file="recording"),
        _payload(recording=True),
        _payload(mime_type="audio/wav"),
        _payload(text="   "),
        _payload(text="a" * 501),
        _payload(text="hello\u0000world"),
        _payload(latitude=None, longitude=106.7),
        _payload(latitude=10.7, longitude=None),
        _payload(latitude=91.0),
        _payload(longitude=181.0),
        _payload(latitude="NaN"),
        _payload(longitude="Infinity"),
        _payload(trip_id="trip-one"),
        _payload(client_mode="offline"),
    ],
)
def test_invalid_or_audio_request_fields_are_rejected(
    payload: dict[str, object],
) -> None:
    orchestrator = CapturingOrchestrator()
    with _client(orchestrator) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=payload,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert orchestrator.requests == []


def test_coordinates_may_be_absent_and_vietnamese_unicode_is_preserved() -> None:
    orchestrator = CapturingOrchestrator()
    payload = _payload(text="  Tôi cần một gợi ý ở Đà Lạt  ")
    payload.pop("latitude")
    payload.pop("longitude")
    with _client(orchestrator) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=payload,
        )

    assert response.status_code == 200
    assert orchestrator.requests[0].user_query == "Tôi cần một gợi ý ở Đà Lạt"
    assert orchestrator.requests[0].discovery_origin is None


@pytest.mark.parametrize(
    ("result_factory", "expected_status", "expected_intent"),
    [
        (_success_result, "success", "nearby_discovery"),
        (_partial_result, "partial", "general_travel_help"),
        (_failed_result, "failed", None),
    ],
)
def test_runtime_status_intent_and_safe_message_mapping(
    result_factory: object,
    expected_status: str,
    expected_intent: str | None,
) -> None:
    factory = result_factory  # keep parametrized callable type explicit below
    result = factory(REQUEST_ID)  # type: ignore[operator]
    with _client(CapturingOrchestrator(result)) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == expected_status
    assert body["intent"] == expected_intent
    assert body["message"]
    if expected_status == "failed":
        assert body["poi_results"] == []
        assert "lựa chọn" not in body["message"].casefold()


def test_success_preserves_optional_poi_nulls_and_source_closure() -> None:
    with _client(CapturingOrchestrator(_success_result(REQUEST_ID))) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )

    body = response.json()
    poi = body["poi_results"][0]
    assert poi["address"] is None
    assert poi["rating_count"] is None
    assert poi["opening_hours_summary"] is None
    assert poi["distance_metres"] == 125.5
    assert poi["price"] == {
        "minor_units": 65000,
        "currency": "VND",
        "updated_at": "2026-07-01T00:00:00Z",
    }
    assert [source["label"] for source in body["sources"]] == [
        "Nguồn được dùng"
    ]


def test_specialist_output_requires_grounding_and_successful_composition() -> None:
    approved = _specialist_boundary_result(
        REQUEST_ID,
        composer_succeeds=True,
    )
    composer_failed = _specialist_boundary_result(
        REQUEST_ID,
        composer_succeeds=False,
    )
    with _client(CapturingOrchestrator(approved)) as client:
        approved_response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )
    with _client(CapturingOrchestrator(composer_failed)) as client:
        failed_response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )

    assert approved_response.status_code == 200
    approved_body = approved_response.json()
    assert approved_body["narration"]["text"]
    assert approved_body["itinerary"]["draft_only"] is True
    assert approved_body["itinerary"]["items"] == [
        {
            "title": "Điểm dừng đã được xác nhận",
            "start_local_time": "09:00:00",
            "end_local_time": "10:00:00",
        }
    ]

    assert failed_response.status_code == 200
    failed_body = failed_response.json()
    assert failed_body["status"] == "failed"
    assert failed_body["poi_results"] == []
    assert failed_body["narration"] is None
    assert failed_body["itinerary"] is None
    assert failed_body["sources"] == []


def test_partial_warning_is_bounded_and_internal_fields_never_escape() -> None:
    with _client(CapturingOrchestrator(_partial_result(REQUEST_ID))) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )

    body = response.json()
    assert body["warnings"] == [
        {
            "message": "Một phần dữ liệu chưa thể được xác nhận.",
            "retryable": True,
        }
    ]
    assert body["retryable"] is True
    forbidden = {
        "stages",
        "trace_id",
        "token_usage",
        "duration_ms",
        "agent",
        "claim_id",
        "source_id",
        "uid",
        "latitude",
        "longitude",
    }
    assert forbidden.isdisjoint(body)
    assert not any(key in response.text for key in forbidden)


def test_injected_orchestrator_requires_no_database_or_model_execution() -> None:
    orchestrator = CapturingOrchestrator()
    with _client(orchestrator) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )

    assert response.status_code == 200
    assert len(orchestrator.requests) == 1


def test_query_coordinate_token_and_identity_are_not_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    with _client(CapturingOrchestrator()) as client:
        response = client.post(
            "/v1/assistant/query",
            headers=_headers(),
            json=_payload(),
        )

    assert response.status_code == 200
    logs = caplog.text
    for private_value in (
        QUERY_SENTINEL,
        TOKEN_SENTINEL,
        UID_SENTINEL,
        "10.776",
        "106.7",
        response.json()["message"],
        "https://example.com/source-one",
    ):
        assert private_value not in logs


def test_caller_cancellation_is_not_converted_to_http_failure() -> None:
    with _client(
        CancellingOrchestrator(),
        raise_server_exceptions=True,
    ) as client:
        with pytest.raises(BaseException) as raised:
            client.post(
                "/v1/assistant/query",
                headers=_headers(),
                json=_payload(),
            )

    assert isinstance(
        raised.value,
        (asyncio.CancelledError, GeneratorExit),
    ) or raised.value.__class__.__name__ == "CancelledError"
