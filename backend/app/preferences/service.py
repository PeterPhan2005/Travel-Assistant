"""Deterministic preference application service."""

from __future__ import annotations

from pydantic import ValidationError

from app.preferences.contracts import (
    AgentPreferenceProjectionV1,
    PreferenceDocument,
    SupportedPreferenceDocument,
    SupportedPreferenceResponse,
    TravelPreferenceDocument,
    project_for_agents,
    response_from_document,
)
from app.preferences.store import PreferenceStore, PreferenceStoreError


class InvalidStoredPreferenceError(PreferenceStoreError):
    """Stored data does not satisfy the supported public contract."""


class UnsupportedStoredPreferenceVersionError(PreferenceStoreError):
    """Stored data uses a schema this release cannot safely interpret."""


class PreferenceService:
    """Coordinate validation and persistence without exposing identity."""

    def __init__(self, store: PreferenceStore) -> None:
        self._store = store

    async def get(self, firebase_uid: str) -> SupportedPreferenceResponse:
        stored = await self._store.get(firebase_uid)
        if stored is None:
            return response_from_document(PreferenceDocument.empty(), None)
        document = _stored_document(stored.schema_version, stored.preferences)
        return response_from_document(document, stored.updated_at)

    async def get_projection(
        self,
        firebase_uid: str,
    ) -> AgentPreferenceProjectionV1 | None:
        """Return only the identity-free typed agent projection."""
        stored = await self._store.get(firebase_uid)
        if stored is None:
            return None
        return project_for_agents(
            _stored_document(stored.schema_version, stored.preferences)
        )

    async def replace(
        self,
        firebase_uid: str,
        document: SupportedPreferenceDocument,
    ) -> SupportedPreferenceResponse:
        stored = await self._store.replace(firebase_uid, document)
        normalized = _stored_document(
            stored.schema_version,
            stored.preferences,
        )
        return response_from_document(normalized, stored.updated_at)


def _stored_document(
    schema_version: int,
    preferences: dict[str, object],
) -> PreferenceDocument | TravelPreferenceDocument:
    try:
        value = {
            "schema_version": schema_version,
            "preferences": preferences,
        }
        if schema_version == 1:
            return PreferenceDocument.model_validate(value)
        if schema_version == 2:
            return TravelPreferenceDocument.model_validate(value)
        raise UnsupportedStoredPreferenceVersionError
    except ValidationError as error:
        raise InvalidStoredPreferenceError from error
