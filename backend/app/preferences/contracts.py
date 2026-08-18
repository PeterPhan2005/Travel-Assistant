"""Strict legacy and typed travel-preference document contracts."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

PREFERENCE_SCHEMA_VERSION = 1
TRAVEL_PREFERENCE_SCHEMA_VERSION = 2
MAX_DOCUMENT_BYTES = 16_384
MAX_TRAVEL_DOCUMENT_BYTES = 512
MAX_TRAVEL_INTERESTS = 5
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


class TravelInterest(StrEnum):
    """Closed, non-sensitive travel-interest taxonomy."""

    FOOD_AND_CAFES = "food_and_cafes"
    CULTURE_AND_HISTORY = "culture_and_history"
    SCENIC_AND_LANDMARKS = "scenic_and_landmarks"
    NATURE_AND_OUTDOORS = "nature_and_outdoors"
    LOCAL_LIFE_AND_MARKETS = "local_life_and_markets"
    ENTERTAINMENT_AND_NIGHTLIFE = "entertainment_and_nightlife"
    FAMILY_ACTIVITIES = "family_activities"
    WELLNESS_AND_RELAXATION = "wellness_and_relaxation"


class TravelPace(StrEnum):
    """Closed itinerary-pace taxonomy."""

    RELAXED = "relaxed"
    BALANCED = "balanced"
    ACTIVE = "active"


class BudgetPreference(StrEnum):
    """Closed qualitative travel-budget taxonomy."""

    BUDGET = "budget"
    MODERATE = "moderate"
    PREMIUM = "premium"


_INTEREST_ORDER = {item: index for index, item in enumerate(TravelInterest)}


class TravelPreferenceValuesV1(BaseModel):
    """Complete version-1 travel taxonomy values inside schema version 2."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    interests: Annotated[
        tuple[TravelInterest, ...],
        Field(max_length=MAX_TRAVEL_INTERESTS),
    ]
    pace: TravelPace | None
    budget_preference: BudgetPreference | None

    @field_validator("interests", mode="before")
    @classmethod
    def parse_interest_wire_values(cls, value: object) -> object:
        """Parse JSON arrays and exact enum strings without coercing scalars."""
        if not isinstance(value, (list, tuple)):
            return value
        return tuple(
            item
            if isinstance(item, TravelInterest)
            else TravelInterest(item)
            if isinstance(item, str)
            else item
            for item in value
        )

    @field_validator("pace", mode="before")
    @classmethod
    def parse_pace_wire_value(cls, value: object) -> object:
        if value is None or isinstance(value, TravelPace):
            return value
        return TravelPace(value) if isinstance(value, str) else value

    @field_validator("budget_preference", mode="before")
    @classmethod
    def parse_budget_wire_value(cls, value: object) -> object:
        if value is None or isinstance(value, BudgetPreference):
            return value
        return BudgetPreference(value) if isinstance(value, str) else value

    @field_validator("interests")
    @classmethod
    def normalize_interests(
        cls,
        value: tuple[TravelInterest, ...],
    ) -> tuple[TravelInterest, ...]:
        """Reject duplicates and use one stable taxonomy order."""
        if len(value) != len(set(value)):
            raise ValueError("Travel interests must be unique.")
        return tuple(sorted(value, key=_INTEREST_ORDER.__getitem__))

    @classmethod
    def empty(cls) -> "TravelPreferenceValuesV1":
        return cls(interests=(), pace=None, budget_preference=None)


class TravelPreferenceDocument(BaseModel):
    """Complete immutable typed travel-preference replacement document."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[2]
    preferences: TravelPreferenceValuesV1

    @model_validator(mode="after")
    def validate_document_size(self) -> "TravelPreferenceDocument":
        serialized = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(serialized) > MAX_TRAVEL_DOCUMENT_BYTES:
            raise ValueError("Travel preference document is too large.")
        return self

    @classmethod
    def empty(cls) -> "TravelPreferenceDocument":
        return cls(
            schema_version=2,
            preferences=TravelPreferenceValuesV1.empty(),
        )


class TravelPreferenceResponse(TravelPreferenceDocument):
    """Typed server representation with its authoritative timestamp."""

    updated_at: AwareDatetime | None


SupportedPreferenceDocument: TypeAlias = Annotated[
    PreferenceDocument | TravelPreferenceDocument,
    Field(discriminator="schema_version"),
]
SupportedPreferenceResponse: TypeAlias = Annotated[
    PreferenceResponse | TravelPreferenceResponse,
    Field(discriminator="schema_version"),
]


class AgentPreferenceProjectionV1(BaseModel):
    """Identity-free request-scoped values approved for personalization."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1] = 1
    interests: Annotated[
        tuple[TravelInterest, ...],
        Field(max_length=MAX_TRAVEL_INTERESTS),
    ] = ()
    pace: TravelPace | None = None
    budget_preference: BudgetPreference | None = None

    @model_validator(mode="after")
    def validate_interests(self) -> "AgentPreferenceProjectionV1":
        expected = tuple(sorted(set(self.interests), key=_INTEREST_ORDER.__getitem__))
        if self.interests != expected:
            raise ValueError("Projected travel interests are not canonical.")
        return self

    @property
    def is_empty(self) -> bool:
        return (
            not self.interests
            and self.pace is None
            and (self.budget_preference is None)
        )


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
        normalized.append(_normalize_value(item, depth=depth + 1, counter=counter))
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
    document: PreferenceDocument | TravelPreferenceDocument,
    updated_at: datetime | None,
) -> PreferenceResponse | TravelPreferenceResponse:
    """Build the public response without any owner identity."""
    if isinstance(document, TravelPreferenceDocument):
        return TravelPreferenceResponse(
            schema_version=document.schema_version,
            preferences=document.preferences,
            updated_at=updated_at,
        )
    return PreferenceResponse(
        schema_version=document.schema_version,
        preferences=document.preferences,
        updated_at=updated_at,
    )


def project_for_agents(
    document: PreferenceDocument | TravelPreferenceDocument,
) -> AgentPreferenceProjectionV1 | None:
    """Project only typed schema-v2 values; legacy documents are opaque."""
    if not isinstance(document, TravelPreferenceDocument):
        return None
    projection = AgentPreferenceProjectionV1(
        interests=document.preferences.interests,
        pace=document.preferences.pace,
        budget_preference=document.preferences.budget_preference,
    )
    return None if projection.is_empty else projection
