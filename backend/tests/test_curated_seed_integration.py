"""Real PostgreSQL/PostGIS integration tests for curated package seeding."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar, cast
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncConnection

import app.data_pipeline.seeder as seeder
from app.data_pipeline.loader import LoadedPackage, load_package
from app.data_pipeline.models import CityCode, CuratedPackageV1
from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from app.data_pipeline.seeder import (
    UnvalidatedPackageError,
    assert_test_database,
    in_memory_loaded_package,
    seed_loaded_package,
)
from tests.curated_fixtures import valid_package

ResultT = TypeVar("ResultT")
CURATED_TABLES = ("sources", "pois", "poi_sources", "menu_items", "narrations")
USER_TABLES = (
    "users",
    "user_preferences",
    "trips",
    "itineraries",
    "itinerary_items",
)


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _asyncpg_dsn(url: URL) -> str:
    return url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )


async def _create_database(base_url: URL, database_name: str) -> None:
    admin = await asyncpg.connect(_asyncpg_dsn(base_url))
    try:
        await admin.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await admin.close()
    database = await asyncpg.connect(
        _asyncpg_dsn(base_url.set(database=database_name))
    )
    try:
        await database.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    finally:
        await database.close()


async def _drop_database(base_url: URL, database_name: str) -> None:
    admin = await asyncpg.connect(_asyncpg_dsn(base_url))
    try:
        await admin.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1 AND pid <> pg_backend_pid()
            """,
            database_name,
        )
        await admin.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    finally:
        await admin.close()


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


@pytest.fixture(scope="module")
def curated_database_url() -> Iterator[str]:
    raw_base_url = os.environ.get("DATABASE_URL")
    if raw_base_url is None:
        pytest.skip("DATABASE_URL is required for real PostGIS tests")
    base_url = make_url(raw_base_url)
    database_name = f"travel_assistant_t031_{uuid4().hex}"
    _run(_create_database(base_url, database_name))
    test_url = base_url.set(database=database_name).render_as_string(
        hide_password=False
    )
    assert_test_database(test_url)
    with _migration_url(test_url):
        command.upgrade(Config("alembic.ini"), "head")
    try:
        yield test_url
    finally:
        _run(_drop_database(base_url, database_name))


async def _truncate_test_database(database_url: str) -> None:
    connection = await asyncpg.connect(
        _asyncpg_dsn(make_url(database_url))
    )
    try:
        await connection.execute(
            """
            TRUNCATE TABLE
                itinerary_items,
                narrations,
                menu_items,
                poi_sources,
                itineraries,
                trips,
                user_preferences,
                users,
                pois,
                sources
            CASCADE
            """
        )
    finally:
        await connection.close()


@pytest.fixture(autouse=True)
def clean_curated_database(
    curated_database_url: str,
) -> Iterator[None]:
    _run(_truncate_test_database(curated_database_url))
    yield
    _run(_truncate_test_database(curated_database_url))


def _loaded_city(city: str) -> LoadedPackage:
    result = load_package(CITY_PACKAGE_PATHS[city])
    assert result.is_valid
    return result.packages[0]


async def _counts(database_url: str) -> dict[str, int]:
    connection = await asyncpg.connect(
        _asyncpg_dsn(make_url(database_url))
    )
    try:
        return {
            table: cast(
                int,
                await connection.fetchval(
                    f'SELECT count(*) FROM "{table}"'
                ),
            )
            for table in (*CURATED_TABLES, *USER_TABLES)
        }
    finally:
        await connection.close()


def test_migrated_schema_seeds_both_cities_with_spatial_provenance(
    curated_database_url: str,
) -> None:
    hcmc = _loaded_city("hcmc")
    bangkok = _loaded_city("bkk")

    hcmc_summary = _run(
        seed_loaded_package(hcmc, curated_database_url)
    )
    bangkok_summary = _run(
        seed_loaded_package(bangkok, curated_database_url)
    )
    counts = _run(_counts(curated_database_url))

    assert hcmc_summary.package_id == "hcmc-starter-v1"
    assert bangkok_summary.package_id == "bkk-starter-v1"
    assert counts["sources"] == 35
    assert counts["pois"] == 42
    assert counts["poi_sources"] == 76
    assert counts["menu_items"] == 3
    assert counts["narrations"] == 42
    assert {counts[table] for table in USER_TABLES} == {0}

    async def snapshot() -> tuple[list[str], list[asyncpg.Record]]:
        connection = await asyncpg.connect(
            _asyncpg_dsn(make_url(curated_database_url))
        )
        try:
            cities = cast(
                list[str],
                await connection.fetchval(
                    "SELECT array_agg(DISTINCT city ORDER BY city) FROM pois"
                ),
            )
            spatial = await connection.fetch(
                """
                SELECT
                    id,
                    ST_GeometryType(location::geometry) AS geometry_type,
                    ST_SRID(location::geometry) AS srid
                FROM pois
                ORDER BY id
                """
            )
            return cities, spatial
        finally:
            await connection.close()

    cities, spatial = _run(snapshot())
    assert cities == ["bkk", "hcmc"]
    assert all(row["geometry_type"] == "ST_Point" for row in spatial)
    assert all(row["srid"] == 4326 for row in spatial)


def test_second_seed_is_idempotent_and_changed_content_updates(
    curated_database_url: str,
) -> None:
    loaded = _loaded_city("hcmc")
    _run(seed_loaded_package(loaded, curated_database_url))

    async def poi_snapshot() -> tuple[int, str, str]:
        connection = await asyncpg.connect(
            _asyncpg_dsn(make_url(curated_database_url))
        )
        try:
            row = await connection.fetchrow(
                """
                SELECT count(*) OVER () AS row_count,
                       canonical_name,
                       xmin::text AS row_version
                FROM pois
                WHERE id = 'hcmc-poi-central-post-office'
                """
            )
            assert row is not None
            return (
                cast(int, row["row_count"]),
                cast(str, row["canonical_name"]),
                cast(str, row["row_version"]),
            )
        finally:
            await connection.close()

    first = _run(poi_snapshot())
    _run(seed_loaded_package(loaded, curated_database_url))
    second = _run(poi_snapshot())
    assert second == first

    updated_pois = tuple(
        poi.model_copy(update={"canonical_name": "Updated deterministic name"})
        if poi.id == "hcmc-poi-central-post-office"
        else poi
        for poi in loaded.package.pois
    )
    updated_package = loaded.package.model_copy(
        update={"pois": updated_pois}
    )
    updated = LoadedPackage(loaded.source_path, updated_package)
    _run(seed_loaded_package(updated, curated_database_url))
    third = _run(poi_snapshot())

    assert third[0] == first[0]
    assert third[1] == "Updated deterministic name"
    assert third[2] != first[2]
    counts = _run(_counts(curated_database_url))
    assert counts["pois"] == 30
    assert counts["sources"] == 22
    assert counts["poi_sources"] == 63


def test_second_bangkok_seed_is_idempotent(
    curated_database_url: str,
) -> None:
    loaded = _loaded_city("bkk")
    first_summary = _run(seed_loaded_package(loaded, curated_database_url))
    first_counts = _run(_counts(curated_database_url))
    second_summary = _run(seed_loaded_package(loaded, curated_database_url))
    second_counts = _run(_counts(curated_database_url))

    assert first_summary == second_summary
    assert first_counts == second_counts
    assert second_counts["sources"] == 13
    assert second_counts["pois"] == 12
    assert second_counts["poi_sources"] == 13
    assert second_counts["menu_items"] == 0
    assert second_counts["narrations"] == 12


def test_menu_and_narration_provenance_and_freshness_survive(
    curated_database_url: str,
) -> None:
    loaded = in_memory_loaded_package(valid_package("bkk"))

    _run(seed_loaded_package(loaded, curated_database_url))

    async def snapshot() -> tuple[asyncpg.Record, asyncpg.Record]:
        connection = await asyncpg.connect(
            _asyncpg_dsn(make_url(curated_database_url))
        )
        try:
            menu = await connection.fetchrow(
                """
                SELECT
                    m.price_minor_units,
                    m.currency_code,
                    m.source_type,
                    m.source_updated_at,
                    m.source_id,
                    s.url,
                    s.retrieved_at
                FROM menu_items AS m
                JOIN sources AS s ON s.id = m.source_id
                WHERE m.id = 'bkk-menu-test'
                """
            )
            narration = await connection.fetchrow(
                """
                SELECT n.source_id, n.verification_status, s.label
                FROM narrations AS n
                JOIN sources AS s ON s.id = n.source_id
                WHERE n.id = 'bkk-narration-test'
                """
            )
            assert menu is not None
            assert narration is not None
            return menu, narration
        finally:
            await connection.close()

    menu, narration = _run(snapshot())
    assert menu["price_minor_units"] == 12500
    assert menu["currency_code"] == "THB"
    assert menu["source_type"] == "official_operator"
    assert menu["source_id"] == "bkk-source-test"
    assert menu["source_updated_at"].isoformat() == (
        "2026-01-01T00:00:00+00:00"
    )
    assert menu["retrieved_at"].isoformat() == (
        "2026-01-01T00:00:00+00:00"
    )
    assert menu["url"] == "https://example.test/source"
    assert narration["source_id"] == "bkk-source-test"
    assert narration["verification_status"] == "verified"
    assert narration["label"] == "Test operator source"


def test_invalid_package_connects_to_nothing_and_inserts_nothing(
    curated_database_url: str,
) -> None:
    package = valid_package("hcmc")
    wrong_city_poi = package.pois[0].model_copy(
        update={"city_code": CityCode.BANGKOK}
    )
    invalid = package.model_copy(update={"pois": (wrong_city_poi,)})

    with pytest.raises(UnvalidatedPackageError):
        _run(
            seed_loaded_package(
                in_memory_loaded_package(invalid),
                curated_database_url,
            )
        )

    assert set(_run(_counts(curated_database_url)).values()) == {0}


def test_late_database_failure_rolls_back_whole_package(
    curated_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_after_sources(
        connection: AsyncConnection,
        package: CuratedPackageV1,
    ) -> None:
        del connection, package
        raise RuntimeError("deliberate late write failure")

    monkeypatch.setattr(seeder, "_upsert_pois", fail_after_sources)

    with pytest.raises(RuntimeError, match="deliberate"):
        _run(
            seed_loaded_package(
                _loaded_city("hcmc"),
                curated_database_url,
            )
        )

    assert set(_run(_counts(curated_database_url)).values()) == {0}


def test_test_database_guard_rejects_normal_database_name() -> None:
    with pytest.raises(
        seeder.UnsafeSeedTargetError,
        match="test-only",
    ):
        assert_test_database(
            "postgresql+asyncpg://user:password@localhost/travel_assistant"
        )
