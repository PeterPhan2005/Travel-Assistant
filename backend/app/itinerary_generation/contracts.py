"""Strict transport-neutral structured itinerary generation contracts."""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime, time
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    field_validator,
    model_validator,
)

from app.agents.contracts import LocaleCode, SupportedCity
from app.agents.contracts.common import PlainShortText


class ItineraryGenerationModel(BaseModel):
    """Immutable strict model shared by the application and HTTP boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        revalidate_instances="always",
    )


def _validate_notes(value: str) -> str:
    if not value.strip():
        raise ValueError("Notes must not be blank.")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError("Notes must not contain control characters.")
    return value


ItineraryNotes = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=500),
    AfterValidator(_validate_notes),
]

_LOCAL_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LOCAL_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


class ItineraryDraftGenerationRequest(ItineraryGenerationModel):
    """Validated structured form input with no transcript or internal context."""

    city: SupportedCity
    local_date: date
    timezone: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=64),
    ]
    start_local_time: time
    end_local_time: time
    maximum_stops: Annotated[StrictInt, Field(ge=1, le=20)]
    notes: ItineraryNotes | None = None
    locale: LocaleCode
    client_mode: Literal["online"]
    latitude: Annotated[
        StrictFloat,
        Field(ge=-90, le=90, allow_inf_nan=False),
    ] | None = None
    longitude: Annotated[
        StrictFloat,
        Field(ge=-180, le=180, allow_inf_nan=False),
    ] | None = None

    @field_validator("city", mode="before")
    @classmethod
    def parse_city(cls, value: object) -> object:
        """Accept only exact existing city vocabulary strings."""
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
        """Accept only canonical ISO calendar dates without coercion."""
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
        """Accept only canonical minute-aligned HH:mm strings."""
        if isinstance(value, time):
            return value
        if isinstance(value, str) and _LOCAL_TIME_PATTERN.fullmatch(value):
            try:
                return time.fromisoformat(value)
            except ValueError:
                return value
        return value

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        """Enforce the closed city/window/mode and coordinate contract."""
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
        ):
            raise ValueError("Local times must be naive and minute-aligned.")
        if self.start_local_time >= self.end_local_time:
            raise ValueError("Itinerary start must be before end.")
        if (self.latitude is None) is not (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must be supplied together."
            )
        if self.latitude is not None and self.longitude is not None:
            if not math.isfinite(self.latitude) or not math.isfinite(
                self.longitude
            ):
                raise ValueError("Coordinates must be finite.")
        return self


class ItineraryDraftGenerationStatus(StrEnum):
    """Closed public generation result status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ItineraryDraftFailureCategory(StrEnum):
    """Stable public failure categories without internal implementation detail."""

    INSUFFICIENT_CANDIDATES = "insufficient_candidates"
    CANDIDATE_RESOLUTION_UNAVAILABLE = "candidate_resolution_unavailable"
    GENERATION_UNAVAILABLE = "generation_unavailable"
    INVALID_GENERATION_OUTPUT = "invalid_generation_output"


class ItineraryDraftItemResponse(ItineraryGenerationModel):
    """One safe public timeline item without internal identity."""

    start_local_time: time
    end_local_time: time
    title: PlainShortText

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if (
            self.start_local_time.tzinfo is not None
            or self.end_local_time.tzinfo is not None
            or self.start_local_time >= self.end_local_time
        ):
            raise ValueError("Draft item interval is invalid.")
        return self


class ItineraryDraftGenerationResponse(ItineraryGenerationModel):
    """Safe closed generation result suitable for Android transport."""

    status: ItineraryDraftGenerationStatus
    city: SupportedCity
    local_date: date
    timezone: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=64),
    ]
    start_local_time: time
    end_local_time: time
    items: Annotated[
        tuple[ItineraryDraftItemResponse, ...],
        Field(max_length=20),
    ] = ()
    assumptions: Annotated[
        tuple[PlainShortText, ...],
        Field(max_length=10),
    ] = ()
    warnings: Annotated[
        tuple[PlainShortText, ...],
        Field(max_length=30),
    ] = ()
    failure_category: ItineraryDraftFailureCategory | None = None
    retryable: bool

    @model_validator(mode="after")
    def validate_result_shape(self) -> Self:
        if self.start_local_time >= self.end_local_time:
            raise ValueError("Response window is invalid.")
        if self.status is ItineraryDraftGenerationStatus.FAILED:
            if (
                self.items
                or self.assumptions
                or self.failure_category is None
            ):
                raise ValueError("Failed response shape is invalid.")
            return self
        if not self.items or not self.assumptions:
            raise ValueError("Usable response requires a nonempty draft.")
        if self.failure_category is not None:
            raise ValueError("Usable response cannot contain a failure category.")
        if self.status is ItineraryDraftGenerationStatus.SUCCESS:
            if self.warnings or self.retryable:
                raise ValueError("Successful response cannot contain warnings.")
        elif not self.warnings:
            raise ValueError("Partial response requires a safe warning.")
        return self

    def validate_against(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> Self:
        """Fail closed unless the public result matches the exact form window."""
        if (
            self.city is not request.city
            or self.local_date != request.local_date
            or self.timezone != request.timezone
            or self.start_local_time != request.start_local_time
            or self.end_local_time != request.end_local_time
            or len(self.items) > request.maximum_stops
        ):
            raise ValueError("Generation result differs from the request.")
        previous_end = request.start_local_time
        for item in self.items:
            if (
                item.start_local_time < request.start_local_time
                or item.end_local_time > request.end_local_time
                or item.start_local_time < previous_end
            ):
                raise ValueError("Generation result timeline is invalid.")
            previous_end = item.end_local_time
        return self
