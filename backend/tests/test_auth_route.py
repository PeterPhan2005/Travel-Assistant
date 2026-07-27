"""Deterministic tests for the HTTP Bearer dependency and protected route."""

import asyncio
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.auth.models import (
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
    InvalidAuthenticationTokenError,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.middleware.request_id import REQUEST_ID_HEADER

TEST_DATABASE_URL = "postgresql+asyncpg://unused:unused@localhost/unused"
TEST_FIREBASE_PROJECT_ID = "travel-assistant-test"
SENTINEL_TOKEN = "sentinel-token-fragment-NEVER-EXPOSE"


class StaticVerifier:
    """Return or raise one deterministic verification outcome."""

    def __init__(
        self,
        outcome: AuthenticatedPrincipal | Exception,
    ) -> None:
        self._outcome = outcome

    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        del raw_token
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


class TokenMappedVerifier:
    """Map each request token directly to an isolated principal."""

    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        await asyncio.sleep(0)
        return AuthenticatedPrincipal(uid=f"uid-for-{raw_token}")


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr(TEST_DATABASE_URL),
        firebase_project_id=TEST_FIREBASE_PROJECT_ID,
        application_environment=ApplicationEnvironment.TEST,
    )


def _client(
    verifier: StaticVerifier | TokenMappedVerifier,
) -> TestClient:
    return TestClient(
        create_app(_settings(), token_verifier=verifier),
        raise_server_exceptions=False,
    )


def _assert_standard_authentication_error(
    response_body: object,
    *,
    actual_status_code: int,
    response_request_id: str,
    status_code: int,
    code: str,
) -> None:
    assert actual_status_code == status_code
    assert isinstance(response_body, dict)
    body = response_body
    assert set(body) == {"error"}
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert error["request_id"] == response_request_id
    assert "detail" not in body


@pytest.mark.parametrize(
    ("authorization", "supplied_request_id"),
    [
        (None, None),
        ("Basic opaque-credential", None),
        ("Bearer", None),
        ("Bearer ", None),
        ("Bearer token with spaces", "safe-auth-request-001"),
        ("\tBearer\tcredential", None),
    ],
)
def test_missing_or_malformed_bearer_credentials_return_401(
    authorization: str | None,
    supplied_request_id: str | None,
) -> None:
    headers: dict[str, str] = {}
    if authorization is not None:
        headers["Authorization"] = authorization
    if supplied_request_id is not None:
        headers[REQUEST_ID_HEADER] = supplied_request_id

    with _client(
        StaticVerifier(AuthenticatedPrincipal(uid="unused"))
    ) as client:
        response = client.get("/auth/me", headers=headers)

    _assert_standard_authentication_error(
        response.json(),
        actual_status_code=response.status_code,
        response_request_id=response.headers[REQUEST_ID_HEADER],
        status_code=401,
        code="authentication_required",
    )
    assert response.headers["WWW-Authenticate"] == "Bearer"
    if supplied_request_id is not None:
        assert response.headers[REQUEST_ID_HEADER] == supplied_request_id


def test_valid_token_returns_only_uid() -> None:
    expected_uid = "firebase-user-123"

    with _client(
        StaticVerifier(AuthenticatedPrincipal(uid=expected_uid))
    ) as client:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {SENTINEL_TOKEN}"},
        )

    assert response.status_code == 200
    assert response.json() == {"uid": expected_uid}
    assert SENTINEL_TOKEN not in response.text
    assert "email" not in response.text
    assert "claims" not in response.text


@pytest.mark.parametrize(
    "failure",
    [
        InvalidAuthenticationTokenError(),
        InvalidAuthenticationTokenError("expired"),
        InvalidAuthenticationTokenError("revoked"),
    ],
)
def test_invalid_expired_or_revoked_token_returns_401(
    failure: Exception,
) -> None:
    with _client(StaticVerifier(failure)) as client:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {SENTINEL_TOKEN}"},
        )

    _assert_standard_authentication_error(
        response.json(),
        actual_status_code=response.status_code,
        response_request_id=response.headers[REQUEST_ID_HEADER],
        status_code=401,
        code="invalid_token",
    )
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unavailable_verifier_returns_controlled_503() -> None:
    with _client(
        StaticVerifier(AuthenticationServiceUnavailableError("private"))
    ) as client:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {SENTINEL_TOKEN}"},
        )

    _assert_standard_authentication_error(
        response.json(),
        actual_status_code=response.status_code,
        response_request_id=response.headers[REQUEST_ID_HEADER],
        status_code=503,
        code="authentication_unavailable",
    )
    assert "private" not in response.text


def test_unexpected_verifier_failure_is_sanitized(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="travel_assistant.api")

    with _client(
        StaticVerifier(RuntimeError(f"SDK failed for {SENTINEL_TOKEN}"))
    ) as client:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {SENTINEL_TOKEN}"},
        )

    _assert_standard_authentication_error(
        response.json(),
        actual_status_code=response.status_code,
        response_request_id=response.headers[REQUEST_ID_HEADER],
        status_code=500,
        code="internal_error",
    )
    combined_logs = "\n".join(record.getMessage() for record in caplog.records)
    for sensitive_text in (
        SENTINEL_TOKEN,
        "sentinel-token-fragment",
        "Authorization",
    ):
        assert sensitive_text not in response.text
        assert sensitive_text not in str(response.headers)
        assert sensitive_text not in combined_logs


def test_expected_authentication_failures_do_not_log_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)

    with _client(
        StaticVerifier(InvalidAuthenticationTokenError(SENTINEL_TOKEN))
    ) as client:
        missing_response = client.get("/auth/me")
        invalid_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {SENTINEL_TOKEN}"},
        )

    combined_responses = f"{missing_response.text}\n{invalid_response.text}"
    combined_logs = "\n".join(record.getMessage() for record in caplog.records)
    for sensitive_text in (
        SENTINEL_TOKEN,
        "sentinel-token-fragment",
        "Authorization",
    ):
        assert sensitive_text not in combined_responses
        assert sensitive_text not in combined_logs


def test_concurrent_requests_do_not_share_principal_state() -> None:
    app = create_app(_settings(), token_verifier=TokenMappedVerifier())

    async def send_requests() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await asyncio.gather(
                *(
                    client.get(
                        "/auth/me",
                        headers={"Authorization": f"Bearer token-{index}"},
                    )
                    for index in range(20)
                )
            )

    responses = asyncio.run(send_requests())

    assert [response.json()["uid"] for response in responses] == [
        f"uid-for-token-{index}" for index in range(20)
    ]


def test_fake_verifier_keeps_health_public_and_bypasses_firebase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_initialized(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("Firebase Admin must not initialize for an injected fake")

    monkeypatch.setattr(
        "firebase_admin.initialize_app",
        fail_if_initialized,
    )
    with _client(
        StaticVerifier(AuthenticatedPrincipal(uid="unused"))
    ) as client:
        health_response = client.get("/health")
        auth_response = client.get("/auth/me")

    assert health_response.status_code == 200
    assert auth_response.status_code == 401


def test_factories_with_different_verifiers_remain_independent() -> None:
    first_client = _client(
        StaticVerifier(AuthenticatedPrincipal(uid="first-user"))
    )
    second_client = _client(
        StaticVerifier(AuthenticatedPrincipal(uid="second-user"))
    )

    with first_client, second_client:
        first_response = first_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer first-token"},
        )
        second_response = second_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer second-token"},
        )

    assert first_response.json() == {"uid": "first-user"}
    assert second_response.json() == {"uid": "second-user"}
