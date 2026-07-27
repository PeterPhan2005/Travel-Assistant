"""Deterministic HTTP contract tests for GET /pois/nearby."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from types import TracebackType
from typing import Protocol

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl, SecretStr
from starlette.types import Message, Receive, Scope, Send

from app.auth.models import (
    AuthenticatedPrincipal,
    InvalidAuthenticationTokenError,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.middleware.request_id import REQUEST_ID_HEADER
from app.middleware.privacy import RedactAccessLogQueryMiddleware
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
    PriceLevel,
    SourceReference,
    SupportedCity,
    build_normalized_poi_id,
)

TEST_DATABASE_URL = (
    "postgresql+asyncpg://unused:never-connect@database.invalid:9999/unused"
)
TEST_FIREBASE_PROJECT_ID = "travel-assistant-test"
SENTINEL_TOKEN = "nearby-token-fragment-NEVER-EXPOSE"
FRESHNESS = datetime(2026, 7, 1, 2, 3, 4, tzinfo=timezone.utc)
QueryValue = str | int | float | bool | None


class ResponseLike(Protocol):
    """Small response surface shared by httpx and TestClient."""

    @property
    def status_code(self) -> int:
        """Return the HTTP status."""
        ...

    @property
    def headers(self) -> HeadersLike:
        """Return case-insensitive response headers."""
        ...

    def json(self) -> object:
        """Decode the response JSON body."""
        ...


class HeadersLike(Protocol):
    """Header lookup surface shared by both response implementations."""

    def __getitem__(self, key: str) -> str:
        """Return one response header."""
        ...


class RecordingProvider:
    """Record normalized requests and return one deterministic outcome."""

    def __init__(
        self,
        outcome: PoiResultEnvelope | BaseException,
    ) -> None:
        self.outcome = outcome
        self.requests: list[PoiDiscoveryRequest] = []

    async def discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        self.requests.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class RecordingVerifier:
    """Record only whether verification was requested."""

    def __init__(
        self,
        outcome: AuthenticatedPrincipal | Exception,
    ) -> None:
        self.outcome = outcome
        self.call_count = 0

    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        self.call_count += 1
        del raw_token
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class TrackingSession:
    """Record forbidden transaction behavior."""

    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class TrackingSessionContext:
    """Record request-session entry and guaranteed closure."""

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
    """Return a fresh, observable request session context."""

    def __init__(self) -> None:
        self.contexts: list[TrackingSessionContext] = []

    def __call__(self) -> TrackingSessionContext:
        context = TrackingSessionContext()
        self.contexts.append(context)
        return context


class TrackingDatabaseRuntime:
    """Test double for app-scoped runtime disposal."""

    def __init__(self) -> None:
        self.session_factory = TrackingSessionFactory()
        self.dispose_count = 0

    async def dispose(self) -> None:
        self.dispose_count += 1


def _settings(
    database_url: str = TEST_DATABASE_URL,
) -> Settings:
    return Settings(
        database_url=SecretStr(database_url),
        firebase_project_id=TEST_FIREBASE_PROJECT_ID,
        application_environment=ApplicationEnvironment.TEST,
    )


def _item(
    *,
    provider_id: str = "hcmc-poi-test",
    city: SupportedCity = SupportedCity.HCMC,
    include_optional_facts: bool = True,
) -> PoiDiscoveryResult:
    source = SourceReference(
        source_id=f"{provider_id}-source",
        source_type="official_operator",
        label="Official source",
        publisher="Test publisher",
        url=HttpUrl("https://example.test/source"),
        published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        retrieved_at=FRESHNESS,
    )
    return PoiDiscoveryResult(
        id=build_normalized_poi_id(
            PoiProviderKind.CURATED,
            provider_id,
        ),
        provider=PoiProviderKind.CURATED,
        provider_id=provider_id,
        canonical_name="Normalized destination",
        city=city,
        category="museum",
        address="Public destination address",
        coordinates=Coordinates(latitude=10.123, longitude=106.456),
        distance_metres=321.5,
        rating=Decimal("4.5") if include_optional_facts else None,
        rating_count=100 if include_optional_facts else None,
        price_level=(
            PriceLevel.MODERATE if include_optional_facts else None
        ),
        opening_hours_summary=(
            "Open during published hours."
            if include_optional_facts
            else None
        ),
        sources=(source,),
        retrieved_at=FRESHNESS,
        is_curated=True,
        is_externally_supplied=False,
    )


def _result(
    *,
    item: PoiDiscoveryResult | None = None,
    is_complete: bool = True,
) -> PoiResultEnvelope:
    items = (item or _item(),)
    return PoiResultEnvelope(
        provider=PoiProviderKind.CURATED,
        items=items,
        returned_count=len(items),
        is_complete=is_complete,
        freshness_at=FRESHNESS,
    )


def _client(
    provider: RecordingProvider,
    verifier: RecordingVerifier | None = None,
) -> TestClient:
    resolved_verifier = verifier or RecordingVerifier(
        AuthenticatedPrincipal(uid="unused-nearby-user")
    )
    return TestClient(
        create_app(
            _settings(),
            token_verifier=resolved_verifier,
            poi_provider=provider,
        ),
        raise_server_exceptions=False,
    )


def _params(**updates: QueryValue) -> dict[str, QueryValue]:
    values: dict[str, QueryValue] = {
        "city": "hcmc",
        "latitude": 10.7,
        "longitude": 106.7,
    }
    values.update(updates)
    return values


def _assert_standard_error(
    response: ResponseLike,
    *,
    status_code: int,
    code: str,
) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert isinstance(body, dict)
    assert set(body) == {"error"}
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert (
        error["request_id"]
        == response.headers[REQUEST_ID_HEADER]
    )


def test_valid_hcmc_request_uses_defaults_and_returns_normalized_data() -> None:
    provider = RecordingProvider(_result())

    with _client(provider) as client:
        response = client.get("/pois/nearby", params=_params())

    assert response.status_code == 200
    assert provider.requests == [
        PoiDiscoveryRequest(
            city=SupportedCity.HCMC,
            origin=Coordinates(latitude=10.7, longitude=106.7),
            radius_metres=5_000,
            limit=5,
        )
    ]
    body = response.json()
    assert body["provider"] == "curated"
    assert body["returned_count"] == len(body["items"]) == 1
    assert body["is_complete"] is True
    assert body["freshness_at"] == "2026-07-01T02:03:04Z"
    item = body["items"][0]
    assert item["id"] == "curated:hcmc-poi-test"
    assert item["provider_id"] == "hcmc-poi-test"
    assert item["distance_metres"] == 321.5
    assert item["coordinates"] == {
        "latitude": 10.123,
        "longitude": 106.456,
    }
    assert item["sources"][0]["retrieved_at"] == (
        "2026-07-01T02:03:04Z"
    )
    assert item["rating"] == "4.5"
    assert item["price_level"] == "moderate"


def test_valid_bangkok_explicit_bounds_and_filters_are_normalized() -> None:
    item = _item(
        provider_id="bkk-poi-test",
        city=SupportedCity.BANGKOK,
    )
    provider = RecordingProvider(_result(item=item, is_complete=False))

    with _client(provider) as client:
        response = client.get(
            "/pois/nearby",
            params=_params(
                city="bkk",
                latitude=13.75,
                longitude=100.5,
                radius_metres=50_000,
                limit=20,
                query="  Wat   Pho ",
                category="  MuSeUm ",
            ),
        )

    assert response.status_code == 200
    request = provider.requests[0]
    assert request.city is SupportedCity.BANGKOK
    assert request.origin == Coordinates(
        latitude=13.75,
        longitude=100.5,
    )
    assert request.radius_metres == 50_000
    assert request.limit == 20
    assert request.query == "Wat Pho"
    assert request.category == "museum"
    assert response.json()["is_complete"] is False


def test_blank_filters_become_none_through_provider_contract() -> None:
    provider = RecordingProvider(_result())

    with _client(provider) as client:
        response = client.get(
            "/pois/nearby",
            params=_params(query=" \n ", category="\t "),
        )

    assert response.status_code == 200
    assert provider.requests[0].query is None
    assert provider.requests[0].category is None


@pytest.mark.parametrize(
    ("updates", "field"),
    [
        ({"city": "saigon"}, "city"),
        ({"latitude": -90.1}, "latitude"),
        ({"latitude": 90.1}, "latitude"),
        ({"longitude": -180.1}, "longitude"),
        ({"longitude": 180.1}, "longitude"),
        ({"latitude": "nan"}, "latitude"),
        ({"latitude": "inf"}, "latitude"),
        ({"longitude": "-inf"}, "longitude"),
        ({"radius_metres": 0}, "radius_metres"),
        ({"radius_metres": -1}, "radius_metres"),
        ({"radius_metres": 50_001}, "radius_metres"),
        ({"limit": 0}, "limit"),
        ({"limit": -1}, "limit"),
        ({"limit": 21}, "limit"),
    ],
)
def test_invalid_query_values_use_standard_validation_envelope(
    updates: dict[str, QueryValue],
    field: str,
) -> None:
    provider = RecordingProvider(_result())

    with _client(provider) as client:
        response = client.get(
            "/pois/nearby",
            params=_params(**updates),
        )

    _assert_standard_error(
        response,
        status_code=422,
        code="validation_error",
    )
    assert response.json()["error"]["details"][0]["location"] == [
        "query",
        field,
    ]
    assert provider.requests == []


@pytest.mark.parametrize(
    ("updates", "field"),
    [
        ({"radius_metres": "1.5"}, "radius_metres"),
        ({"limit": "1.5"}, "limit"),
    ],
)
def test_radius_and_limit_require_integers(
    updates: dict[str, QueryValue],
    field: str,
) -> None:
    provider = RecordingProvider(_result())

    with _client(provider) as client:
        response = client.get(
            "/pois/nearby",
            params=_params(**updates),
        )

    _assert_standard_error(
        response,
        status_code=422,
        code="validation_error",
    )
    assert response.json()["error"]["details"][0]["location"] == [
        "query",
        field,
    ]


def test_response_omits_origin_and_has_no_payload_escape_hatches() -> None:
    provider = RecordingProvider(
        _result(item=_item(include_optional_facts=False))
    )

    with _client(provider) as client:
        response = client.get(
            "/pois/nearby",
            params=_params(latitude=1.23456, longitude=2.34567),
        )

    assert response.status_code == 200
    body = response.json()
    serialized = response.text
    assert "1.23456" not in serialized
    assert "2.34567" not in serialized
    assert "origin" not in serialized
    item = body["items"][0]
    for field in (
        "raw",
        "payload",
        "metadata",
        "description",
        "menu",
        "narration",
        "uid",
    ):
        assert field not in item
    for field in (
        "rating",
        "rating_count",
        "price_level",
        "opening_hours_summary",
    ):
        assert item[field] is None


def test_missing_authorization_is_anonymous_and_skips_verifier() -> None:
    provider = RecordingProvider(_result())
    verifier = RecordingVerifier(
        AuthenticatedPrincipal(uid="must-not-be-used")
    )

    with _client(provider, verifier) as client:
        response = client.get("/pois/nearby", params=_params())

    assert response.status_code == 200
    assert verifier.call_count == 0
    assert "uid" not in response.text


def test_valid_supplied_token_is_accepted_without_personalization() -> None:
    provider = RecordingProvider(_result())
    verifier = RecordingVerifier(
        AuthenticatedPrincipal(uid="private-uid")
    )

    with _client(provider, verifier) as client:
        response = client.get(
            "/pois/nearby",
            params=_params(),
            headers={"Authorization": f"Bearer {SENTINEL_TOKEN}"},
        )

    assert response.status_code == 200
    assert verifier.call_count == 1
    assert "private-uid" not in response.text
    assert SENTINEL_TOKEN not in response.text


@pytest.mark.parametrize(
    ("authorization", "expected_code", "verifier_calls"),
    [
        ("Basic opaque", "authentication_required", 0),
        ("Bearer", "authentication_required", 0),
        ("Bearer token with spaces", "authentication_required", 0),
        (
            f"Bearer {SENTINEL_TOKEN}",
            "invalid_token",
            1,
        ),
    ],
)
def test_invalid_supplied_credentials_are_not_anonymous(
    authorization: str,
    expected_code: str,
    verifier_calls: int,
) -> None:
    provider = RecordingProvider(_result())
    verifier = RecordingVerifier(InvalidAuthenticationTokenError("private"))

    with _client(provider, verifier) as client:
        response = client.get(
            "/pois/nearby",
            params=_params(),
            headers={"Authorization": authorization},
        )

    _assert_standard_error(
        response,
        status_code=401,
        code=expected_code,
    )
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert verifier.call_count == verifier_calls
    assert provider.requests == []


def test_auth_me_remains_strictly_authenticated() -> None:
    provider = RecordingProvider(_result())
    verifier = RecordingVerifier(
        AuthenticatedPrincipal(uid="unused")
    )

    with _client(provider, verifier) as client:
        response = client.get("/auth/me")

    _assert_standard_error(
        response,
        status_code=401,
        code="authentication_required",
    )
    assert verifier.call_count == 0


@pytest.mark.parametrize(
    ("provider_code", "status_code", "application_code"),
    [
        (
            ProviderErrorCode.INVALID_REQUEST,
            400,
            "poi_provider_invalid_request",
        ),
        (
            ProviderErrorCode.RATE_LIMITED,
            429,
            "poi_provider_rate_limited",
        ),
        (ProviderErrorCode.TIMEOUT, 503, "poi_provider_timeout"),
        (
            ProviderErrorCode.UNAVAILABLE,
            503,
            "poi_provider_unavailable",
        ),
        (
            ProviderErrorCode.MISCONFIGURED,
            503,
            "poi_provider_misconfigured",
        ),
        (
            ProviderErrorCode.UNSUPPORTED,
            501,
            "poi_provider_unsupported",
        ),
        (
            ProviderErrorCode.INVALID_RESPONSE,
            502,
            "poi_provider_invalid_response",
        ),
        (ProviderErrorCode.INTERNAL, 500, "poi_provider_internal"),
    ],
)
def test_provider_failures_map_to_sanitized_http_errors(
    provider_code: ProviderErrorCode,
    status_code: int,
    application_code: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    provider = RecordingProvider(
        PoiProviderError(
            ProviderFailure.for_code(
                PoiProviderKind.CURATED,
                provider_code,
            )
        )
    )
    request_id = "nearby-provider-error-001"

    with _client(provider) as client:
        response = client.get(
            "/pois/nearby",
            params=_params(),
            headers={REQUEST_ID_HEADER: request_id},
        )

    _assert_standard_error(
        response,
        status_code=status_code,
        code=application_code,
    )
    assert response.headers[REQUEST_ID_HEADER] == request_id
    combined_logs = "\n".join(
        record.getMessage() for record in caplog.records
    )
    for private_value in (
        TEST_DATABASE_URL,
        "asyncpg",
        "SELECT ",
        "PoiProviderError",
    ):
        assert private_value not in response.text
        assert private_value not in combined_logs
    assert "retry-after" not in response.headers


def test_unexpected_provider_failure_is_sanitized() -> None:
    provider = RecordingProvider(
        RuntimeError("private SQL and provider payload")
    )

    with _client(provider) as client:
        response = client.get("/pois/nearby", params=_params())

    _assert_standard_error(
        response,
        status_code=500,
        code="internal_error",
    )
    assert "private SQL" not in response.text
    assert "RuntimeError" not in response.text


def test_caller_cancellation_propagates() -> None:
    provider = RecordingProvider(asyncio.CancelledError())
    app = create_app(
        _settings(),
        token_verifier=RecordingVerifier(
            AuthenticatedPrincipal(uid="unused")
        ),
        poi_provider=provider,
    )

    async def call() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            await client.get("/pois/nearby", params=_params())

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(call())


def test_fake_provider_app_never_creates_database_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_created(database_url: str) -> None:
        del database_url
        pytest.fail("Injected provider must bypass database runtime creation")

    monkeypatch.setattr(
        "app.main.create_database_runtime",
        fail_if_created,
    )
    provider = RecordingProvider(_result())

    with _client(provider) as client:
        health = client.get("/health")
        nearby = client.get("/pois/nearby", params=_params())

    assert health.status_code == 200
    assert nearby.status_code == 200


@pytest.mark.parametrize(
    ("outcome", "expected_status"),
    [
        (_result(), 200),
        (
            PoiProviderError(
                ProviderFailure.for_code(
                    PoiProviderKind.CURATED,
                    ProviderErrorCode.UNAVAILABLE,
                )
            ),
            503,
        ),
    ],
)
def test_production_request_session_closes_without_commit(
    outcome: PoiResultEnvelope | BaseException,
    expected_status: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = TrackingDatabaseRuntime()
    provider = RecordingProvider(outcome)

    def runtime_factory(database_url: str) -> TrackingDatabaseRuntime:
        assert database_url == TEST_DATABASE_URL
        return runtime

    def curated_provider(session: object) -> RecordingProvider:
        assert isinstance(session, TrackingSession)
        return provider

    monkeypatch.setattr(
        "app.main.create_database_runtime",
        runtime_factory,
    )
    monkeypatch.setattr("app.main.CuratedPoiProvider", curated_provider)
    app = create_app(
        _settings(),
        token_verifier=RecordingVerifier(
            AuthenticatedPrincipal(uid="unused")
        ),
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/pois/nearby", params=_params())
        assert runtime.dispose_count == 0

    assert response.status_code == expected_status
    assert len(runtime.session_factory.contexts) == 1
    context = runtime.session_factory.contexts[0]
    assert context.enter_count == 1
    assert context.exit_count == 1
    assert context.session.commit_count == 0
    assert runtime.dispose_count == 1


def test_only_canonical_nearby_route_exists() -> None:
    provider = RecordingProvider(_result())

    with _client(provider) as client:
        nearby_alias = client.get("/nearby")
        pois_alias = client.get("/pois")

    assert nearby_alias.status_code == 404
    assert pois_alias.status_code == 404


def test_access_log_scope_is_redacted_after_query_is_consumed() -> None:
    observed_query: bytes | None = None
    query_at_response_start: bytes | None = None

    async def downstream(
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        del receive
        nonlocal observed_query
        observed_query = scope["query_string"]
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        nonlocal query_at_response_start
        if message["type"] == "http.response.start":
            query_at_response_start = scope["query_string"]

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/pois/nearby",
        "raw_path": b"/pois/nearby",
        "query_string": (
            b"latitude=10.7&longitude=106.7&query=private"
        ),
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("127.0.0.1", 8000),
    }

    asyncio.run(
        RedactAccessLogQueryMiddleware(downstream)(
            scope,
            receive,
            send,
        )
    )

    assert observed_query == (
        b"latitude=10.7&longitude=106.7&query=private"
    )
    assert query_at_response_start == b""
