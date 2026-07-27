"""Typed declarative base and reusable mapping columns."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.metadata import metadata


class Base(DeclarativeBase):
    """Base for every server database model."""

    metadata = metadata


class TimestampMixin:
    """Timezone-aware creation and modification timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
