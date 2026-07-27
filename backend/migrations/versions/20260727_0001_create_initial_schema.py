"""Create the initial PostgreSQL/PostGIS application schema.

The database role running this first upgrade must be allowed to install the
PostGIS extension when infrastructure has not installed it already. Downgrade
does not remove the shared extension.

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

from collections.abc import Sequence
from datetime import datetime

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column[datetime], sa.Column[datetime]]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    """Create all T030 tables, constraints, and indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(firebase_uid) <> ''",
            name="ck_users_firebase_uid_nonblank",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint(
            "firebase_uid",
            name="uq_users_firebase_uid",
        ),
    )
    op.create_table(
        "pois",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column(
            "canonical_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("area", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
            ),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(canonical_name) <> ''",
            name="ck_pois_canonical_name_nonblank",
        ),
        sa.CheckConstraint(
            "btrim(category) <> ''",
            name="ck_pois_category_nonblank",
        ),
        sa.CheckConstraint(
            "btrim(city) <> ''",
            name="ck_pois_city_nonblank",
        ),
        sa.CheckConstraint("btrim(id) <> ''", name="ck_pois_id_nonblank"),
        sa.PrimaryKeyConstraint("id", name="pk_pois"),
    )
    op.create_index(
        "ix_pois_city_category",
        "pois",
        ["city", "category"],
        unique=False,
    )
    op.create_index(
        "ix_pois_location_gist",
        "pois",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("publisher", sa.String(length=200), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "retrieved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(id) <> ''",
            name="ck_sources_id_nonblank",
        ),
        sa.CheckConstraint(
            "btrim(label) <> ''",
            name="ck_sources_label_nonblank",
        ),
        sa.CheckConstraint(
            "btrim(source_type) <> ''",
            name="ck_sources_type_nonblank",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
    )
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "schema_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "schema_version > 0",
            name="ck_user_preferences_schema_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_preferences_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_preferences"),
    )
    op.create_index(
        "ix_user_preferences_user_id",
        "user_preferences",
        ["user_id"],
        unique=True,
    )
    op.create_table(
        "trips",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "destination_city",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL "
            "OR end_date >= start_date",
            name="ck_trips_date_order",
        ),
        sa.CheckConstraint(
            "destination_city IS NULL OR btrim(destination_city) <> ''",
            name="ck_trips_destination_city_nonblank",
        ),
        sa.CheckConstraint(
            "btrim(title) <> ''",
            name="ck_trips_title_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_trips_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trips"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            name="uq_trips_id_user_id",
        ),
    )
    op.create_index(
        "ix_trips_user_id",
        "trips",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "itineraries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(title) <> ''",
            name="ck_itineraries_title_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id", "user_id"],
            ["trips.id", "trips.user_id"],
            name="fk_itineraries_trip_id_user_id_trips",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_itineraries_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_itineraries"),
    )
    op.create_index(
        "ix_itineraries_trip_id",
        "itineraries",
        ["trip_id"],
        unique=False,
    )
    op.create_index(
        "ix_itineraries_user_id",
        "itineraries",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "poi_sources",
        sa.Column("poi_id", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(
            ["poi_id"],
            ["pois.id"],
            name="fk_poi_sources_poi_id_pois",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_poi_sources_source_id_sources",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "poi_id",
            "source_id",
            name="pk_poi_sources",
        ),
    )
    op.create_table(
        "menu_items",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("poi_id", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("item_name", sa.String(length=200), nullable=False),
        sa.Column("price_minor_units", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column(
            "source_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'",
            name="ck_menu_items_currency_code_iso_shape",
        ),
        sa.CheckConstraint(
            "btrim(id) <> ''",
            name="ck_menu_items_id_nonblank",
        ),
        sa.CheckConstraint(
            "btrim(item_name) <> ''",
            name="ck_menu_items_item_name_nonblank",
        ),
        sa.CheckConstraint(
            "price_minor_units >= 0",
            name="ck_menu_items_price_nonnegative",
        ),
        sa.CheckConstraint(
            "btrim(source_type) <> ''",
            name="ck_menu_items_source_type_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["poi_id"],
            ["pois.id"],
            name="fk_menu_items_poi_id_pois",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_menu_items_source_id_sources",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_menu_items"),
    )
    op.create_index(
        "ix_menu_items_poi_id",
        "menu_items",
        ["poi_id"],
        unique=False,
    )
    op.create_index(
        "ix_menu_items_source_id",
        "menu_items",
        ["source_id"],
        unique=False,
    )
    op.create_table(
        "narrations",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("poi_id", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "fallback_source_label",
            sa.String(length=200),
            nullable=True,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(content) <> ''",
            name="ck_narrations_content_nonblank",
        ),
        sa.CheckConstraint(
            "btrim(id) <> ''",
            name="ck_narrations_id_nonblank",
        ),
        sa.CheckConstraint(
            "btrim(language_code) <> ''",
            name="ck_narrations_language_code_nonblank",
        ),
        sa.CheckConstraint(
            "source_id IS NOT NULL OR "
            "(fallback_source_label IS NOT NULL "
            "AND btrim(fallback_source_label) <> '')",
            name="ck_narrations_source_or_fallback",
        ),
        sa.CheckConstraint(
            "btrim(verification_status) <> ''",
            name="ck_narrations_verification_status_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["poi_id"],
            ["pois.id"],
            name="fk_narrations_poi_id_pois",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_narrations_source_id_sources",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_narrations"),
        sa.UniqueConstraint(
            "poi_id",
            "language_code",
            name="uq_narrations_poi_id_language_code",
        ),
    )
    op.create_index(
        "ix_narrations_source_id",
        "narrations",
        ["source_id"],
        unique=False,
    )
    op.create_table(
        "itinerary_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("itinerary_id", sa.Uuid(), nullable=False),
        sa.Column("poi_id", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "start_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("travel_time_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "end_at IS NULL OR start_at IS NULL OR end_at >= start_at",
            name="ck_itinerary_items_time_order",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_itinerary_items_position_nonnegative",
        ),
        sa.CheckConstraint(
            "btrim(title) <> ''",
            name="ck_itinerary_items_title_nonblank",
        ),
        sa.CheckConstraint(
            "travel_time_minutes IS NULL OR travel_time_minutes >= 0",
            name="ck_itinerary_items_travel_time_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["itinerary_id"],
            ["itineraries.id"],
            name="fk_itinerary_items_itinerary_id_itineraries",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["poi_id"],
            ["pois.id"],
            name="fk_itinerary_items_poi_id_pois",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_itinerary_items"),
        sa.UniqueConstraint(
            "itinerary_id",
            "position",
            name="uq_itinerary_items_itinerary_id_position",
        ),
    )
    op.create_index(
        "ix_itinerary_items_poi_id",
        "itinerary_items",
        ["poi_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop application objects in dependency-safe reverse order."""
    op.drop_index(
        "ix_itinerary_items_poi_id",
        table_name="itinerary_items",
    )
    op.drop_table("itinerary_items")
    op.drop_index("ix_narrations_source_id", table_name="narrations")
    op.drop_table("narrations")
    op.drop_index("ix_menu_items_source_id", table_name="menu_items")
    op.drop_index("ix_menu_items_poi_id", table_name="menu_items")
    op.drop_table("menu_items")
    op.drop_table("poi_sources")
    op.drop_index("ix_itineraries_user_id", table_name="itineraries")
    op.drop_index("ix_itineraries_trip_id", table_name="itineraries")
    op.drop_table("itineraries")
    op.drop_index("ix_trips_user_id", table_name="trips")
    op.drop_table("trips")
    op.drop_index(
        "ix_user_preferences_user_id",
        table_name="user_preferences",
    )
    op.drop_table("user_preferences")
    op.drop_table("sources")
    op.drop_index("ix_pois_location_gist", table_name="pois")
    op.drop_index("ix_pois_city_category", table_name="pois")
    op.drop_table("pois")
    op.drop_table("users")
