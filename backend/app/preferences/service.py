"""Deterministic preference application service."""

from __future__ import annotations

from pydantic import ValidationError

from app.preferences.contracts import (
    PreferenceDocument,
    PreferenceResponse,
    response_from_document,
)
from app.preferences.store import PreferenceStore, PreferenceStoreError


class InvalidStoredPreferenceError(PreferenceStoreError):
    """Stored data does not satisfy the supported public contract."""


class PreferenceService:
    """Coordinate validation and persistence without exposing identity."""

    def __init__(self, store: PreferenceStore) -> None:
        self._store = store

    async def get(self, firebase_uid: str) -> PreferenceResponse:
        stored = await self._store.get(firebase_uid)
        if stored is None:
            return response_from_document(PreferenceDocument.empty(), None)
        document = _stored_document(stored.schema_version, stored.preferences)
        return response_from_document(document, stored.updated_at)

    async def replace(
        self,
        firebase_uid: str,
        document: PreferenceDocument,
    ) -> PreferenceResponse:
        stored = await self._store.replace(firebase_uid, document)
        normalized = _stored_document(
            stored.schema_version,
            stored.preferences,
        )
        return response_from_document(normalized, stored.updated_at)


def _stored_document(
    schema_version: int,
    preferences: dict[str, object],
) -> PreferenceDocument:
    try:
        return PreferenceDocument.model_validate(
            {
                "schema_version": schema_version,
                "preferences": preferences,
            }
        )
    except ValidationError as error:
        raise InvalidStoredPreferenceError from error

