"""Owned trip, itinerary, and ordered itinerary-item mappings."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.content import Poi
    from app.db.models.user import User


class Trip(TimestampMixin, Base):
    """Minimal owner-scoped context for a journey."""

    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("btrim(title) <> ''", name="title_nonblank"),
        CheckConstraint(
            "destination_city IS NULL OR btrim(destination_city) <> ''",
            name="destination_city_nonblank",
        ),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="date_order",
        ),
        UniqueConstraint("id", "user_id", name="uq_trips_id_user_id"),
        Index("ix_trips_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    destination_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    owner: Mapped[User] = relationship(
        back_populates="trips",
        overlaps="itineraries,owner",
    )
    itineraries: Mapped[list[Itinerary]] = relationship(
        back_populates="trip",
        passive_deletes=True,
        overlaps="itineraries,owner",
    )


class Itinerary(TimestampMixin, Base):
    """An owner-scoped ordered plan, optionally attached to an owned trip."""

    __tablename__ = "itineraries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["trip_id", "user_id"],
            ["trips.id", "trips.user_id"],
            name="fk_itineraries_trip_id_user_id_trips",
            ondelete="RESTRICT",
        ),
        CheckConstraint("btrim(title) <> ''", name="title_nonblank"),
        Index("ix_itineraries_user_id", "user_id"),
        Index("ix_itineraries_trip_id", "trip_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    trip_id: Mapped[UUID | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    owner: Mapped[User] = relationship(
        back_populates="itineraries",
        overlaps="itineraries,owner,trip",
    )
    trip: Mapped[Trip | None] = relationship(
        back_populates="itineraries",
        overlaps="itineraries,owner",
    )
    items: Mapped[list[ItineraryItem]] = relationship(
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryItem.position",
        passive_deletes=True,
        single_parent=True,
    )


class ItineraryItem(TimestampMixin, Base):
    """One deterministic position in an itinerary."""

    __tablename__ = "itinerary_items"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_nonnegative"),
        CheckConstraint("btrim(title) <> ''", name="title_nonblank"),
        CheckConstraint(
            "travel_time_minutes IS NULL OR travel_time_minutes >= 0",
            name="travel_time_nonnegative",
        ),
        CheckConstraint(
            "end_at IS NULL OR start_at IS NULL OR end_at >= start_at",
            name="time_order",
        ),
        UniqueConstraint(
            "itinerary_id",
            "position",
            name="uq_itinerary_items_itinerary_id_position",
        ),
        Index("ix_itinerary_items_poi_id", "poi_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    itinerary_id: Mapped[UUID] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
    )
    poi_id: Mapped[str | None] = mapped_column(
        ForeignKey("pois.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    travel_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    itinerary: Mapped[Itinerary] = relationship(back_populates="items")
    poi: Mapped[Poi | None] = relationship(back_populates="itinerary_items")
