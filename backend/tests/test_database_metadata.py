"""Static tests for the SQLAlchemy schema contract."""

from __future__ import annotations

import subprocess
import sys
from typing import cast

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Table, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.db.metadata import NAMING_CONVENTION
from app.db.models import (
    Itinerary,
    ItineraryItem,
    MenuItem,
    Narration,
    Poi,
    PoiSource,
    Source,
    Trip,
    User,
    UserPreference,
)

EXPECTED_TABLES = {
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


def test_metadata_contains_exact_t030_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES
    assert Base.metadata.naming_convention == NAMING_CONVENTION


def test_models_use_typed_relationships_without_mapper_errors() -> None:
    configure_mappers()

    assert User.preferences.property.uselist is False
    assert User.trips.property.back_populates == "owner"
    assert User.itineraries.property.back_populates == "owner"
    assert Trip.itineraries.property.back_populates == "trip"
    assert Itinerary.items.property.back_populates == "itinerary"
    assert ItineraryItem.poi.property.back_populates == "itinerary_items"
    assert Poi.source_links.property.back_populates == "poi"
    assert Poi.menu_items.property.back_populates == "poi"
    assert Poi.narrations.property.back_populates == "poi"
    assert PoiSource.source.property.back_populates == "poi_links"
    assert MenuItem.source.property.back_populates == "menu_items"
    assert Narration.source.property.back_populates == "narrations"
    assert Source.poi_links.property.passive_deletes == "all"


def test_owner_columns_and_indexes_are_explicit() -> None:
    expected_owner_indexes = {
        cast(Table, UserPreference.__table__): (
            "ix_user_preferences_user_id",
            True,
        ),
        cast(Table, Trip.__table__): ("ix_trips_user_id", False),
        cast(Table, Itinerary.__table__): (
            "ix_itineraries_user_id",
            False,
        ),
    }

    for table, (expected_name, expected_unique) in (
        expected_owner_indexes.items()
    ):
        assert "user_id" in table.c
        owner_index = next(
            index for index in table.indexes if index.name == expected_name
        )
        assert owner_index.unique is expected_unique
        assert list(owner_index.columns.keys()) == ["user_id"]


def test_uniqueness_and_delete_behaviors_match_retention_rules() -> None:
    user_uniques = {
        tuple(constraint.columns.keys())
        for constraint in cast(Table, User.__table__).constraints
        if isinstance(constraint, UniqueConstraint)
    }
    item_uniques = {
        tuple(constraint.columns.keys())
        for constraint in cast(Table, ItineraryItem.__table__).constraints
        if isinstance(constraint, UniqueConstraint)
    }
    itinerary_foreign_keys = {
        tuple(constraint.column_keys): constraint.ondelete
        for constraint in cast(
            Table, Itinerary.__table__
        ).foreign_key_constraints
    }

    assert ("firebase_uid",) in user_uniques
    assert ("itinerary_id", "position") in item_uniques
    assert itinerary_foreign_keys[("trip_id", "user_id")] == "RESTRICT"
    itinerary_fk = next(
        iter(ItineraryItem.__table__.c.itinerary_id.foreign_keys)
    )
    poi_fk = next(iter(ItineraryItem.__table__.c.poi_id.foreign_keys))
    assert itinerary_fk.ondelete == "CASCADE"
    assert poi_fk.ondelete == "SET NULL"


def test_spatial_and_timestamp_metadata_are_explicit() -> None:
    location_type = Poi.__table__.c.location.type
    assert isinstance(location_type, Geography)
    assert location_type.geometry_type == "POINT"
    assert location_type.srid == 4326
    spatial_index = next(
        index
        for index in cast(Table, Poi.__table__).indexes
        if index.name == "ix_pois_location_gist"
    )
    assert spatial_index.dialect_options["postgresql"]["using"] == "gist"

    for table in (
        User.__table__,
        UserPreference.__table__,
        Trip.__table__,
        Itinerary.__table__,
        ItineraryItem.__table__,
        Poi.__table__,
        Source.__table__,
        MenuItem.__table__,
        Narration.__table__,
    ):
        for column_name in ("created_at", "updated_at"):
            column_type = table.c[column_name].type
            assert isinstance(column_type, DateTime)
            assert column_type.timezone is True
            assert table.c[column_name].nullable is False


def test_importing_models_does_not_connect_or_initialize_firebase() -> None:
    script = """
import asyncpg
import firebase_admin
import sqlalchemy.ext.asyncio

def fail(*args, **kwargs):
    raise AssertionError("external initialization during model import")

asyncpg.connect = fail
firebase_admin.initialize_app = fail
sqlalchemy.ext.asyncio.create_async_engine = fail

import app.db.models
from app.db.base import Base

assert "pois" in Base.metadata.tables
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
