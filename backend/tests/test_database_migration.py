"""Real PostgreSQL/PostGIS migration and constraint tests."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar, TypedDict, cast
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL, make_url

EXPECTED_APPLICATION_TABLES = {
    "itineraries",
    "itinerary_items",
    "menu_items",
    "narrations",
    "poi_sources",
    "pois",
    "sources",
    "trips",
    "user_preferences",
    "users",
}
ResultT = TypeVar("ResultT")


class SpatialSnapshot(TypedDict):
    storage_type: str
    geometry_type: str
    srid: int


class SchemaSnapshot(TypedDict):
    tables: set[str]
    spatial: SpatialSnapshot | None
    indexes: dict[str, str]
    row_counts: dict[str, int]


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _asyncpg_dsn(url: URL) -> str:
    return url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )


async def _create_postgis_database(base_url: URL, database_name: str) -> None:
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


@pytest.fixture
def postgis_database_url() -> Iterator[str]:
    raw_base_url = os.environ.get("DATABASE_URL")
    if raw_base_url is None:
        pytest.skip("DATABASE_URL is required for real PostGIS tests")

    base_url = make_url(raw_base_url)
    database_name = f"travel_assistant_t030_{uuid4().hex}"
    _run(_create_postgis_database(base_url, database_name))
    test_url = base_url.set(database=database_name).render_as_string(
        hide_password=False
    )
    try:
        yield test_url
    finally:
        _run(_drop_database(base_url, database_name))


@contextmanager
def _migration_url(database_url: str) -> Iterator[None]:
    original = os.environ.get("DATABASE_URL")
    original_firebase_project = os.environ.pop(
        "FIREBASE_PROJECT_ID",
        None,
    )
    os.environ["DATABASE_URL"] = database_url
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original
        if original_firebase_project is not None:
            os.environ["FIREBASE_PROJECT_ID"] = original_firebase_project


def _alembic(database_url: str, revision: str) -> None:
    configuration = Config("alembic.ini")
    with _migration_url(database_url):
        if revision == "base":
            command.downgrade(configuration, revision)
        else:
            command.upgrade(configuration, revision)


async def _schema_snapshot(database_url: str) -> SchemaSnapshot:
    connection = await asyncpg.connect(
        _asyncpg_dsn(make_url(database_url))
    )
    try:
        table_names = cast(
            list[str] | None,
            await connection.fetchval(
                """
                SELECT array_agg(table_name ORDER BY table_name)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                  AND table_name NOT IN ('alembic_version', 'spatial_ref_sys')
                """
            ),
        )
        tables = set(table_names or [])
        spatial = await connection.fetchrow(
            """
            SELECT
                postgis_typmod_type(a.atttypmod) AS geometry_type,
                postgis_typmod_srid(a.atttypmod) AS srid,
                t.typname AS storage_type
            FROM pg_attribute AS a
            JOIN pg_class AS c ON c.oid = a.attrelid
            JOIN pg_type AS t ON t.oid = a.atttypid
            WHERE c.relname = 'pois'
              AND a.attname = 'location'
              AND NOT a.attisdropped
            """
        )
        indexes: dict[str, str] = {
            cast(str, row["indexname"]): cast(str, row["indexdef"])
            for row in await connection.fetch(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                """
            )
        }
        row_counts = {
            table: cast(
                int,
                await connection.fetchval(
                    f'SELECT count(*) FROM "{table}"'
                ),
            )
            for table in EXPECTED_APPLICATION_TABLES.intersection(tables)
        }
        return {
            "tables": tables,
            "spatial": (
                None
                if spatial is None
                else SpatialSnapshot(
                    storage_type=cast(str, spatial["storage_type"]),
                    geometry_type=cast(str, spatial["geometry_type"]),
                    srid=cast(int, spatial["srid"]),
                )
            ),
            "indexes": indexes,
            "row_counts": row_counts,
        }
    finally:
        await connection.close()


def test_initial_migration_round_trips_on_real_postgis(
    postgis_database_url: str,
) -> None:
    _alembic(postgis_database_url, "head")
    first_snapshot = _run(_schema_snapshot(postgis_database_url))

    assert first_snapshot["tables"] == EXPECTED_APPLICATION_TABLES
    spatial = first_snapshot["spatial"]
    assert spatial is not None
    assert spatial["storage_type"] == "geography"
    assert spatial["geometry_type"] == "Point"
    assert spatial["srid"] == 4326
    indexes = first_snapshot["indexes"]
    assert "ix_pois_location_gist" in indexes
    assert "USING gist (location)" in indexes["ix_pois_location_gist"]
    for index_name in (
        "ix_user_preferences_user_id",
        "ix_trips_user_id",
        "ix_itineraries_user_id",
    ):
        assert index_name in indexes
    assert set(first_snapshot["row_counts"].values()) == {0}

    _alembic(postgis_database_url, "base")
    downgraded_snapshot = _run(_schema_snapshot(postgis_database_url))
    assert downgraded_snapshot["tables"] == set()

    _alembic(postgis_database_url, "head")
    second_snapshot = _run(_schema_snapshot(postgis_database_url))
    assert second_snapshot["tables"] == EXPECTED_APPLICATION_TABLES
    assert set(second_snapshot["row_counts"].values()) == {0}


async def _assert_database_constraints(database_url: str) -> None:
    connection = await asyncpg.connect(
        _asyncpg_dsn(make_url(database_url))
    )
    transaction = connection.transaction()
    await transaction.start()
    try:
        first_user_id = uuid4()
        second_user_id = uuid4()
        trip_id = uuid4()
        itinerary_id = uuid4()
        await connection.execute(
            "INSERT INTO users (id, firebase_uid) VALUES ($1, $2)",
            first_user_id,
            "firebase-user-one",
        )
        await connection.execute(
            "INSERT INTO users (id, firebase_uid) VALUES ($1, $2)",
            second_user_id,
            "firebase-user-two",
        )

        with pytest.raises(asyncpg.UniqueViolationError):
            async with connection.transaction():
                await connection.execute(
                    "INSERT INTO users (id, firebase_uid) VALUES ($1, $2)",
                    uuid4(),
                    "firebase-user-one",
                )

        await connection.execute(
            """
            INSERT INTO user_preferences (id, user_id)
            VALUES ($1, $2)
            """,
            uuid4(),
            first_user_id,
        )
        with pytest.raises(asyncpg.UniqueViolationError):
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO user_preferences (id, user_id)
                    VALUES ($1, $2)
                    """,
                    uuid4(),
                    first_user_id,
                )

        await connection.execute(
            """
            INSERT INTO trips (id, user_id, title)
            VALUES ($1, $2, 'HCMC')
            """,
            trip_id,
            first_user_id,
        )
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO itineraries (id, user_id, trip_id, title)
                    VALUES ($1, $2, $3, 'Wrong owner')
                    """,
                    uuid4(),
                    second_user_id,
                    trip_id,
                )

        await connection.execute(
            """
            INSERT INTO itineraries (id, user_id, trip_id, title)
            VALUES ($1, $2, $3, 'Owned itinerary')
            """,
            itinerary_id,
            first_user_id,
            trip_id,
        )
        await connection.execute(
            """
            INSERT INTO itinerary_items
                (id, itinerary_id, title, position)
            VALUES ($1, $2, 'Morning', 0)
            """,
            uuid4(),
            itinerary_id,
        )
        with pytest.raises(asyncpg.UniqueViolationError):
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO itinerary_items
                        (id, itinerary_id, title, position)
                    VALUES ($1, $2, 'Duplicate position', 0)
                    """,
                    uuid4(),
                    itinerary_id,
                )

        await connection.execute(
            """
            INSERT INTO pois
                (id, canonical_name, city, category, location)
            VALUES (
                'hcmc-poi-test',
                'Test POI',
                'Ho Chi Minh City',
                'landmark',
                ST_SetSRID(ST_MakePoint(106.7, 10.77), 4326)::geography
            )
            """
        )
        await connection.execute(
            """
            INSERT INTO sources (id, source_type, label)
            VALUES ('source-test', 'curated', 'Curated test source')
            """
        )
        for price, currency in ((-1, "VND"), (1, "vnd"), (1, "VN")):
            with pytest.raises(asyncpg.CheckViolationError):
                async with connection.transaction():
                    await connection.execute(
                        """
                        INSERT INTO menu_items (
                            id, poi_id, source_id, item_name,
                            price_minor_units, currency_code,
                            source_type, source_updated_at
                        )
                        VALUES (
                            $1, 'hcmc-poi-test', 'source-test', 'Phở',
                            $2, $3, 'curated', now()
                        )
                        """,
                        f"menu-{price}-{currency}",
                        price,
                        currency,
                    )

        with pytest.raises(asyncpg.CheckViolationError):
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO narrations (
                        id, poi_id, language_code, content,
                        verification_status
                    )
                    VALUES (
                        'narration-invalid',
                        'hcmc-poi-test',
                        'vi',
                        'Unsupported content',
                        'fallback'
                    )
                    """
                )
        await connection.execute(
            """
            INSERT INTO narrations (
                id, poi_id, language_code, content,
                verification_status, fallback_source_label
            )
            VALUES (
                'narration-fallback',
                'hcmc-poi-test',
                'vi',
                'Explicit fallback content',
                'fallback',
                'Chưa có nguồn xác minh'
            )
            """
        )
    finally:
        await transaction.rollback()
        await connection.close()


def test_database_enforces_ownership_money_and_provenance(
    postgis_database_url: str,
) -> None:
    _alembic(postgis_database_url, "head")
    _run(_assert_database_constraints(postgis_database_url))


async def _assert_delete_behaviors(database_url: str) -> None:
    connection = await asyncpg.connect(
        _asyncpg_dsn(make_url(database_url))
    )
    transaction = connection.transaction()
    await transaction.start()
    try:
        user_id = uuid4()
        itinerary_id = uuid4()
        item_id = uuid4()
        await connection.execute(
            "INSERT INTO users (id, firebase_uid) VALUES ($1, $2)",
            user_id,
            "delete-behavior-user",
        )
        await connection.execute(
            """
            INSERT INTO itineraries (id, user_id, title)
            VALUES ($1, $2, 'Preserved itinerary')
            """,
            itinerary_id,
            user_id,
        )
        await connection.execute(
            """
            INSERT INTO pois
                (id, canonical_name, city, category, location)
            VALUES (
                'poi-delete-test',
                'Delete test',
                'Bangkok',
                'landmark',
                ST_SetSRID(ST_MakePoint(100.5, 13.75), 4326)::geography
            )
            """
        )
        await connection.execute(
            """
            INSERT INTO itinerary_items
                (id, itinerary_id, poi_id, title, position)
            VALUES ($1, $2, 'poi-delete-test', 'Fallback title', 0)
            """,
            item_id,
            itinerary_id,
        )
        await connection.execute(
            """
            INSERT INTO sources (id, source_type, label)
            VALUES ('delete-source', 'curated', 'Retained provenance')
            """
        )
        await connection.execute(
            """
            INSERT INTO narrations (
                id, poi_id, source_id, language_code, content,
                verification_status
            )
            VALUES (
                'delete-narration',
                'poi-delete-test',
                'delete-source',
                'vi',
                'Grounded content',
                'verified'
            )
            """
        )
        with pytest.raises(asyncpg.RestrictViolationError):
            async with connection.transaction():
                await connection.execute(
                    "DELETE FROM sources WHERE id = 'delete-source'"
                )

        await connection.execute(
            "DELETE FROM pois WHERE id = 'poi-delete-test'"
        )
        preserved = await connection.fetchrow(
            """
            SELECT poi_id, title
            FROM itinerary_items
            WHERE id = $1
            """,
            item_id,
        )
        assert preserved is not None
        assert preserved["poi_id"] is None
        assert preserved["title"] == "Fallback title"
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM narrations "
                "WHERE id = 'delete-narration'"
            )
            == 0
        )
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM sources WHERE id = 'delete-source'"
            )
            == 1
        )

        await connection.execute(
            "DELETE FROM itineraries WHERE id = $1",
            itinerary_id,
        )
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM itinerary_items WHERE id = $1",
                item_id,
            )
            == 0
        )

        trip_id = uuid4()
        owned_itinerary_id = uuid4()
        await connection.execute(
            """
            INSERT INTO trips (id, user_id, title)
            VALUES ($1, $2, 'Account deletion trip')
            """,
            trip_id,
            user_id,
        )
        await connection.execute(
            """
            INSERT INTO itineraries (id, user_id, trip_id, title)
            VALUES ($1, $2, $3, 'Account deletion itinerary')
            """,
            owned_itinerary_id,
            user_id,
            trip_id,
        )
        await connection.execute("DELETE FROM users WHERE id = $1", user_id)
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM trips WHERE id = $1",
                trip_id,
            )
            == 0
        )
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM itineraries WHERE id = $1",
                owned_itinerary_id,
            )
            == 0
        )
    finally:
        await transaction.rollback()
        await connection.close()


def test_delete_behaviors_preserve_user_plan_context(
    postgis_database_url: str,
) -> None:
    _alembic(postgis_database_url, "head")
    _run(_assert_delete_behaviors(postgis_database_url))
