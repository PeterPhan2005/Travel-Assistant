"""Tests for the application factory and liveness endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app

TEST_DATABASE_URL = (
    "postgresql+asyncpg://unused:never-connect@database.invalid:9999/unused"
)
TEST_FIREBASE_PROJECT_ID = "travel-assistant-test"


def test_factory_creates_independent_fastapi_apps() -> None:
    settings = Settings(
        database_url=SecretStr(TEST_DATABASE_URL),
        firebase_project_id=TEST_FIREBASE_PROJECT_ID,
        application_environment=ApplicationEnvironment.TEST,
    )

    first_app = create_app(settings)
    second_app = create_app(settings)

    assert isinstance(first_app, FastAPI)
    assert isinstance(second_app, FastAPI)
    assert first_app is not second_app


def test_health_is_safe_liveness_without_database() -> None:
    settings = Settings(
        database_url=SecretStr(TEST_DATABASE_URL),
        firebase_project_id=TEST_FIREBASE_PROJECT_ID,
        application_name="Travel Assistant Test API",
        application_environment=ApplicationEnvironment.TEST,
        application_version="test-version",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Travel Assistant Test API",
        "environment": "test",
        "version": "test-version",
    }
    serialized_response = response.text
    assert TEST_DATABASE_URL not in serialized_response
    assert "never-connect" not in serialized_response
