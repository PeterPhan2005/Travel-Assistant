"""Tests for request correlation and the public JSON error contract."""

from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.middleware.request_id import MAX_REQUEST_ID_LENGTH, REQUEST_ID_HEADER

TEST_DATABASE_URL = "postgresql+asyncpg://unused:unused@localhost/unused"
TEST_FIREBASE_PROJECT_ID = "travel-assistant-test"


def _client() -> TestClient:
    settings = Settings(
        database_url=SecretStr(TEST_DATABASE_URL),
        firebase_project_id=TEST_FIREBASE_PROJECT_ID,
        application_environment=ApplicationEnvironment.TEST,
    )
    app = create_app(settings)

    @app.get("/validated")
    async def validated(count: int) -> dict[str, int]:
        return {"count": count}

    @app.get("/controlled")
    async def controlled() -> None:
        raise HTTPException(status_code=418, detail="Controlled failure.")

    @app.get("/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("private traceback detail and database password")

    return TestClient(app, raise_server_exceptions=False)


def _assert_matching_request_id(response_body: object, header: str) -> None:
    assert isinstance(response_body, dict)
    error = response_body.get("error")
    assert isinstance(error, dict)
    assert error.get("request_id") == header


def test_missing_request_id_generates_uuid_on_success() -> None:
    with _client() as client:
        response = client.get("/health")

    request_id = response.headers[REQUEST_ID_HEADER]
    assert request_id
    assert str(UUID(request_id)) == request_id


def test_valid_supplied_request_id_is_preserved() -> None:
    supplied_request_id = "mobile.session_123:attempt-4"

    with _client() as client:
        response = client.get(
            "/health",
            headers={REQUEST_ID_HEADER: supplied_request_id},
        )

    assert response.headers[REQUEST_ID_HEADER] == supplied_request_id


@pytest.mark.parametrize(
    "supplied_request_id",
    [
        "contains spaces",
        "<script>",
        "x" * (MAX_REQUEST_ID_LENGTH + 1),
        "",
    ],
)
def test_invalid_supplied_request_id_is_replaced(
    supplied_request_id: str,
) -> None:
    with _client() as client:
        response = client.get(
            "/health",
            headers={REQUEST_ID_HEADER: supplied_request_id},
        )

    response_request_id = response.headers[REQUEST_ID_HEADER]
    assert response_request_id != supplied_request_id
    assert str(UUID(response_request_id)) == response_request_id


def test_unknown_route_uses_standard_error_envelope() -> None:
    with _client() as client:
        response = client.get("/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    _assert_matching_request_id(
        response.json(),
        response.headers[REQUEST_ID_HEADER],
    )


def test_validation_failure_uses_sanitized_error_envelope() -> None:
    invalid_value = "sensitive-invalid-count"

    with _client() as client:
        response = client.get("/validated", params={"count": invalid_value})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"] == [
        {
            "location": ["query", "count"],
            "message": "Invalid value.",
            "type": "int_parsing",
        }
    ]
    assert invalid_value not in response.text
    _assert_matching_request_id(body, response.headers[REQUEST_ID_HEADER])


def test_controlled_http_exception_preserves_status_and_message() -> None:
    with _client() as client:
        response = client.get("/controlled")

    assert response.status_code == 418
    assert response.json()["error"]["code"] == "http_error"
    assert response.json()["error"]["message"] == "Controlled failure."
    _assert_matching_request_id(
        response.json(),
        response.headers[REQUEST_ID_HEADER],
    )


def test_unexpected_exception_is_sanitized() -> None:
    with _client() as client:
        response = client.get("/unexpected")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["message"] == (
        "An internal server error occurred."
    )
    assert "private traceback detail" not in response.text
    assert "database password" not in response.text
    assert "RuntimeError" not in response.text
    _assert_matching_request_id(
        response.json(),
        response.headers[REQUEST_ID_HEADER],
    )
