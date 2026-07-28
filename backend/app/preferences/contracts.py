"""Strict, taxonomy-neutral preference document contracts."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    field_validator,
)

PREFERENCE_SCHEMA_VERSION = 1
MAX_DOCUMENT_BYTES = 16_384
MAX_CONTAINER_DEPTH = 6
MAX_KEY_LENGTH = 64
MAX_STRING_LENGTH = 512
MAX_ARRAY_ITEMS = 50
MAX_OBJECT_ITEMS = 50
MAX_TOTAL_VALUES = 500
MAX_INTEGER_ABSOLUTE_VALUE = 1_000_000_000_000


class PreferenceDocument(BaseModel):
    """Complete immutable version-1 preference replacement document."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    preferences: dict[str, object]

    @field_validator("preferences")
    @classmethod
    def validate_preferences(
        cls,
        value: dict[str, object],
    ) -> dict[str, object]:
        """Validate and deterministically normalize the generic JSON object."""
        counter = _ValueCounter()
        normalized = _normalize_object(value, depth=0, counter=counter)
        serialized = json.dumps(
            {
                "schema_version": PREFERENCE_SCHEMA_VERSION,
                "preferences": normalized,
            },
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(serialized) > MAX_DOCUMENT_BYTES:
            raise ValueError("Preference document is too large.")
        return normalized

    @classmethod
    def empty(cls) -> "PreferenceDocument":
        """Return the canonical read-only missing-row representation."""
        return cls(schema_version=1, preferences={})


class PreferenceResponse(PreferenceDocument):
    """Server representation with its authoritative update timestamp."""

    updated_at: AwareDatetime | None


class _ValueCounter:
    def __init__(self) -> None:
        self.value = 0

    def add(self) -> None:
        self.value += 1
        if self.value > MAX_TOTAL_VALUES:
            raise ValueError("Preference document has too many values.")


def _normalize_object(
    value: dict[str, object],
    *,
    depth: int,
    counter: _ValueCounter,
) -> dict[str, object]:
    _validate_depth(depth)
    if len(value) > MAX_OBJECT_ITEMS:
        raise ValueError("Preference object has too many entries.")

    normalized: dict[str, object] = {}
    for key in sorted(value):
        if not isinstance(key, str):
            raise ValueError("Preference object keys must be strings.")
        if not key or len(key) > MAX_KEY_LENGTH:
            raise ValueError("Preference object key length is invalid.")
        counter.add()
        normalized[key] = _normalize_value(
            value[key],
            depth=depth + 1,
            counter=counter,
        )
    return normalized


def _normalize_array(
    value: list[object],
    *,
    depth: int,
    counter: _ValueCounter,
) -> list[object]:
    _validate_depth(depth)
    if len(value) > MAX_ARRAY_ITEMS:
        raise ValueError("Preference array has too many items.")
    normalized: list[object] = []
    for item in value:
        counter.add()
        normalized.append(
            _normalize_value(item, depth=depth + 1, counter=counter)
        )
    return normalized


def _normalize_value(
    value: object,
    *,
    depth: int,
    counter: _ValueCounter,
) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > MAX_INTEGER_ABSOLUTE_VALUE:
            raise ValueError("Preference integer is outside the allowed range.")
        return value
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise ValueError("Preference string is too long.")
        return value
    if isinstance(value, dict):
        return _normalize_object(value, depth=depth, counter=counter)
    if isinstance(value, list):
        return _normalize_array(value, depth=depth, counter=counter)
    raise ValueError("Preference value is not an allowed JSON value.")


def _validate_depth(depth: int) -> None:
    if depth > MAX_CONTAINER_DEPTH:
        raise ValueError("Preference document is nested too deeply.")


def response_from_document(
    document: PreferenceDocument,
    updated_at: datetime | None,
) -> PreferenceResponse:
    """Build the public response without any owner identity."""
    return PreferenceResponse(
        schema_version=document.schema_version,
        preferences=document.preferences,
        updated_at=updated_at,
    )
