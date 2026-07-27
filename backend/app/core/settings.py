"""Typed application settings loaded from the process environment."""

from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationEnvironment(StrEnum):
    """Supported service environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Supported standard-library logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Validated, immutable service configuration."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    database_url: SecretStr = Field(validation_alias="DATABASE_URL")
    firebase_project_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias="FIREBASE_PROJECT_ID",
    )
    application_name: str = Field(
        default="Travel Assistant API",
        min_length=1,
        max_length=100,
        validation_alias="APP_NAME",
    )
    application_environment: ApplicationEnvironment = Field(
        default=ApplicationEnvironment.DEVELOPMENT,
        validation_alias="APP_ENVIRONMENT",
    )
    application_version: str = Field(
        default="0.1.0",
        min_length=1,
        max_length=50,
        validation_alias="APP_VERSION",
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        validation_alias="LOG_LEVEL",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        """Require the async PostgreSQL URL shape planned for the backend."""
        raw_value = value.get_secret_value()
        if not raw_value.strip():
            raise ValueError("DATABASE_URL must not be blank")

        try:
            parsed_url = urlsplit(raw_value)
        except ValueError as error:
            raise ValueError("DATABASE_URL must be a valid URL") from error

        if parsed_url.scheme != "postgresql+asyncpg":
            raise ValueError(
                "DATABASE_URL must use the postgresql+asyncpg scheme"
            )
        return value

    @field_validator("firebase_project_id", mode="before")
    @classmethod
    def validate_firebase_project_id(cls, value: object) -> object:
        """Trim and reject a blank expected Firebase project identifier."""
        if not isinstance(value, str):
            return value
        project_id = value.strip()
        if not project_id:
            raise ValueError("FIREBASE_PROJECT_ID must not be blank")
        return project_id
