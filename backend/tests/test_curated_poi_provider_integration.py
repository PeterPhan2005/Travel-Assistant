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
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.agents.discovery.menu import (
    MenuErrorCode,
    MenuReaderError,
    MenuTimeoutPolicy,
    SqlAlchemyPoiMenuReader,
)
from app.data_pipeline.loader import load_package
from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from app.data_pipeline.seeder import (
    assert_test_database,
    in_memory_loaded_package,
    seed_loaded_package,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.itinerary_generation.candidates import (
    SqlAlchemyCuratedCityCandidateReader,
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


async def _read_city_candidates_with_statement_capture(
    database_url: str,
    city: SupportedCity,
    limit: int,
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
            result = await SqlAlchemyCuratedCityCandidateReader(session).read(
                city,
                limit,
            )
            return result, statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
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


def test_city_only_candidates_are_stable_read_only_and_have_no_distance(
    provider_database_url: str,
) -> None:
    _run(_insert_user_fixture(provider_database_url))
    before = _run(_database_snapshot(provider_database_url))

    first, statements = _run(
        _read_city_candidates_with_statement_capture(
            provider_database_url,
            SupportedCity.HCMC,
            20,
        )
    )
    second, _ = _run(
        _read_city_candidates_with_statement_capture(
            provider_database_url,
            SupportedCity.HCMC,
            20,
        )
    )
    bangkok, _ = _run(
        _read_city_candidates_with_statement_capture(
            provider_database_url,
            SupportedCity.BANGKOK,
            20,
        )
    )
    after = _run(_database_snapshot(provider_database_url))

    assert [item.provider_id for item in first.items] == [
        "hcmc-poi-central-post-office",
        "hcmc-poi-war-remnants-museum",
    ]
    assert first == second
    assert [item.provider_id for item in bangkok.items] == ["bkk-poi-wat-pho"]
    assert all(item.distance_metres is None for item in first.items)
    assert all(item.city is SupportedCity.HCMC for item in first.items)
    assert before == after
    assert len(statements) == 1
    normalized_sql = statements[0].casefold()
    assert normalized_sql.lstrip().startswith("with itinerary_city_candidates")
    for user_table in USER_TABLES:
        assert user_table not in normalized_sql


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


def _endpoint_client(database_url: str) -> TestClient:
    settings = Settings(
        database_url=SecretStr(database_url),
        firebase_project_id="travel-assistant-postgis-test",
        application_environment=ApplicationEnvironment.TEST,
    )
    return TestClient(
        create_app(settings),
        raise_server_exceptions=False,
    )


def test_nearby_endpoint_uses_seeded_postgis_without_mutation(
    provider_database_url: str,
) -> None:
    before = _run(_database_snapshot(provider_database_url))

    with _endpoint_client(provider_database_url) as client:
        health = client.get("/health")
        hcmc = client.get(
            "/pois/nearby",
            params={
                "city": "hcmc",
                "latitude": 10.7799,
                "longitude": 106.7,
            },
        )
        bangkok = client.get(
            "/pois/nearby",
            params={
                "city": "bkk",
                "latitude": 13.746508,
                "longitude": 100.493096,
            },
        )
        category = client.get(
            "/pois/nearby",
            params={
                "city": "hcmc",
                "latitude": 10.7799,
                "longitude": 106.7,
                "category": "museum",
            },
        )
        text = client.get(
            "/pois/nearby",
            params={
                "city": "hcmc",
                "latitude": 10.7799,
                "longitude": 106.7,
                "query": "chiến tranh",
            },
        )
        radius = client.get(
            "/pois/nearby",
            params={
                "city": "hcmc",
                "latitude": 10.7799,
                "longitude": 106.7,
                "radius_metres": 100,
            },
        )
        limited = client.get(
            "/pois/nearby",
            params={
                "city": "hcmc",
                "latitude": 10.7799,
                "longitude": 106.7,
                "limit": 1,
            },
        )

    after = _run(_database_snapshot(provider_database_url))
    assert health.status_code == 200
    assert hcmc.status_code == 200
    assert bangkok.status_code == 200
    assert category.status_code == 200
    assert text.status_code == 200
    assert radius.status_code == 200
    assert limited.status_code == 200
    assert before == after

    hcmc_body = hcmc.json()
    bangkok_body = bangkok.json()
    assert [item["provider_id"] for item in hcmc_body["items"]] == [
        "hcmc-poi-central-post-office",
        "hcmc-poi-war-remnants-museum",
    ]
    assert [item["provider_id"] for item in bangkok_body["items"]] == [
        "bkk-poi-wat-pho"
    ]
    assert {item["city"] for item in hcmc_body["items"]} == {"hcmc"}
    assert {item["city"] for item in bangkok_body["items"]} == {"bkk"}
    assert [item["provider_id"] for item in category.json()["items"]] == [
        "hcmc-poi-war-remnants-museum"
    ]
    assert [item["provider_id"] for item in text.json()["items"]] == [
        "hcmc-poi-war-remnants-museum"
    ]
    assert [item["provider_id"] for item in radius.json()["items"]] == [
        "hcmc-poi-central-post-office"
    ]
    assert limited.json()["returned_count"] == 1
    assert limited.json()["is_complete"] is False

    first = hcmc_body["items"][0]
    assert first["distance_metres"] == pytest.approx(0.0, abs=0.01)
    assert first["coordinates"] == {
        "latitude": pytest.approx(10.7799),
        "longitude": pytest.approx(106.7),
    }
    assert first["sources"]
    assert first["retrieved_at"]
    assert hcmc_body["freshness_at"]
    assert first["rating"] is None
    assert first["price_level"] is None
    assert first["opening_hours_summary"] is None
    assert "origin" not in hcmc.text
    assert "payload" not in hcmc.text
    assert "metadata" not in hcmc.text
    source_ids = [
        source["source_id"] for source in first["sources"]
    ]
    assert source_ids == sorted(set(source_ids))


def test_nearby_endpoint_preserves_distance_then_stable_id_order(
    provider_database_url: str,
) -> None:
    _run(_insert_tie_fixtures(provider_database_url))

    with _endpoint_client(provider_database_url) as client:
        response = client.get(
            "/pois/nearby",
            params={
                "city": "hcmc",
                "latitude": 10.78,
                "longitude": 106.71,
                "radius_metres": 100,
                "query": "Tie POI",
                "limit": 20,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert [item["provider_id"] for item in body["items"]] == [
        "hcmc-poi-tie-a",
        "hcmc-poi-tie-b",
    ]
    assert all(
        item["distance_metres"] == pytest.approx(0.0, abs=0.01)
        for item in body["items"]
    )
    assert [
        source["source_id"]
        for source in body["items"][0]["sources"]
    ] == [
        "hcmc-source-tie-a",
        "hcmc-source-tie-b",
    ]


async def _read_menus(
    database_url: str,
    selected_ids: tuple[str, ...],
) -> Any:
    engine = create_async_engine(database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await SqlAlchemyPoiMenuReader(session).read_menu_items(
                selected_ids
            )
    finally:
        await engine.dispose()


def test_menu_reader_accepts_current_zero_menu_production_data_by_city(
    provider_database_url: str,
) -> None:
    hcmc = _run(
        _read_menus(
            provider_database_url,
            (
                "hcmc-poi-central-post-office",
                "hcmc-poi-war-remnants-museum",
            ),
        )
    )
    bangkok = _run(
        _read_menus(
            provider_database_url,
            ("bkk-poi-wat-pho",),
        )
    )

    assert hcmc.items == ()
    assert bangkok.items == ()


def test_menu_reader_maps_only_selected_pois_with_exact_source_and_money(
    provider_database_url: str,
) -> None:
    _run(
        seed_loaded_package(
            in_memory_loaded_package(valid_package("hcmc")),
            provider_database_url,
        )
    )
    _run(
        seed_loaded_package(
            in_memory_loaded_package(valid_package("bkk")),
            provider_database_url,
        )
    )

    hcmc = _run(
        _read_menus(
            provider_database_url,
            ("hcmc-poi-test",),
        )
    )
    unrelated = _run(
        _read_menus(
            provider_database_url,
            ("hcmc-poi-central-post-office",),
        )
    )
    none_selected = _run(_read_menus(provider_database_url, ()))

    assert len(hcmc.items) == 1
    item = hcmc.items[0]
    assert item.menu_item_id == "hcmc-menu-test"
    assert item.poi_provider_id == "hcmc-poi-test"
    assert item.item_name == "Test menu item"
    assert item.price_minor_units == 12_500
    assert item.currency == "VND"
    assert item.source.source_id == "hcmc-source-test"
    assert item.source.source_type.value == "official_operator"
    assert item.source.publisher == "Test publisher"
    assert str(item.source.url) == "https://example.test/source"
    assert item.source_updated_at == datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )
    assert unrelated.items == ()
    assert none_selected.items == ()


async def _menu_read_with_statement_capture(
    database_url: str,
    selected_ids: tuple[str, ...],
) -> tuple[Any, list[str], bool]:
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
            result = await SqlAlchemyPoiMenuReader(
                session
            ).read_menu_items(selected_ids)
            return result, statements, session.is_active
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
        await engine.dispose()


def test_menu_reader_is_one_parameterized_read_without_mutation_or_n_plus_one(
    provider_database_url: str,
) -> None:
    _run(
        seed_loaded_package(
            in_memory_loaded_package(valid_package("hcmc")),
            provider_database_url,
        )
    )
    _run(_insert_user_fixture(provider_database_url))
    before = _run(_database_snapshot(provider_database_url))

    result, statements, session_remained_active = _run(
        _menu_read_with_statement_capture(
            provider_database_url,
            (
                "hcmc-poi-central-post-office",
                "hcmc-poi-test",
            ),
        )
    )
    after = _run(_database_snapshot(provider_database_url))

    assert [item.menu_item_id for item in result.items] == [
        "hcmc-menu-test"
    ]
    assert len(statements) == 1
    normalized_sql = statements[0].casefold()
    assert normalized_sql.lstrip().startswith("select")
    assert "menu_items.poi_id in" in normalized_sql
    assert "order by menu_items.poi_id, menu_items.id" in normalized_sql
    for user_table in USER_TABLES:
        assert user_table not in normalized_sql
    assert session_remained_active is True
    assert after == before


async def _hold_menu_lock(database_url: str) -> asyncpg.Connection:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    await connection.execute("BEGIN")
    await connection.execute("LOCK TABLE menu_items IN ACCESS EXCLUSIVE MODE")
    return connection


async def _menu_timeout_while_database_is_blocked(database_url: str) -> None:
    lock = await _hold_menu_lock(database_url)
    engine = create_async_engine(database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            reader = SqlAlchemyPoiMenuReader(
                session,
                timeout_policy=MenuTimeoutPolicy(seconds=0.01),
            )
            with pytest.raises(MenuReaderError) as captured:
                await reader.read_menu_items(
                    ("hcmc-poi-central-post-office",)
                )
            assert captured.value.code is MenuErrorCode.TIMEOUT
    finally:
        await lock.execute("ROLLBACK")
        await lock.close()
        await engine.dispose()


def test_real_menu_database_deadline_maps_to_sanitized_timeout(
    provider_database_url: str,
) -> None:
    _run(_menu_timeout_while_database_is_blocked(provider_database_url))


async def _cancel_menu_while_database_is_blocked(database_url: str) -> None:
    lock = await _hold_menu_lock(database_url)
    engine = create_async_engine(database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            reader = SqlAlchemyPoiMenuReader(session)
            task = asyncio.create_task(
                reader.read_menu_items(
                    ("hcmc-poi-central-post-office",)
                )
            )
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    finally:
        await lock.execute("ROLLBACK")
        await lock.close()
        await engine.dispose()


def test_real_menu_database_cancellation_propagates(
    provider_database_url: str,
) -> None:
    _run(_cancel_menu_while_database_is_blocked(provider_database_url))


async def _corrupt_menu_source_type(database_url: str) -> None:
    connection = await asyncpg.connect(_asyncpg_dsn(make_url(database_url)))
    try:
        await connection.execute(
            """
            UPDATE sources
            SET source_type = 'unsupported_source'
            WHERE id = 'hcmc-source-test'
            """
        )
        await connection.execute(
            """
            UPDATE menu_items
            SET source_type = 'unsupported_source'
            WHERE id = 'hcmc-menu-test'
            """
        )
    finally:
        await connection.close()


def test_malformed_database_source_data_fails_closed(
    provider_database_url: str,
) -> None:
    _run(
        seed_loaded_package(
            in_memory_loaded_package(valid_package("hcmc")),
            provider_database_url,
        )
    )
    _run(_corrupt_menu_source_type(provider_database_url))

    with pytest.raises(MenuReaderError) as captured:
        _run(
            _read_menus(
                provider_database_url,
                ("hcmc-poi-test",),
            )
        )
    assert captured.value.code is MenuErrorCode.INVALID_OUTPUT
