"""Database-only environment boundary used by migration commands."""

import os

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ASYNC_POSTGRESQL_DRIVER = "postgresql+asyncpg"


class DatabaseConfigurationError(RuntimeError):
    """Raised when migration database configuration is missing or invalid."""


def get_database_url() -> str:
    """Return a validated async PostgreSQL URL without exposing its value."""
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.strip():
        raise DatabaseConfigurationError("DATABASE_URL is required")

    try:
        parsed_url = make_url(database_url)
    except ArgumentError as error:
        raise DatabaseConfigurationError(
            "DATABASE_URL must be a valid SQLAlchemy URL"
        ) from error

    if parsed_url.drivername != ASYNC_POSTGRESQL_DRIVER:
        raise DatabaseConfigurationError(
            "DATABASE_URL must use the postgresql+asyncpg driver"
        )
    return database_url
