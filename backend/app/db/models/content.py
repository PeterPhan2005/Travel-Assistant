"""Curated POI content and normalized provenance mappings."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.trip import ItineraryItem


class Poi(TimestampMixin, Base):
    """A stable curated point of interest."""

    __tablename__ = "pois"
    __table_args__ = (
        CheckConstraint("btrim(id) <> ''", name="id_nonblank"),
        CheckConstraint(
            "btrim(canonical_name) <> ''",
            name="canonical_name_nonblank",
        ),
        CheckConstraint("btrim(city) <> ''", name="city_nonblank"),
        CheckConstraint("btrim(category) <> ''", name="category_nonblank"),
        Index("ix_pois_city_category", "city", "category"),
        Index(
            "ix_pois_location_gist",
            "location",
            postgresql_using="gist",
        ),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    short_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    location: Mapped[object] = mapped_column(
        Geography(
            geometry_type="POINT",
            srid=4326,
            spatial_index=False,
        ),
        nullable=False,
    )

    source_links: Mapped[list[PoiSource]] = relationship(
        back_populates="poi",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    menu_items: Mapped[list[MenuItem]] = relationship(
        back_populates="poi",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    narrations: Mapped[list[Narration]] = relationship(
        back_populates="poi",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    itinerary_items: Mapped[list[ItineraryItem]] = relationship(
        back_populates="poi",
        passive_deletes=True,
    )


class Source(TimestampMixin, Base):
    """Reusable provenance metadata for curated facts."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("btrim(id) <> ''", name="id_nonblank"),
        CheckConstraint("btrim(source_type) <> ''", name="type_nonblank"),
        CheckConstraint("btrim(label) <> ''", name="label_nonblank"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    publisher: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    poi_links: Mapped[list[PoiSource]] = relationship(
        back_populates="source",
        passive_deletes="all",
    )
    menu_items: Mapped[list[MenuItem]] = relationship(
        back_populates="source",
        passive_deletes="all",
    )
    narrations: Mapped[list[Narration]] = relationship(
        back_populates="source",
        passive_deletes="all",
    )


class PoiSource(Base):
    """Normalized many-to-many provenance link for a POI."""

    __tablename__ = "poi_sources"

    poi_id: Mapped[str] = mapped_column(
        ForeignKey("pois.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    poi: Mapped[Poi] = relationship(back_populates="source_links")
    source: Mapped[Source] = relationship(back_populates="poi_links")


class MenuItem(TimestampMixin, Base):
    """A POI-owned menu price with explicit source and freshness."""

    __tablename__ = "menu_items"
    __table_args__ = (
        CheckConstraint("btrim(id) <> ''", name="id_nonblank"),
        CheckConstraint("btrim(item_name) <> ''", name="item_name_nonblank"),
        CheckConstraint(
            "price_minor_units >= 0",
            name="price_nonnegative",
        ),
        CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'",
            name="currency_code_iso_shape",
        ),
        CheckConstraint(
            "btrim(source_type) <> ''",
            name="source_type_nonblank",
        ),
        Index("ix_menu_items_poi_id", "poi_id"),
        Index("ix_menu_items_source_id", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    poi_id: Mapped[str] = mapped_column(
        ForeignKey("pois.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    price_minor_units: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    poi: Mapped[Poi] = relationship(back_populates="menu_items")
    source: Mapped[Source] = relationship(back_populates="menu_items")


class Narration(TimestampMixin, Base):
    """A grounded narration, or one carrying an explicit fallback label."""

    __tablename__ = "narrations"
    __table_args__ = (
        CheckConstraint("btrim(id) <> ''", name="id_nonblank"),
        CheckConstraint(
            "btrim(language_code) <> ''",
            name="language_code_nonblank",
        ),
        CheckConstraint("btrim(content) <> ''", name="content_nonblank"),
        CheckConstraint(
            "btrim(verification_status) <> ''",
            name="verification_status_nonblank",
        ),
        CheckConstraint(
            "source_id IS NOT NULL OR "
            "(fallback_source_label IS NOT NULL "
            "AND btrim(fallback_source_label) <> '')",
            name="source_or_fallback",
        ),
        UniqueConstraint(
            "poi_id",
            "language_code",
            name="uq_narrations_poi_id_language_code",
        ),
        Index("ix_narrations_source_id", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    poi_id: Mapped[str] = mapped_column(
        ForeignKey("pois.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=True,
    )
    language_code: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    fallback_source_label: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    poi: Mapped[Poi] = relationship(back_populates="narrations")
    source: Mapped[Source | None] = relationship(
        back_populates="narrations",
    )
