"""Disposable PostgreSQL integration tests for preference ownership/upserts."""

from __future__ import annotations

import asyncio
from datetime import datetime
import os
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar, cast
from uuid import uuid4

from alembic import command
from alembic.config import Config
import asyncpg  # type: ignore[import-untyped]
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

from app.auth.models import AuthenticatedPrincipal
from app.core.settings import ApplicationEnvironment, Settings
from app.db.runtime import create_database_runtime
from app.main import create_app
from app.preferences.contracts import (
    BudgetPreference,
    PreferenceDocument,
    TravelInterest,
    TravelPreferenceDocument,
    TravelPreferenceValuesV1,
)
from app.preferences.store import (
    PreferenceSchemaConflictError,
    PreferenceStoreError,
    SqlAlchemyPreferenceStore,
)
from app.providers.poi.models import PoiDiscoveryRequest, PoiResultEnvelope

ResultT = TypeVar("ResultT")


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _asyncpg_dsn(url: URL) -> str:
    return url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )


async def _create_database(base_url: URL, name: str) -> None:
    connection = await asyncpg.connect(_asyncpg_dsn(base_url))
    try:
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()
    database = await asyncpg.connect(
        _asyncpg_dsn(base_url.set(database=name))
    )
    try:
        await database.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    finally:
        await database.close()


async def _drop_database(base_url: URL, name: str) -> None:
    connection = await asyncpg.connect(_asyncpg_dsn(base_url))
    try:
        await connection.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1 AND pid <> pg_backend_pid()
            """,
            name,
        )
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}"')
    finally:
        await connection.close()


@contextmanager
def _migration_url(database_url: str) -> Iterator[None]:
    original = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original


@pytest.fixture
def preference_database_url() -> Iterator[str]:
    raw_base_url = os.environ.get("DATABASE_URL")
    if raw_base_url is None:
        pytest.skip("DATABASE_URL is required for real preference tests")
    base_url = make_url(raw_base_url)
    database_name = f"travel_assistant_t025_{uuid4().hex}"
    _run(_create_database(base_url, database_name))
    database_url = base_url.set(database=database_name).render_as_string(
        hide_password=False
    )
    try:
        with _migration_url(database_url):
            command.upgrade(Config("alembic.ini"), "head")
        yield database_url
    finally:
        _run(_drop_database(base_url, database_name))


class TokenVerifier:
    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(uid=f"firebase-{raw_token}")


class UnusedPoiProvider:
    async def discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        del request
        raise AssertionError("POI provider must not be called")


async def _counts(database_url: str) -> dict[str, int]:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    try:
        tables = (
            "users",
            "user_preferences",
            "trips",
            "itineraries",
            "pois",
        )
        return {
            table: cast(
                int,
                await connection.fetchval(f'SELECT count(*) FROM "{table}"'),
            )
            for table in tables
        }
    finally:
        await connection.close()


def test_authenticated_api_persists_replaces_and_isolates_owners(
    preference_database_url: str,
) -> None:
    settings = Settings(
        database_url=SecretStr(preference_database_url),
        firebase_project_id="travel-assistant-test",
        application_environment=ApplicationEnvironment.TEST,
    )
    app = create_app(
        settings,
        token_verifier=TokenVerifier(),
        poi_provider=UnusedPoiProvider(),
    )
    with TestClient(app) as client:
        first = client.put(
            "/preferences",
            headers={"Authorization": "Bearer one"},
            json={
                "schema_version": 1,
                "preferences": {"old": True, "unicode": "Tiếng Việt"},
            },
        )
        replacement = client.put(
            "/preferences",
            headers={"Authorization": "Bearer one"},
            json={
                "schema_version": 1,
                "preferences": {"new": 2},
            },
        )
        other = client.put(
            "/preferences",
            headers={"Authorization": "Bearer two"},
            json={
                "schema_version": 1,
                "preferences": {"owner": "two"},
            },
        )
        first_get = client.get(
            "/preferences",
            headers={"Authorization": "Bearer one"},
        )
        second_get = client.get(
            "/preferences",
            headers={"Authorization": "Bearer two"},
        )

    assert first.status_code == 200
    assert replacement.status_code == 200
    assert other.status_code == 200
    first_updated_at = datetime.fromisoformat(
        first.json()["updated_at"].replace("Z", "+00:00")
    )
    replacement_updated_at = datetime.fromisoformat(
        replacement.json()["updated_at"].replace("Z", "+00:00")
    )
    assert first_updated_at.utcoffset() is not None
    assert replacement_updated_at.utcoffset() is not None
    assert replacement_updated_at >= first_updated_at
    assert first_get.json()["preferences"] == {"new": 2}
    assert first_get.json()["updated_at"] == replacement.json()["updated_at"]
    assert second_get.json()["preferences"] == {"owner": "two"}
    counts = _run(_counts(preference_database_url))
    assert counts == {
        "users": 2,
        "user_preferences": 2,
        "trips": 0,
        "itineraries": 0,
        "pois": 0,
    }


async def _concurrent_first_writes(database_url: str) -> None:
    runtime = create_database_runtime(database_url)
    try:
        async def write(value: int) -> None:
            async with runtime.session_factory() as session:
                await SqlAlchemyPreferenceStore(session).replace(
                    "firebase-concurrent",
                    PreferenceDocument(
                        schema_version=1,
                        preferences={"value": value},
                    ),
                )

        await asyncio.gather(write(1), write(2))
    finally:
        await runtime.dispose()


def test_concurrent_first_writes_keep_one_owner_and_one_preference(
    preference_database_url: str,
) -> None:
    _run(_concurrent_first_writes(preference_database_url))

    counts = _run(_counts(preference_database_url))
    assert counts["users"] == 1
    assert counts["user_preferences"] == 1


async def _failed_replace_preserves_prior_document(
    database_url: str,
) -> None:
    runtime = create_database_runtime(database_url)
    try:
        async with runtime.session_factory() as session:
            original = await SqlAlchemyPreferenceStore(session).replace(
                "firebase-rollback",
                PreferenceDocument(
                    schema_version=1,
                    preferences={"stable": "prior"},
                ),
            )

        async with runtime.engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    ALTER TABLE user_preferences
                    ADD CONSTRAINT reject_t025_forced_failure
                    CHECK (preferences <> '{"force_reject": true}'::jsonb)
                    """
                )
            )

        async with runtime.session_factory() as session:
            with pytest.raises(PreferenceStoreError):
                await SqlAlchemyPreferenceStore(session).replace(
                    "firebase-rollback",
                    PreferenceDocument(
                        schema_version=1,
                        preferences={"force_reject": True},
                    ),
                )

        async with runtime.session_factory() as session:
            retained = await SqlAlchemyPreferenceStore(session).get(
                "firebase-rollback"
            )

        assert retained is not None
        assert retained.preferences == {"stable": "prior"}
        assert retained.updated_at == original.updated_at
        assert retained.updated_at.utcoffset() is not None
    finally:
        await runtime.dispose()


def test_failed_transaction_rolls_back_and_preserves_prior_document(
    preference_database_url: str,
) -> None:
    _run(_failed_replace_preserves_prior_document(preference_database_url))


async def _schema_upgrade_cannot_be_downgraded(database_url: str) -> None:
    runtime = create_database_runtime(database_url)
    try:
        async with runtime.session_factory() as session:
            store = SqlAlchemyPreferenceStore(session)
            await store.replace(
                "firebase-schema-upgrade",
                PreferenceDocument(
                    schema_version=1,
                    preferences={"legacy": True},
                ),
            )
            upgraded = await store.replace(
                "firebase-schema-upgrade",
                TravelPreferenceDocument(
                    schema_version=2,
                    preferences=TravelPreferenceValuesV1(
                        interests=(TravelInterest.FOOD_AND_CAFES,),
                        pace=None,
                        budget_preference=BudgetPreference.BUDGET,
                    ),
                ),
            )

        async with runtime.session_factory() as session:
            with pytest.raises(PreferenceSchemaConflictError):
                await SqlAlchemyPreferenceStore(session).replace(
                    "firebase-schema-upgrade",
                    PreferenceDocument(
                        schema_version=1,
                        preferences={},
                    ),
                )

        async with runtime.session_factory() as session:
            retained = await SqlAlchemyPreferenceStore(session).get(
                "firebase-schema-upgrade"
            )

        assert upgraded.schema_version == 2
        assert retained is not None
        assert retained.schema_version == 2
        assert retained.preferences["interests"] == ["food_and_cafes"]
    finally:
        await runtime.dispose()


def test_schema_v2_upgrade_is_atomic_and_rejects_legacy_downgrade(
    preference_database_url: str,
) -> None:
    _run(_schema_upgrade_cannot_be_downgraded(preference_database_url))
