"""Transactional deterministic upserts into the fixed T030 schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from geoalchemy2.elements import WKTElement
from sqlalchemy import Table, func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.data_pipeline.loader import LoadedPackage
from app.data_pipeline.models import CuratedPackageV1
from app.data_pipeline.validation import validate_package_semantics
from app.db.models import MenuItem, Narration, Poi, PoiSource, Source


class UnsafeSeedTargetError(RuntimeError):
    """Raised before connection when a database is not visibly non-production."""


class UnvalidatedPackageError(RuntimeError):
    """Raised before connection when semantic validation was bypassed."""


@dataclass(frozen=True)
class SeedSummary:
    """Safe controlled summary for one package transaction."""

    package_id: str
    city_code: str
    sources: int
    pois: int
    poi_source_links: int
    menu_items: int
    narrations: int


def assert_safe_seed_target(database_url: str) -> None:
    """Allow only visibly local/development or disposable test databases."""
    parsed = make_url(database_url)
    database = (parsed.database or "").lower()
    host = (parsed.host or "").lower()
    visibly_non_production = any(
        marker in database for marker in ("test", "t031", "dev", "local")
    )
    default_local = database == "travel_assistant" and host in {
        "127.0.0.1",
        "localhost",
        "database",
    }
    if not (visibly_non_production or default_local):
        raise UnsafeSeedTargetError(
            "Refusing to seed a database that is not visibly local, "
            "development, or test-only."
        )


def assert_test_database(database_url: str) -> None:
    """Require a visibly disposable T031 database for integration tests."""
    database = (make_url(database_url).database or "").lower()
    if "test" not in database and "t031" not in database:
        raise UnsafeSeedTargetError(
            "Integration tests require a visibly test-only database name."
        )


async def _upsert_rows(
    connection: AsyncConnection,
    table: Table,
    rows: list[dict[str, Any]],
    mutable_columns: tuple[str, ...],
) -> None:
    if not rows:
        return
    statement = insert(table).values(rows)
    excluded = statement.excluded
    changed = or_(
        *(
            table.c[column].is_distinct_from(getattr(excluded, column))
            for column in mutable_columns
        )
    )
    values = {
        column: getattr(excluded, column) for column in mutable_columns
    }
    values["updated_at"] = func.now()
    await connection.execute(
        statement.on_conflict_do_update(
            index_elements=[table.c.id],
            set_=values,
            where=changed,
        )
    )


async def _upsert_sources(
    connection: AsyncConnection,
    package: CuratedPackageV1,
) -> None:
    table = cast(Table, Source.__table__)
    await _upsert_rows(
        connection,
        table,
        [
            {
                "id": source.id,
                "source_type": source.source_type.value,
                "label": source.label,
                "publisher": source.publisher,
                "url": str(source.url) if source.url is not None else None,
                "published_at": source.published_at,
                "retrieved_at": source.retrieved_at,
            }
            for source in package.sources
        ],
        (
            "source_type",
            "label",
            "publisher",
            "url",
            "published_at",
            "retrieved_at",
        ),
    )


async def _upsert_pois(
    connection: AsyncConnection,
    package: CuratedPackageV1,
) -> None:
    table = cast(Table, Poi.__table__)
    await _upsert_rows(
        connection,
        table,
        [
            {
                "id": poi.id,
                "canonical_name": poi.canonical_name,
                "city": poi.city_code.value,
                "area": poi.area,
                "category": poi.category,
                "address": poi.address,
                "short_description": poi.short_description,
                "location": WKTElement(
                    (
                        f"POINT({poi.location.longitude} "
                        f"{poi.location.latitude})"
                    ),
                    srid=4326,
                ),
            }
            for poi in package.pois
        ],
        (
            "canonical_name",
            "city",
            "area",
            "category",
            "address",
            "short_description",
            "location",
        ),
    )


async def _upsert_poi_source_links(
    connection: AsyncConnection,
    package: CuratedPackageV1,
) -> None:
    rows = [
        {"poi_id": poi.id, "source_id": source_id}
        for poi in package.pois
        for source_id in poi.source_ids
    ]
    if not rows:
        return
    table = cast(Table, PoiSource.__table__)
    statement = insert(table).values(rows)
    await connection.execute(
        statement.on_conflict_do_nothing(
            index_elements=[table.c.poi_id, table.c.source_id]
        )
    )


async def _upsert_menu_items(
    connection: AsyncConnection,
    package: CuratedPackageV1,
) -> None:
    table = cast(Table, MenuItem.__table__)
    await _upsert_rows(
        connection,
        table,
        [
            {
                "id": item.id,
                "poi_id": item.poi_id,
                "source_id": item.source_id,
                "item_name": item.item_name,
                "price_minor_units": item.price_minor_units,
                "currency_code": item.currency_code,
                "source_type": item.source_type.value,
                "source_updated_at": item.source_updated_at,
            }
            for item in package.menu_items
        ],
        (
            "poi_id",
            "source_id",
            "item_name",
            "price_minor_units",
            "currency_code",
            "source_type",
            "source_updated_at",
        ),
    )


async def _upsert_narrations(
    connection: AsyncConnection,
    package: CuratedPackageV1,
) -> None:
    table = cast(Table, Narration.__table__)
    await _upsert_rows(
        connection,
        table,
        [
            {
                "id": narration.id,
                "poi_id": narration.poi_id,
                "source_id": narration.source_id,
                "language_code": narration.language_code,
                "title": narration.title,
                "content": narration.content,
                "verification_status": (
                    narration.verification_status.value
                ),
                "fallback_source_label": (
                    narration.fallback_source_label
                ),
            }
            for narration in package.narrations
        ],
        (
            "poi_id",
            "source_id",
            "language_code",
            "title",
            "content",
            "verification_status",
            "fallback_source_label",
        ),
    )


def _summary(package: CuratedPackageV1) -> SeedSummary:
    return SeedSummary(
        package_id=package.package.package_id,
        city_code=package.package.city_code.value,
        sources=len(package.sources),
        pois=len(package.pois),
        poi_source_links=sum(
            len(poi.source_ids) for poi in package.pois
        ),
        menu_items=len(package.menu_items),
        narrations=len(package.narrations),
    )


async def seed_loaded_package(
    loaded: LoadedPackage,
    database_url: str,
    *,
    engine: AsyncEngine | None = None,
) -> SeedSummary:
    """Validate before connection and upsert a package in one transaction."""
    issues = validate_package_semantics(
        loaded.package,
        loaded.source_path,
    )
    if issues:
        raise UnvalidatedPackageError(
            f"Package has {len(issues)} validation issue(s)."
        )
    assert_safe_seed_target(database_url)
    owned_engine = engine is None
    resolved_engine = engine or create_async_engine(
        database_url,
        poolclass=NullPool,
    )
    try:
        async with resolved_engine.begin() as connection:
            await _upsert_sources(connection, loaded.package)
            await _upsert_pois(connection, loaded.package)
            await _upsert_poi_source_links(connection, loaded.package)
            await _upsert_menu_items(connection, loaded.package)
            await _upsert_narrations(connection, loaded.package)
    finally:
        if owned_engine:
            await resolved_engine.dispose()
    return _summary(loaded.package)


def in_memory_loaded_package(package: CuratedPackageV1) -> LoadedPackage:
    """Create a labelled package for focused programmatic tests."""
    return LoadedPackage(Path("<in-memory>"), package)
