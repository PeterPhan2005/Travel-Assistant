"""Real PostgreSQL/PostGIS integration tests for the curated POI provider."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, TypeVar, cast
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.data_pipeline.loader import load_package
from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from app.data_pipeline.seeder import (
    assert_test_database,
    in_memory_loaded_package,
    seed_loaded_package,
)
from app.providers.poi.curated import CuratedPoiProvider
from app.providers.poi.errors import PoiProviderError, ProviderErrorCode
from app.providers.poi.models import (
    Coordinates,
    PoiDiscoveryRequest,
    PoiProviderKind,
    ProviderTimeoutPolicy,
    SupportedCity,
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
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


async def _create_database(base_url: URL, database_name: str) -> None:
    admin = await asyncpg.connect(_asyncpg_dsn(base_url))
    try:
        await admin.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await admin.close()
    database = await asyncpg.connect(_asyncpg_dsn(base_url.set(database=database_name)))
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
def provider_database_url() -> Iterator[str]:
    raw_base_url = os.environ.get("DATABASE_URL")
    if raw_base_url is None:
        pytest.skip("DATABASE_URL is required for real PostGIS tests")
    base_url = make_url(raw_base_url)
    database_name = f"travel_assistant_test_t032_{uuid4().hex}"
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
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
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


def _loaded_city(city: str) -> Any:
    result = load_package(CITY_PACKAGE_PATHS[city])
    assert result.is_valid
    return result.packages[0]


@pytest.fixture(autouse=True)
def seeded_provider_database(
    provider_database_url: str,
) -> Iterator[None]:
    _run(_truncate_test_database(provider_database_url))
    _run(
        seed_loaded_package(
            _loaded_city("hcmc"),
            provider_database_url,
        )
    )
    _run(
        seed_loaded_package(
            _loaded_city("bkk"),
            provider_database_url,
        )
    )
    yield
    _run(_truncate_test_database(provider_database_url))


def _request(
    *,
    city: SupportedCity = SupportedCity.HCMC,
    latitude: float = 10.7799,
    longitude: float = 106.7,
    radius_metres: int = 5_000,
    limit: int = 20,
    query: str | None = None,
    category: str | None = None,
) -> PoiDiscoveryRequest:
    return PoiDiscoveryRequest(
        query=query,
        category=category,
        city=city,
        origin=Coordinates(latitude=latitude, longitude=longitude),
        radius_metres=radius_metres,
        limit=limit,
    )


async def _discover(
    database_url: str,
    request: PoiDiscoveryRequest,
) -> Any:
    engine = create_async_engine(database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await CuratedPoiProvider(session).discover(request)
    finally:
        await engine.dispose()


def test_hcmc_and_bangkok_results_are_city_scoped_with_metres(
    provider_database_url: str,
) -> None:
    hcmc = _run(_discover(provider_database_url, _request()))
    bangkok = _run(
        _discover(
            provider_database_url,
            _request(
                city=SupportedCity.BANGKOK,
                latitude=13.746508,
                longitude=100.493096,
            ),
        )
    )

    assert [item.provider_id for item in hcmc.items] == [
        "hcmc-poi-central-post-office",
        "hcmc-poi-war-remnants-museum",
    ]
    assert {item.city for item in hcmc.items} == {SupportedCity.HCMC}
    assert [item.provider_id for item in bangkok.items] == ["bkk-poi-wat-pho"]
    assert {item.city for item in bangkok.items} == {SupportedCity.BANGKOK}
    assert all(item.distance_metres is not None for item in hcmc.items)
    assert hcmc.items[0].distance_metres == pytest.approx(0.0, abs=0.01)


def test_category_text_radius_and_limit_filters_are_bounded(
    provider_database_url: str,
) -> None:
    category = _run(
        _discover(
            provider_database_url,
            _request(category="museum"),
        )
    )
    text = _run(
        _discover(
            provider_database_url,
            _request(query="chiến tranh"),
        )
    )
    radius = _run(
        _discover(
            provider_database_url,
            _request(radius_metres=100),
        )
    )
    limited = _run(
        _discover(
            provider_database_url,
            _request(limit=1),
        )
    )

    assert [item.provider_id for item in category.items] == [
        "hcmc-poi-war-remnants-museum"
    ]
    assert [item.provider_id for item in text.items] == ["hcmc-poi-war-remnants-museum"]
    assert [item.provider_id for item in radius.items] == [
        "hcmc-poi-central-post-office"
    ]
    assert limited.returned_count == 1
    assert limited.is_complete is False


async def _insert_tie_fixtures(database_url: str) -> None:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    try:
        await connection.execute(
            """
            INSERT INTO sources (
                id, source_type, label, published_at, retrieved_at
            )
            VALUES
                (
                    'hcmc-source-tie-a',
                    'official_operator',
                    'Tie source A',
                    '2025-01-01T00:00:00Z',
                    '2026-01-01T00:00:00Z'
                ),
                (
                    'hcmc-source-tie-b',
                    'official_operator',
                    'Tie source B',
                    '2025-02-01T00:00:00Z',
                    '2026-02-01T00:00:00Z'
                )
            """
        )
        await connection.execute(
            """
            INSERT INTO pois (
                id, canonical_name, city, category, location
            )
            VALUES
                (
                    'hcmc-poi-tie-a',
                    'Tie POI A',
                    'hcmc',
                    'test',
                    ST_SetSRID(
                        ST_MakePoint(106.71, 10.78),
                        4326
                    )::geography
                ),
                (
                    'hcmc-poi-tie-b',
                    'Tie POI B',
                    'hcmc',
                    'test',
                    ST_SetSRID(
                        ST_MakePoint(106.71, 10.78),
                        4326
                    )::geography
                )
            """
        )
        await connection.execute(
            """
            INSERT INTO poi_sources (poi_id, source_id)
            VALUES
                ('hcmc-poi-tie-a', 'hcmc-source-tie-b'),
                ('hcmc-poi-tie-a', 'hcmc-source-tie-a'),
                ('hcmc-poi-tie-b', 'hcmc-source-tie-a')
            """
        )
    finally:
        await connection.close()


def test_distance_and_stable_id_ordering_with_sorted_unique_sources(
    provider_database_url: str,
) -> None:
    _run(_insert_tie_fixtures(provider_database_url))

    result = _run(
        _discover(
            provider_database_url,
            _request(
                latitude=10.78,
                longitude=106.71,
                radius_metres=100,
                query="Tie POI",
            ),
        )
    )

    assert [item.provider_id for item in result.items] == [
        "hcmc-poi-tie-a",
        "hcmc-poi-tie-b",
    ]
    assert result.items[0].distance_metres == pytest.approx(0.0, abs=0.01)
    assert result.items[1].distance_metres == pytest.approx(0.0, abs=0.01)
    assert [source.source_id for source in result.items[0].sources] == [
        "hcmc-source-tie-a",
        "hcmc-source-tie-b",
    ]


def test_point_coordinates_srid_provenance_and_freshness_are_plain(
    provider_database_url: str,
) -> None:
    _run(
        seed_loaded_package(
            in_memory_loaded_package(valid_package("hcmc")),
            provider_database_url,
        )
    )

    result = _run(
        _discover(
            provider_database_url,
            _request(
                latitude=10.77,
                longitude=106.7,
                query="Test POI",
            ),
        )
    )
    item = result.items[0]
    source = item.sources[0]

    assert item.coordinates == Coordinates(
        latitude=10.77,
        longitude=106.7,
    )
    assert item.provider is PoiProviderKind.CURATED
    assert source.source_id == "hcmc-source-test"
    assert source.publisher == "Test publisher"
    assert str(source.url) == "https://example.test/source"
    assert source.published_at == datetime(
        2025,
        12,
        31,
        tzinfo=timezone.utc,
    )
    assert source.retrieved_at == datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )
    assert item.retrieved_at == source.retrieved_at
    assert result.freshness_at == item.retrieved_at


def test_missing_optional_facts_remain_absent(
    provider_database_url: str,
) -> None:
    result = _run(_discover(provider_database_url, _request(limit=1)))
    item = result.items[0]
    serialized = item.model_dump(mode="json", exclude_none=True)

    assert item.rating is None
    assert item.rating_count is None
    assert item.price_level is None
    assert item.opening_hours_summary is None
    for absent in (
        "rating",
        "rating_count",
        "price_level",
        "opening_hours_summary",
        "description",
        "menu",
        "narration",
        "raw",
        "payload",
        "metadata",
    ):
        assert absent not in serialized


async def _database_snapshot(database_url: str) -> dict[str, tuple[int, int]]:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    try:
        snapshot: dict[str, tuple[int, int]] = {}
        for table in (*CURATED_TABLES, *USER_TABLES):
            count = cast(
                int,
                await connection.fetchval(f'SELECT count(*) FROM "{table}"'),
            )
            version_sum = cast(
                int,
                await connection.fetchval(
                    f"""
                    SELECT COALESCE(
                        sum(('x' || lpad(xmin::text, 8, '0'))::bit(32)::bigint),
                        0
                    )
                    FROM "{table}"
                    """
                ),
            )
            snapshot[table] = (count, version_sum)
        return snapshot
    finally:
        await connection.close()


async def _insert_user_fixture(database_url: str) -> None:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    try:
        await connection.execute(
            "INSERT INTO users (id, firebase_uid) VALUES ($1, $2)",
            uuid4(),
            "provider-boundary-user",
        )
    finally:
        await connection.close()


async def _discover_with_statement_capture(
    database_url: str,
) -> tuple[Any, list[str]]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    statements: list[str] = []

    def capture(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        del connection, cursor, parameters, context, executemany
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            result = await CuratedPoiProvider(session).discover(_request())
            return result, statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
        await engine.dispose()


def test_discovery_is_one_read_only_query_without_user_table_access(
    provider_database_url: str,
) -> None:
    _run(_insert_user_fixture(provider_database_url))
    before = _run(_database_snapshot(provider_database_url))

    result, statements = _run(_discover_with_statement_capture(provider_database_url))
    after = _run(_database_snapshot(provider_database_url))

    assert result.returned_count == 2
    assert before == after
    assert len(statements) == 1
    normalized_sql = statements[0].casefold()
    assert normalized_sql.lstrip().startswith("with candidate_pois")
    for user_table in USER_TABLES:
        assert user_table not in normalized_sql


async def _hold_poi_lock(database_url: str) -> asyncpg.Connection:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    await connection.execute("BEGIN")
    await connection.execute("LOCK TABLE pois IN ACCESS EXCLUSIVE MODE")
    return connection


async def _timeout_while_database_is_blocked(database_url: str) -> None:
    lock = await _hold_poi_lock(database_url)
    engine = create_async_engine(database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            provider = CuratedPoiProvider(
                session,
                timeout_policy=ProviderTimeoutPolicy(seconds=0.01),
            )
            with pytest.raises(PoiProviderError) as captured:
                await provider.discover(_request())
            assert captured.value.failure.code is ProviderErrorCode.TIMEOUT
            assert captured.value.failure.retryable is True
    finally:
        await lock.execute("ROLLBACK")
        await lock.close()
        await engine.dispose()


def test_real_database_deadline_maps_to_standard_timeout(
    provider_database_url: str,
) -> None:
    _run(_timeout_while_database_is_blocked(provider_database_url))


async def _cancel_while_database_is_blocked(database_url: str) -> None:
    lock = await _hold_poi_lock(database_url)
    engine = create_async_engine(database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            task = asyncio.create_task(CuratedPoiProvider(session).discover(_request()))
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    finally:
        await lock.execute("ROLLBACK")
        await lock.close()
        await engine.dispose()


def test_real_database_cancellation_propagates(
    provider_database_url: str,
) -> None:
    _run(_cancel_while_database_is_blocked(provider_database_url))
