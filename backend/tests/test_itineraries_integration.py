"""Disposable PostGIS integration tests for saved-itinerary ownership/revisions."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
import os
from typing import Any, TypeVar, cast
from uuid import uuid4

from alembic import command
from alembic.config import Config
import asyncpg  # type: ignore[import-untyped]
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
from sqlalchemy.engine import URL, make_url

from app.auth.models import AuthenticatedPrincipal
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
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
    database = await asyncpg.connect(_asyncpg_dsn(base_url.set(database=name)))
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
def itinerary_database_url() -> Iterator[str]:
    raw_base_url = os.environ.get("DATABASE_URL")
    if raw_base_url is None:
        pytest.skip("DATABASE_URL is required for real itinerary tests")
    base_url = make_url(raw_base_url)
    database_name = f"travel_assistant_t071_{uuid4().hex}"
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
    async def verify_id_token(self, raw_token: str) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(uid=f"firebase-{raw_token}")


class UnusedPoiProvider:
    async def discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        del request
        raise AssertionError("POI provider must not be called")


def _client(database_url: str) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                database_url=SecretStr(database_url),
                firebase_project_id="travel-assistant-test",
                application_environment=ApplicationEnvironment.TEST,
            ),
            token_verifier=TokenVerifier(),
            poi_provider=UnusedPoiProvider(),
        )
    )


def _snapshot(
    *,
    base_revision: int = 0,
    item_title: str = "Điểm đầu",
) -> dict[str, object]:
    return {
        "base_revision": base_revision,
        "title": "Lịch trình đã lưu",
        "city": "hcmc",
        "local_date": "2026-08-03",
        "timezone": "Asia/Ho_Chi_Minh",
        "start_local_time": "09:00",
        "end_local_time": "17:00",
        "items": [
            {
                "id": "20000000-0000-4000-8000-000000000001",
                "position": 0,
                "title": item_title,
                "start_local_time": "09:00",
                "end_local_time": "12:00",
            },
            {
                "id": "20000000-0000-4000-8000-000000000002",
                "position": 1,
                "title": "Điểm sau",
                "start_local_time": "13:00",
                "end_local_time": "17:00",
            },
        ],
        "assumptions": ["Lịch trình nháp chưa tính thời gian di chuyển."],
        "warnings": ["Kiểm tra giờ mở cửa trước khi đi."],
    }


def _auth(owner: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {owner}"}


async def _database_state(database_url: str) -> dict[str, object]:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    try:
        return {
            "users": cast(int, await connection.fetchval("SELECT count(*) FROM users")),
            "itineraries": cast(
                int,
                await connection.fetchval("SELECT count(*) FROM itineraries"),
            ),
            "items": cast(
                int,
                await connection.fetchval("SELECT count(*) FROM itinerary_items"),
            ),
            "tombstones": cast(
                int,
                await connection.fetchval(
                    "SELECT count(*) FROM itinerary_tombstones"
                ),
            ),
            "revision": await connection.fetchval(
                "SELECT revision FROM itineraries LIMIT 1"
            ),
            "positions": tuple(
                row["position"]
                for row in await connection.fetch(
                    "SELECT position FROM itinerary_items ORDER BY position"
                )
            ),
            "notes": tuple(
                row["notes"]
                for row in await connection.fetch(
                    "SELECT notes FROM itinerary_items ORDER BY position"
                )
            ),
        }
    finally:
        await connection.close()


def test_real_database_enforces_owner_revision_atomicity_and_tombstone(
    itinerary_database_url: str,
) -> None:
    itinerary_id = "10000000-0000-4000-8000-000000000001"
    with _client(itinerary_database_url) as client:
        created = client.put(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("one"),
            json=_snapshot(),
        )
        owner_get = client.get(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("one"),
        )
        other_get = client.get(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("two"),
        )
        other_put = client.put(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("two"),
            json=_snapshot(),
        )
        stale = client.put(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("one"),
            json=_snapshot(),
        )
        updated = client.put(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("one"),
            json=_snapshot(base_revision=1, item_title="Điểm mới"),
        )
        deleted = client.request(
            "DELETE",
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("one"),
            json={"base_revision": 2},
        )
        repeated_delete = client.request(
            "DELETE",
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("one"),
            json={"base_revision": 2},
        )
        resurrection = client.put(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("one"),
            json=_snapshot(base_revision=2),
        )

    assert created.status_code == 200
    assert owner_get.json() == created.json()
    assert other_get.status_code == 404
    assert other_put.status_code == 404
    assert stale.status_code == 409
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert [item["position"] for item in updated.json()["items"]] == [0, 1]
    assert deleted.json()["revision"] == 3
    assert repeated_delete.json() == deleted.json()
    assert resurrection.status_code == 409
    assert _run(_database_state(itinerary_database_url)) == {
        "users": 1,
        "itineraries": 0,
        "items": 0,
        "tombstones": 1,
        "revision": None,
        "positions": (),
        "notes": (),
    }


async def _add_reject_constraint(database_url: str) -> None:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    try:
        await connection.execute(
            """
            ALTER TABLE itinerary_items
            ADD CONSTRAINT reject_t071_atomic_failure
            CHECK (title <> 'force-atomic-failure')
            """
        )
    finally:
        await connection.close()


def test_item_failure_rolls_back_parent_revision_and_complete_item_set(
    itinerary_database_url: str,
) -> None:
    itinerary_id = "10000000-0000-4000-8000-000000000002"
    with _client(itinerary_database_url) as client:
        created = client.put(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("rollback"),
            json=_snapshot(),
        )
        assert created.status_code == 200
        _run(_add_reject_constraint(itinerary_database_url))
        failed = client.put(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("rollback"),
            json=_snapshot(
                base_revision=1,
                item_title="force-atomic-failure",
            ),
        )
        retained = client.get(
            f"/v1/itineraries/{itinerary_id}",
            headers=_auth("rollback"),
        )

    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "itineraries_unavailable"
    assert retained.status_code == 200
    assert retained.json() == created.json()
    assert _run(_database_state(itinerary_database_url))["positions"] == (0, 1)
    assert _run(_database_state(itinerary_database_url))["notes"] == (None, None)
