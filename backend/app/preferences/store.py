"""Preference persistence protocol and PostgreSQL implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.db.models.user import User, UserPreference
from app.preferences.contracts import PreferenceDocument


@dataclass(frozen=True, slots=True)
class StoredPreference:
    """Persistence result without ORM or owner identifiers."""

    schema_version: int
    preferences: dict[str, object]
    updated_at: datetime


class PreferenceStoreError(Exception):
    """A sanitized preference persistence operation failed."""


class PreferenceStore(Protocol):
    """Persistence seam used by the deterministic preference service."""

    async def get(self, firebase_uid: str) -> StoredPreference | None:
        """Return only the authenticated owner's preference row."""
        ...

    async def replace(
        self,
        firebase_uid: str,
        document: PreferenceDocument,
    ) -> StoredPreference:
        """Atomically replace the authenticated owner's complete document."""
        ...


class SqlAlchemyPreferenceStore:
    """Request-scoped async PostgreSQL preference persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, firebase_uid: str) -> StoredPreference | None:
        """Read without creating rows or committing."""
        try:
            result = await self._session.execute(
                select(
                    UserPreference.schema_version,
                    UserPreference.preferences,
                    UserPreference.updated_at,
                )
                .join(User, User.id == UserPreference.user_id)
                .where(User.firebase_uid == firebase_uid)
            )
            row = result.one_or_none()
        except SQLAlchemyError as error:
            raise PreferenceStoreError from error
        if row is None:
            return None
        return StoredPreference(
            schema_version=row.schema_version,
            preferences=dict(row.preferences),
            updated_at=row.updated_at,
        )

    async def replace(
        self,
        firebase_uid: str,
        document: PreferenceDocument,
    ) -> StoredPreference:
        """Upsert the owner and one document in one transaction and commit."""
        try:
            async with self._session.begin():
                user_id = (
                    await self._session.execute(
                        insert(User)
                        .values(id=uuid4(), firebase_uid=firebase_uid)
                        .on_conflict_do_update(
                            index_elements=[User.firebase_uid],
                            set_={"firebase_uid": firebase_uid},
                        )
                        .returning(User.id)
                    )
                ).scalar_one()
                row = (
                    await self._session.execute(
                        insert(UserPreference)
                        .values(
                            id=uuid4(),
                            user_id=user_id,
                            schema_version=document.schema_version,
                            preferences=document.preferences,
                        )
                        .on_conflict_do_update(
                            index_elements=[UserPreference.user_id],
                            set_={
                                "schema_version": document.schema_version,
                                "preferences": document.preferences,
                                "updated_at": func.now(),
                            },
                        )
                        .returning(
                            UserPreference.schema_version,
                            UserPreference.preferences,
                            UserPreference.updated_at,
                        )
                    )
                ).one()
        except SQLAlchemyError as error:
            await self._session.rollback()
            raise PreferenceStoreError from error
        return StoredPreference(
            schema_version=row.schema_version,
            preferences=dict(row.preferences),
            updated_at=row.updated_at,
        )

