"""Strict public contracts for authenticated saved-itinerary persistence."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

from app.agents.contracts import SupportedCity


class SavedItineraryModel(BaseModel):
    """Immutable, strict, extra-forbidden saved-itinerary value."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        revalidate_instances="always",
    )


def _safe_text(value: str) -> str:
    if not value.strip():
        raise ValueError("Text must not be blank.")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError("Text must not contain control characters.")
    return value


SafeTitle = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=200),
    AfterValidator(_safe_text),
]
SafePresentationText = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=240),
    AfterValidator(_safe_text),
]

_LOCAL_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LOCAL_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}(?::00)?$")


class SavedItineraryItem(SavedItineraryModel):
    """One stable ordered item in a complete saved snapshot."""

    id: UUID
    position: Annotated[StrictInt, Field(ge=0, le=19)]
    title: SafeTitle
    start_local_time: time
    end_local_time: time

    @field_validator("id", mode="before")
    @classmethod
    def parse_id(cls, value: object) -> object:
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                return value
        return value

    @field_validator("start_local_time", "end_local_time", mode="before")
    @classmethod
    def parse_local_time(cls, value: object) -> object:
        return _parse_local_time(value)

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if (
            self.start_local_time.tzinfo is not None
            or self.end_local_time.tzinfo is not None
            or self.start_local_time.second
            or self.start_local_time.microsecond
            or self.end_local_time.second
            or self.end_local_time.microsecond
            or self.start_local_time >= self.end_local_time
        ):
            raise ValueError("Saved item interval is invalid.")
        return self


class SavedItinerarySnapshotFields(SavedItineraryModel):
    """Complete content shared by replace requests and saved responses."""

    title: SafeTitle
    city: SupportedCity
    local_date: date
    timezone: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=64),
    ]
    start_local_time: time
    end_local_time: time
    items: Annotated[
        tuple[SavedItineraryItem, ...],
        Field(min_length=1, max_length=20),
    ]
    assumptions: Annotated[
        tuple[SafePresentationText, ...],
        Field(min_length=1, max_length=10),
    ]
    warnings: Annotated[
        tuple[SafePresentationText, ...],
        Field(max_length=30),
    ] = ()

    @field_validator("items", "assumptions", "warnings", mode="before")
    @classmethod
    def parse_json_array(cls, value: object) -> object:
        """Accept JSON arrays while retaining immutable tuple values."""
        return tuple(value) if isinstance(value, list) else value

    @field_validator("city", mode="before")
    @classmethod
    def parse_city(cls, value: object) -> object:
        if isinstance(value, SupportedCity):
            return value
        if isinstance(value, str):
            try:
                return SupportedCity(value)
            except ValueError:
                return value
        return value

    @field_validator("local_date", mode="before")
    @classmethod
    def parse_local_date(cls, value: object) -> object:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, str) and _LOCAL_DATE_PATTERN.fullmatch(value):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return value
        return value

    @field_validator("start_local_time", "end_local_time", mode="before")
    @classmethod
    def parse_local_time(cls, value: object) -> object:
        return _parse_local_time(value)

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        expected_timezone = {
            SupportedCity.HCMC: "Asia/Ho_Chi_Minh",
            SupportedCity.BANGKOK: "Asia/Bangkok",
        }[self.city]
        if self.timezone != expected_timezone:
            raise ValueError("Timezone does not match the selected city.")
        if (
            self.start_local_time.tzinfo is not None
            or self.end_local_time.tzinfo is not None
            or self.start_local_time.second
            or self.start_local_time.microsecond
            or self.end_local_time.second
            or self.end_local_time.microsecond
            or self.start_local_time >= self.end_local_time
        ):
            raise ValueError("Saved itinerary window is invalid.")
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Saved itinerary item IDs must be unique.")
        previous_end = self.start_local_time
        for expected_position, item in enumerate(self.items):
            if (
                item.position != expected_position
                or item.start_local_time < self.start_local_time
                or item.end_local_time > self.end_local_time
                or item.start_local_time < previous_end
            ):
                raise ValueError("Saved itinerary item order is invalid.")
            previous_end = item.end_local_time
        return self


class ItineraryReplaceRequest(SavedItinerarySnapshotFields):
    """One complete optimistic-concurrency snapshot replacement."""

    base_revision: Annotated[StrictInt, Field(ge=0)]


class SavedItineraryResponse(SavedItinerarySnapshotFields):
    """Canonical saved itinerary with server-owned revision."""

    id: UUID
    revision: Annotated[StrictInt, Field(ge=1)]


class SavedItineraryListResponse(SavedItineraryModel):
    """Deterministically ordered current-owner saved itineraries."""

    itineraries: tuple[SavedItineraryResponse, ...]


class ItineraryDeleteRequest(SavedItineraryModel):
    """Revision checked delete command with no identity or content."""

    base_revision: Annotated[StrictInt, Field(ge=0)]


class ItineraryDeleteResponse(SavedItineraryModel):
    """Durable tombstone acknowledgement."""

    id: UUID
    revision: Annotated[StrictInt, Field(ge=1)]
    deleted: bool = True

    @model_validator(mode="after")
    def require_deleted(self) -> Self:
        if not self.deleted:
            raise ValueError("Delete acknowledgement must be deleted.")
        return self


def _parse_local_time(value: object) -> object:
    if isinstance(value, time):
        return value
    if isinstance(value, str) and _LOCAL_TIME_PATTERN.fullmatch(value):
        try:
            return time.fromisoformat(value)
        except ValueError:
            return value
    return value
