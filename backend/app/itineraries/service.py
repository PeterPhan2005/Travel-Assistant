"""Deterministic owner-scoped saved-itinerary application service."""

from uuid import UUID

from app.itineraries.contracts import (
    ItineraryDeleteResponse,
    ItineraryReplaceRequest,
    SavedItineraryListResponse,
    SavedItineraryResponse,
)
from app.itineraries.store import ItineraryNotFoundError, ItineraryStore


class SavedItineraryService:
    """Coordinate complete-snapshot CRUD without accepting owner identity."""

    def __init__(self, store: ItineraryStore) -> None:
        self._store = store

    async def list(self, firebase_uid: str) -> SavedItineraryListResponse:
        return SavedItineraryListResponse(
            itineraries=await self._store.list(firebase_uid)
        )

    async def get(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
    ) -> SavedItineraryResponse:
        itinerary = await self._store.get(firebase_uid, itinerary_id)
        if itinerary is None:
            raise ItineraryNotFoundError
        return itinerary

    async def replace(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
        snapshot: ItineraryReplaceRequest,
    ) -> SavedItineraryResponse:
        return await self._store.replace(firebase_uid, itinerary_id, snapshot)

    async def delete(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
        base_revision: int,
    ) -> ItineraryDeleteResponse:
        return await self._store.delete(
            firebase_uid,
            itinerary_id,
            base_revision,
        )
