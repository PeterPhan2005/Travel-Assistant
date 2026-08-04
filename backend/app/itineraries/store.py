"""Saved-itinerary persistence protocol and PostgreSQL implementation."""

from __future__ import annotations

from datetime import datetime, time
from typing import Protocol
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

from app.db.models.trip import (
    Itinerary,
    ItineraryItem,
    ItineraryTombstone,
)
from app.db.models.user import User
from app.agents.contracts import SupportedCity
from app.itineraries.contracts import (
    ItineraryDeleteResponse,
    ItineraryReplaceRequest,
    SavedItineraryItem,
    SavedItineraryResponse,
)


class ItineraryStoreError(Exception):
    """A sanitized itinerary persistence operation failed."""


class ItineraryNotFoundError(Exception):
    """The ID is absent for this owner, including cross-owner IDs."""


class ItineraryConflictError(Exception):
    """The supplied optimistic revision does not match current state."""


class ItineraryStore(Protocol):
    """Persistence seam for authenticated full-snapshot itinerary CRUD."""

    async def list(self, firebase_uid: str) -> tuple[SavedItineraryResponse, ...]:
        ...

    async def get(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
    ) -> SavedItineraryResponse | None:
        ...

    async def replace(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
        snapshot: ItineraryReplaceRequest,
    ) -> SavedItineraryResponse:
        ...

    async def delete(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
        base_revision: int,
    ) -> ItineraryDeleteResponse:
        ...


class SqlAlchemyItineraryStore:
    """Request-scoped async PostgreSQL saved-itinerary persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, firebase_uid: str) -> tuple[SavedItineraryResponse, ...]:
        try:
            result = await self._session.execute(
                select(Itinerary)
                .join(User, User.id == Itinerary.user_id)
                .where(User.firebase_uid == firebase_uid)
                .options(selectinload(Itinerary.items))
                .order_by(
                    Itinerary.local_date.desc(),
                    Itinerary.updated_at.desc(),
                    Itinerary.id.asc(),
                )
            )
            rows = result.scalars().all()
            return tuple(_response_from_row(row) for row in rows)
        except SQLAlchemyError as error:
            raise ItineraryStoreError from error

    async def get(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
    ) -> SavedItineraryResponse | None:
        try:
            result = await self._session.execute(
                select(Itinerary)
                .join(User, User.id == Itinerary.user_id)
                .where(
                    User.firebase_uid == firebase_uid,
                    Itinerary.id == itinerary_id,
                )
                .options(selectinload(Itinerary.items))
            )
            row = result.scalar_one_or_none()
            return None if row is None else _response_from_row(row)
        except SQLAlchemyError as error:
            raise ItineraryStoreError from error

    async def replace(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
        snapshot: ItineraryReplaceRequest,
    ) -> SavedItineraryResponse:
        try:
            async with self._session.begin():
                await self._lock_itinerary(itinerary_id)
                owner_id = await self._owner_id(firebase_uid)
                tombstone = await self._tombstone(itinerary_id)
                current = await self._itinerary(itinerary_id)
                _require_owned_or_absent(owner_id, current, tombstone)
                if tombstone is not None:
                    raise ItineraryConflictError
                if current is None:
                    if snapshot.base_revision != 0:
                        raise ItineraryConflictError
                    revision = 1
                    current = Itinerary(
                        id=itinerary_id,
                        user_id=owner_id,
                        trip_id=None,
                        title=snapshot.title,
                        revision=revision,
                        city=snapshot.city.value,
                        local_date=snapshot.local_date,
                        timezone=snapshot.timezone,
                        start_local_time=snapshot.start_local_time,
                        end_local_time=snapshot.end_local_time,
                        assumptions=list(snapshot.assumptions),
                        warnings=list(snapshot.warnings),
                    )
                    self._session.add(current)
                else:
                    if snapshot.base_revision != current.revision:
                        raise ItineraryConflictError
                    revision = current.revision + 1
                    current.title = snapshot.title
                    current.revision = revision
                    current.city = snapshot.city.value
                    current.local_date = snapshot.local_date
                    current.timezone = snapshot.timezone
                    current.start_local_time = snapshot.start_local_time
                    current.end_local_time = snapshot.end_local_time
                    current.assumptions = list(snapshot.assumptions)
                    current.warnings = list(snapshot.warnings)
                    await self._session.execute(
                        delete(ItineraryItem).where(
                            ItineraryItem.itinerary_id == itinerary_id
                        )
                    )
                await self._session.flush()
                self._session.add_all(
                    _item_rows(itinerary_id, snapshot)
                )
                await self._session.flush()
        except (ItineraryConflictError, ItineraryNotFoundError):
            raise
        except SQLAlchemyError as error:
            await self._session.rollback()
            raise ItineraryStoreError from error
        return _response_from_snapshot(itinerary_id, revision, snapshot)

    async def delete(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
        base_revision: int,
    ) -> ItineraryDeleteResponse:
        try:
            async with self._session.begin():
                await self._lock_itinerary(itinerary_id)
                owner_id = await self._owner_id(firebase_uid)
                tombstone = await self._tombstone(itinerary_id)
                current = await self._itinerary(itinerary_id)
                _require_owned_or_absent(owner_id, current, tombstone)
                if tombstone is not None:
                    if base_revision > tombstone.revision:
                        raise ItineraryConflictError
                    revision = tombstone.revision
                elif current is None:
                    if base_revision != 0:
                        raise ItineraryConflictError
                    revision = 1
                    self._session.add(
                        ItineraryTombstone(
                            itinerary_id=itinerary_id,
                            user_id=owner_id,
                            revision=revision,
                        )
                    )
                else:
                    if base_revision != current.revision:
                        raise ItineraryConflictError
                    revision = current.revision + 1
                    await self._session.delete(current)
                    await self._session.flush()
                    self._session.add(
                        ItineraryTombstone(
                            itinerary_id=itinerary_id,
                            user_id=owner_id,
                            revision=revision,
                        )
                    )
                await self._session.flush()
        except (ItineraryConflictError, ItineraryNotFoundError):
            raise
        except SQLAlchemyError as error:
            await self._session.rollback()
            raise ItineraryStoreError from error
        return ItineraryDeleteResponse(id=itinerary_id, revision=revision)

    async def _owner_id(self, firebase_uid: str) -> UUID:
        return (
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

    async def _lock_itinerary(self, itinerary_id: UUID) -> None:
        key = int.from_bytes(itinerary_id.bytes[:8], "big", signed=True)
        await self._session.execute(select(func.pg_advisory_xact_lock(key)))

    async def _itinerary(self, itinerary_id: UUID) -> Itinerary | None:
        return (
            await self._session.execute(
                select(Itinerary)
                .where(Itinerary.id == itinerary_id)
                .with_for_update()
            )
        ).scalar_one_or_none()

    async def _tombstone(
        self,
        itinerary_id: UUID,
    ) -> ItineraryTombstone | None:
        return (
            await self._session.execute(
                select(ItineraryTombstone)
                .where(ItineraryTombstone.itinerary_id == itinerary_id)
                .with_for_update()
            )
        ).scalar_one_or_none()


def _require_owned_or_absent(
    owner_id: UUID,
    itinerary: Itinerary | None,
    tombstone: ItineraryTombstone | None,
) -> None:
    stored_owner = (
        itinerary.user_id
        if itinerary is not None
        else tombstone.user_id if tombstone is not None else None
    )
    if stored_owner is not None and stored_owner != owner_id:
        raise ItineraryNotFoundError


def _item_rows(
    itinerary_id: UUID,
    snapshot: ItineraryReplaceRequest,
) -> list[ItineraryItem]:
    timezone = ZoneInfo(snapshot.timezone)
    return [
        ItineraryItem(
            id=item.id,
            itinerary_id=itinerary_id,
            poi_id=None,
            title=item.title,
            position=item.position,
            start_at=datetime.combine(
                snapshot.local_date,
                item.start_local_time,
                timezone,
            ),
            end_at=datetime.combine(
                snapshot.local_date,
                item.end_local_time,
                timezone,
            ),
            travel_time_minutes=None,
            notes=None,
        )
        for item in snapshot.items
    ]


def _response_from_snapshot(
    itinerary_id: UUID,
    revision: int,
    snapshot: ItineraryReplaceRequest,
) -> SavedItineraryResponse:
    return SavedItineraryResponse(
        id=itinerary_id,
        revision=revision,
        title=snapshot.title,
        city=snapshot.city,
        local_date=snapshot.local_date,
        timezone=snapshot.timezone,
        start_local_time=snapshot.start_local_time,
        end_local_time=snapshot.end_local_time,
        items=snapshot.items,
        assumptions=snapshot.assumptions,
        warnings=snapshot.warnings,
    )


def _response_from_row(row: Itinerary) -> SavedItineraryResponse:
    timezone = ZoneInfo(row.timezone)
    ordered_items = sorted(row.items, key=lambda item: (item.position, item.id))
    return SavedItineraryResponse(
        id=row.id,
        revision=row.revision,
        title=row.title,
        city=SupportedCity(row.city),
        local_date=row.local_date,
        timezone=row.timezone,
        start_local_time=row.start_local_time,
        end_local_time=row.end_local_time,
        items=tuple(
            SavedItineraryItem(
                id=item.id,
                position=item.position,
                title=item.title,
                start_local_time=_local_time(item.start_at, timezone),
                end_local_time=_local_time(item.end_at, timezone),
            )
            for item in ordered_items
        ),
        assumptions=tuple(row.assumptions),
        warnings=tuple(row.warnings),
    )


def _local_time(value: datetime | None, timezone: ZoneInfo) -> time:
    if value is None:
        raise ItineraryStoreError
    return value.astimezone(timezone).time().replace(tzinfo=None)
