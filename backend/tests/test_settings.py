"""Tests for typed application settings."""

import pytest
from pydantic import SecretStr, ValidationError

from app.core.settings import ApplicationEnvironment, LogLevel, Settings

LOCAL_DATABASE_URL = (
    "postgresql+asyncpg://travel_assistant:"
    "local_dev_only_change_me@localhost:5433/travel_assistant"
)


def test_valid_local_settings() -> None:
    settings = Settings(
        database_url=SecretStr(LOCAL_DATABASE_URL),
        application_environment=ApplicationEnvironment.TEST,
        log_level=LogLevel.DEBUG,
    )

    assert settings.database_url.get_secret_value() == LOCAL_DATABASE_URL
    assert settings.application_environment is ApplicationEnvironment.TEST
    assert settings.log_level is LogLevel.DEBUG


def test_settings_load_database_url_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", LOCAL_DATABASE_URL)

    settings = Settings()  # type: ignore[call-arg]

    assert settings.database_url.get_secret_value() == LOCAL_DATABASE_URL


def test_missing_database_url_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings()  # type: ignore[call-arg]


def test_blank_database_url_fails() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        Settings(database_url=SecretStr("   "))


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///local.db",
        "postgresql://localhost/travel_assistant",
        "https://localhost/travel_assistant",
    ],
)
def test_unsupported_database_url_fails(database_url: str) -> None:
    with pytest.raises(
        ValidationError,
        match=r"must use the postgresql\+asyncpg scheme",
    ):
        Settings(database_url=SecretStr(database_url))


def test_application_environment_is_constrained() -> None:
    with pytest.raises(ValidationError, match="application_environment"):
        Settings.model_validate(
            {
                "database_url": LOCAL_DATABASE_URL,
                "application_environment": "demo",
            }
        )


def test_database_url_is_redacted_from_settings_output() -> None:
    settings = Settings(database_url=SecretStr(LOCAL_DATABASE_URL))

    rendered_settings = f"{settings!r}\n{settings.model_dump_json()}"

    assert LOCAL_DATABASE_URL not in rendered_settings
    assert "local_dev_only_change_me" not in rendered_settings
