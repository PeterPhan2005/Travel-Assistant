"""HTTP contract tests for structured itinerary draft generation."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, time
from pathlib import Path
from types import TracebackType

import httpx
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from app.auth.models import (
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
    InvalidAuthenticationTokenError,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.itinerary_generation import (
    ItineraryDraftFailureCategory,
    ItineraryDraftGenerationRequest,
    ItineraryDraftGenerationResponse,
    ItineraryDraftGenerationStatus,
    ItineraryDraftItemResponse,
)
from app.main import create_app
from app.providers.poi.models import PoiResultEnvelope, PoiProviderKind
from app.providers.poi.models import SupportedCity

TEST_DATABASE_URL = (
    "postgresql+asyncpg://unused:never-connect@database.invalid:9999/unused"
)
TOKEN = "private-itinerary-token"
UID = "private-itinerary-uid"
REQUEST_ID = "itinerary-request-id"
PRIVATE_NOTE = "Ghi chú riêng tư chỉ dùng trong request"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class TokenVerifier:
    async def verify_id_token(self, raw_token: str) -> AuthenticatedPrincipal:
        assert raw_token == TOKEN
        return AuthenticatedPrincipal(uid=UID)


class InvalidTokenVerifier:
    async def verify_id_token(self, raw_token: str) -> AuthenticatedPrincipal:
        del raw_token
        raise InvalidAuthenticationTokenError


class UnavailableTokenVerifier:
    async def verify_id_token(self, raw_token: str) -> AuthenticatedPrincipal:
        del raw_token
        raise AuthenticationServiceUnavailableError("private provider detail")


class CapturingGenerator:
    def __init__(
        self,
        response: ItineraryDraftGenerationResponse | None = None,
    ) -> None:
        self.requests: list[ItineraryDraftGenerationRequest] = []
        self.response = response

    async def generate(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ItineraryDraftGenerationResponse:
        self.requests.append(request)
        return self.response or _success_response(request)


class CancellingGenerator:
    async def generate(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ItineraryDraftGenerationResponse:
        del request
        raise asyncio.CancelledError


class UnexpectedGenerator:
    async def generate(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ItineraryDraftGenerationResponse:
        del request
        raise RuntimeError("private note, coordinate and database detail")


class UnusedPoiProvider:
    async def discover(self, request: object) -> PoiResultEnvelope:
        del request
        return PoiResultEnvelope(
            provider=PoiProviderKind.CURATED,
            items=(),
            returned_count=0,
            is_complete=True,
        )


class TrackingSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class TrackingSessionContext:
    def __init__(self) -> None:
        self.session = TrackingSession()
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(self) -> TrackingSession:
        self.enter_count += 1
        return self.session

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback
        self.exit_count += 1


class TrackingSessionFactory:
    def __init__(self) -> None:
        self.contexts: list[TrackingSessionContext] = []

    def __call__(self) -> TrackingSessionContext:
        context = TrackingSessionContext()
        self.contexts.append(context)
        return context


class TrackingDatabaseRuntime:
    def __init__(self) -> None:
        self.session_factory = TrackingSessionFactory()
        self.dispose_count = 0

    async def dispose(self) -> None:
        self.dispose_count += 1


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr(TEST_DATABASE_URL),
        firebase_project_id="travel-assistant-test",
        application_environment=ApplicationEnvironment.TEST,
    )


def _client(
    generator: object,
    *,
    verifier: object | None = None,
    raise_server_exceptions: bool = False,
) -> TestClient:
    return TestClient(
        create_app(
            _settings(),
            token_verifier=verifier or TokenVerifier(),  # type: ignore[arg-type]
            poi_provider=UnusedPoiProvider(),
            itinerary_generator=generator,  # type: ignore[arg-type]
        ),
        raise_server_exceptions=raise_server_exceptions,
    )


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Request-ID": REQUEST_ID,
    }


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "city": "hcmc",
        "local_date": "2026-08-01",
        "timezone": "Asia/Ho_Chi_Minh",
        "start_local_time": "09:00",
        "end_local_time": "17:00",
        "maximum_stops": 4,
        "notes": PRIVATE_NOTE,
        "locale": "vi-VN",
        "client_mode": "online",
        "latitude": 10.776,
        "longitude": 106.7,
    }
    payload.update(overrides)
    return payload


def _success_response(
    request: ItineraryDraftGenerationRequest,
) -> ItineraryDraftGenerationResponse:
    return ItineraryDraftGenerationResponse(
        status=ItineraryDraftGenerationStatus.SUCCESS,
        city=request.city,
        local_date=request.local_date,
        timezone=request.timezone,
        start_local_time=request.start_local_time,
        end_local_time=request.end_local_time,
        items=(
            ItineraryDraftItemResponse(
                start_local_time=request.start_local_time,
                end_local_time=request.end_local_time,
                title="Bưu điện Trung tâm Sài Gòn",
            ),
        ),
        assumptions=("Đây là lịch trình nháp được chia thời gian đều.",),
        retryable=False,
    )


def _contract_fixture(name: str) -> str:
    return (
        REPOSITORY_ROOT / "contracts" / "fixtures" / name
    ).read_text(encoding="utf-8").strip()


def _synthetic_contract_response(
    city: SupportedCity,
) -> ItineraryDraftGenerationResponse:
    if city is SupportedCity.HCMC:
        return ItineraryDraftGenerationResponse(
            status=ItineraryDraftGenerationStatus.SUCCESS,
            city=city,
            local_date=date(2026, 8, 2),
            timezone="Asia/Ho_Chi_Minh",
            start_local_time=time(9, 0),
            end_local_time=time(17, 0),
            items=(
                ItineraryDraftItemResponse(
                    start_local_time=time(9, 0),
                    end_local_time=time(13, 0),
                    title="Điểm thử nghiệm Một",
                ),
                ItineraryDraftItemResponse(
                    start_local_time=time(13, 0),
                    end_local_time=time(17, 0),
                    title="Điểm thử nghiệm Hai",
                ),
            ),
            assumptions=("Giả định thử nghiệm an toàn.",),
            retryable=False,
        )
    return ItineraryDraftGenerationResponse(
        status=ItineraryDraftGenerationStatus.PARTIAL,
        city=city,
        local_date=date(2026, 8, 2),
        timezone="Asia/Bangkok",
        start_local_time=time(9, 0),
        end_local_time=time(17, 0),
        items=(
            ItineraryDraftItemResponse(
                start_local_time=time(9, 0),
                end_local_time=time(17, 0),
                title="Điểm thử nghiệm Bangkok",
            ),
        ),
        assumptions=("Giả định thử nghiệm an toàn.",),
        warnings=("Cảnh báo thử nghiệm an toàn.",),
        retryable=True,
    )


def _assert_validation_error(response: httpx.Response | object) -> None:
    assert getattr(response, "status_code") == 422
    body = response.json()  # type: ignore[union-attr]
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed."


def test_authentication_contract_and_valid_request_mapping() -> None:
    generator = CapturingGenerator()
    with _client(generator) as client:
        missing = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(),
        )
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert not generator.requests

    with _client(generator, verifier=InvalidTokenVerifier()) as client:
        invalid = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(),
            headers=_headers(),
        )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "invalid_token"

    with _client(generator, verifier=UnavailableTokenVerifier()) as client:
        unavailable = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(),
            headers=_headers(),
        )
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "authentication_unavailable"
    assert "private provider detail" not in unavailable.text

    with _client(generator) as client:
        valid = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(),
            headers=_headers(),
        )
    assert valid.status_code == 200
    captured = generator.requests[-1]
    assert captured.local_date == date(2026, 8, 1)
    assert captured.start_local_time == time(9, 0)
    assert captured.end_local_time == time(17, 0)
    assert captured.notes == PRIVATE_NOTE
    assert captured.maximum_stops == 4
    assert captured.latitude == 10.776
    assert valid.headers["X-Request-ID"] == REQUEST_ID
    assert "request_id" not in valid.json()


@pytest.mark.parametrize(
    "field",
    [
        "unknown",
        "audio",
        "transcript",
        "candidate",
        "evidence",
        "source_id",
        "claim_id",
        "stage",
        "agent",
        "prompt",
        "token",
        "saved_itinerary_id",
    ],
)
def test_unknown_audio_transcript_and_internal_fields_are_rejected(
    field: str,
) -> None:
    with _client(CapturingGenerator()) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(**{field: "private"}),
            headers=_headers(),
        )
    _assert_validation_error(response)
    assert "private" not in response.text


@pytest.mark.parametrize(
    "updates",
    [
        {"city": "hcmc", "timezone": "Asia/Bangkok"},
        {"city": "bkk", "timezone": "Asia/Ho_Chi_Minh"},
        {"city": "unknown"},
        {"local_date": "2026-02-30"},
        {"local_date": "2026-08-01T00:00:00"},
        {"start_local_time": "9:00"},
        {"start_local_time": "09:00:01"},
        {"start_local_time": "17:00", "end_local_time": "17:00"},
        {"start_local_time": "18:00", "end_local_time": "17:00"},
        {"maximum_stops": 0},
        {"maximum_stops": 21},
        {"maximum_stops": 4.0},
        {"notes": "x" * 501},
        {"latitude": None, "longitude": 106.7},
        {"latitude": 10.7, "longitude": None},
        {"latitude": 91.0},
        {"longitude": -181.0},
        {"client_mode": "offline"},
        {"client_mode": "demo"},
    ],
)
def test_strict_request_validation(updates: dict[str, object]) -> None:
    with _client(CapturingGenerator()) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(**updates),
            headers=_headers(),
        )
    _assert_validation_error(response)


@pytest.mark.parametrize("non_finite", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_coordinates_are_rejected(non_finite: str) -> None:
    payload = _payload()
    encoded = json.dumps(payload, ensure_ascii=False).replace(
        "10.776",
        non_finite,
        1,
    )
    with _client(CapturingGenerator()) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            content=encoded,
            headers={**_headers(), "Content-Type": "application/json"},
        )
    _assert_validation_error(response)


@pytest.mark.parametrize(
    ("city", "timezone"),
    [
        ("hcmc", "Asia/Ho_Chi_Minh"),
        ("bkk", "Asia/Bangkok"),
    ],
)
def test_exact_supported_city_timezone_pairs(
    city: str,
    timezone: str,
) -> None:
    generator = CapturingGenerator()
    with _client(generator) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(city=city, timezone=timezone),
            headers=_headers(),
        )
    assert response.status_code == 200
    assert response.json()["city"] == city
    assert response.json()["timezone"] == timezone


@pytest.mark.parametrize(
    ("city", "timezone", "fixture_name", "expected_item_count"),
    [
        (
            SupportedCity.HCMC,
            "Asia/Ho_Chi_Minh",
            "t062_itinerary_success_hcmc.json",
            2,
        ),
        (
            SupportedCity.BANGKOK,
            "Asia/Bangkok",
            "t062_itinerary_partial_bangkok.json",
            1,
        ),
    ],
)
def test_public_model_and_route_match_shared_safe_contract_fixture(
    city: SupportedCity,
    timezone: str,
    fixture_name: str,
    expected_item_count: int,
) -> None:
    expected = _synthetic_contract_response(city)
    fixture = _contract_fixture(fixture_name)
    request = ItineraryDraftGenerationRequest(
        city=city,
        local_date=date(2026, 8, 2),
        timezone=timezone,
        start_local_time=time(9, 0),
        end_local_time=time(17, 0),
        maximum_stops=2,
        notes=None,
        locale="vi-VN",
        client_mode="online",
        latitude=None,
        longitude=None,
    )

    assert expected.model_dump_json() == fixture
    expected.validate_against(request)
    with _client(CapturingGenerator(expected)) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(
                city=city.value,
                local_date="2026-08-02",
                timezone=timezone,
                maximum_stops=2,
                notes=None,
                latitude=None,
                longitude=None,
            ),
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.text == fixture
    body = response.json()
    assert body["local_date"] == "2026-08-02"
    assert body["start_local_time"] == "09:00:00"
    assert body["end_local_time"] == "17:00:00"
    assert len(body["items"]) == expected_item_count
    assert body["assumptions"] == ["Giả định thử nghiệm an toàn."]
    assert all(
        item["start_local_time"].endswith(":00")
        and item["end_local_time"].endswith(":00")
        for item in body["items"]
    )
    serialized = json.dumps(body, ensure_ascii=False)
    for forbidden in (
        "latitude",
        "longitude",
        "coordinates",
        "distance",
        "provider",
        "candidate_id",
        "evidence_id",
        "claim_id",
        "source_id",
        "request_id",
        "trace_id",
        "saved_itinerary_id",
    ):
        assert forbidden not in serialized


def test_public_success_partial_and_failed_response_closure() -> None:
    request = ItineraryDraftGenerationRequest.model_validate(
        {
            "city": SupportedCity.HCMC,
            "local_date": date(2026, 8, 1),
            "timezone": "Asia/Ho_Chi_Minh",
            "start_local_time": time(9, 0),
            "end_local_time": time(17, 0),
            "maximum_stops": 4,
            "notes": None,
            "locale": "vi-VN",
            "client_mode": "online",
            "latitude": None,
            "longitude": None,
        }
    )
    success = _success_response(request)
    partial = success.model_copy(
        update={
            "status": ItineraryDraftGenerationStatus.PARTIAL,
            "warnings": ("Hãy kiểm tra thông tin thực tế trước khi đi.",),
        }
    )
    failed = ItineraryDraftGenerationResponse(
        status=ItineraryDraftGenerationStatus.FAILED,
        city=request.city,
        local_date=request.local_date,
        timezone=request.timezone,
        start_local_time=request.start_local_time,
        end_local_time=request.end_local_time,
        failure_category=ItineraryDraftFailureCategory.INSUFFICIENT_CANDIDATES,
        retryable=False,
    )
    for expected in (success, partial, failed):
        with _client(CapturingGenerator(expected)) as client:
            response = client.post(
                "/v1/itinerary-drafts/generate",
                json=_payload(notes=None, latitude=None, longitude=None),
                headers=_headers(),
            )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == expected.status.value
        forbidden = {
            "coordinates",
            "distance",
            "provider",
            "candidate_id",
            "evidence_id",
            "claim_id",
            "source_id",
            "firebase",
            "trace_id",
            "agent",
            "stage",
            "usage",
            "prompt",
            "saved_itinerary_id",
        }
        assert not forbidden.intersection(body)


def test_cancellation_and_unexpected_failures_remain_controlled() -> None:
    async def cancelled_call() -> None:
        app = create_app(
            _settings(),
            token_verifier=TokenVerifier(),
            poi_provider=UnusedPoiProvider(),
            itinerary_generator=CancellingGenerator(),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            await client.post(
                "/v1/itinerary-drafts/generate",
                json=_payload(),
                headers=_headers(),
            )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(cancelled_call())

    with _client(UnexpectedGenerator()) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(),
            headers=_headers(),
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private note" not in response.text
    assert "RuntimeError" not in response.text


def test_logs_exclude_form_result_token_identity_and_coordinates(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    with _client(CapturingGenerator()) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(),
            headers=_headers(),
        )
    assert response.status_code == 200
    logs = caplog.text
    for private in (
        PRIVATE_NOTE,
        TOKEN,
        UID,
        "10.776",
        "106.7",
        "Bưu điện Trung tâm Sài Gòn",
        "hcmc",
        "2026-08-01",
        "09:00",
        "17:00",
    ):
        assert private not in logs


def test_production_dependency_owns_one_read_only_request_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = TrackingDatabaseRuntime()
    generator = CapturingGenerator()
    monkeypatch.setattr(
        "app.main.create_database_runtime",
        lambda database_url: runtime,
    )
    monkeypatch.setattr(
        "app.main.StructuredItineraryGenerationService",
        lambda candidates, itinerary: generator,
    )
    app = create_app(_settings(), token_verifier=TokenVerifier())

    with TestClient(app) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(),
            headers=_headers(),
        )
        assert response.status_code == 200
        assert len(runtime.session_factory.contexts) == 1
        context = runtime.session_factory.contexts[0]
        assert context.enter_count == 1
        assert context.exit_count == 1
        assert context.session.commit_count == 0

    assert runtime.dispose_count == 1


def test_injected_generator_and_provider_do_not_start_database_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_runtime(database_url: str) -> object:
        del database_url
        raise AssertionError("database runtime must remain isolated")

    monkeypatch.setattr("app.main.create_database_runtime", unexpected_runtime)
    with _client(CapturingGenerator()) as client:
        response = client.post(
            "/v1/itinerary-drafts/generate",
            json=_payload(),
            headers=_headers(),
        )

    assert response.status_code == 200
