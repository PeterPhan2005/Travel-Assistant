"""User identity and minimal versioned preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.trip import Itinerary, ItineraryTombstone, Trip


class User(TimestampMixin, Base):
    """Server owner mapped uniquely to one Firebase Authentication UID."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "btrim(firebase_uid) <> ''",
            name="firebase_uid_nonblank",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )

    preferences: Mapped[UserPreference | None] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )
    trips: Mapped[list[Trip]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    itineraries: Mapped[list[Itinerary]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    itinerary_tombstones: Mapped[list[ItineraryTombstone]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserPreference(TimestampMixin, Base):
    """One versioned JSON preference document per owner."""

    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint(
            "schema_version > 0",
            name="schema_version_positive",
        ),
        Index(
            "ix_user_preferences_user_id",
            "user_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    preferences: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    owner: Mapped[User] = relationship(back_populates="preferences")
