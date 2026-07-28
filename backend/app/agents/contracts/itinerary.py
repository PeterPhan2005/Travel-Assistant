"""Strict one-day draft Itinerary Agent contracts."""

from __future__ import annotations

from datetime import date, time
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, model_validator

from app.agents.contracts.common import (
    AgentKind,
    AgentWarning,
    ClaimId,
    ContractModel,
    EvidenceBundle,
    ItineraryItemId,
    PlainShortText,
    PoiId,
    ShortText,
    SourceId,
    SupportedCity,
    validate_issue_stage,
    validate_references,
    validate_sorted_unique,
)
from app.agents.contracts.discovery import DiscoveryCandidate, DiscoveryOrigin


def _validate_local_time(value: time) -> None:
    if value.tzinfo is not None:
        raise ValueError(
            "Local time must be naive because timezone is explicit."
        )


def _validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Timezone identifier is not recognized.") from error


class ItineraryConstraints(ContractModel):
    """Explicit bounded user constraints without a preference taxonomy."""

    maximum_stops: Annotated[int, Field(strict=True, gt=0, le=20)]
    required_poi_ids: Annotated[
        tuple[PoiId, ...],
        Field(max_length=20),
    ] = ()
    excluded_poi_ids: Annotated[
        tuple[PoiId, ...],
        Field(max_length=20),
    ] = ()
    preferred_categories: Annotated[
        tuple[ShortText, ...],
        Field(max_length=10),
    ] = ()
    notes: Annotated[
        tuple[ShortText, ...],
        Field(max_length=10),
    ] = ()

    @model_validator(mode="after")
    def validate_constraints(self) -> ItineraryConstraints:
        """Reject duplicate, unstable, or contradictory constraints."""
        validate_sorted_unique(
            self.required_poi_ids,
            label="Required POI IDs",
        )
        validate_sorted_unique(
            self.excluded_poi_ids,
            label="Excluded POI IDs",
        )
        if set(self.required_poi_ids) & set(self.excluded_poi_ids):
            raise ValueError("Required and excluded POI IDs must be disjoint.")
        if self.preferred_categories != tuple(
            sorted(set(self.preferred_categories))
        ):
            raise ValueError(
                "Preferred categories must be unique and sorted."
            )
        if self.notes != tuple(sorted(set(self.notes))):
            raise ValueError("Constraint notes must be unique and sorted.")
        return self


class ItineraryRequest(ContractModel):
    """One-day local-time planning input over normalized candidate POIs."""

    city: SupportedCity
    local_date: date
    timezone: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=64),
    ]
    start_local_time: time
    end_local_time: time
    candidates: Annotated[
        tuple[DiscoveryCandidate, ...],
        Field(min_length=1, max_length=20),
    ]
    evidence: EvidenceBundle
    constraints: ItineraryConstraints
    start_origin: DiscoveryOrigin | None = None

    @model_validator(mode="after")
    def validate_request_window(self) -> ItineraryRequest:
        """Validate explicit local time semantics and candidate closure."""
        _validate_timezone(self.timezone)
        _validate_local_time(self.start_local_time)
        _validate_local_time(self.end_local_time)
        if self.start_local_time >= self.end_local_time:
            raise ValueError("Itinerary start must be before end.")
        candidate_ids = tuple(candidate.id for candidate in self.candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Candidate POI IDs must be unique.")
        if any(candidate.city is not self.city for candidate in self.candidates):
            raise ValueError("Candidate city does not match itinerary city.")
        known_candidates = set(candidate_ids)
        constrained_ids = set(self.constraints.required_poi_ids) | set(
            self.constraints.excluded_poi_ids
        )
        if not constrained_ids.issubset(known_candidates):
            raise ValueError("Constraint references an unknown candidate POI.")
        if len(self.constraints.required_poi_ids) > (
            self.constraints.maximum_stops
        ):
            raise ValueError("Required stops exceed the maximum stop count.")
        return self


class ItineraryItem(ContractModel):
    """One ordered, non-overlapping draft stop referencing a candidate POI."""

    item_id: ItineraryItemId
    poi_id: PoiId
    title: PlainShortText
    start_local_time: time
    end_local_time: time
    supporting_claim_ids: Annotated[
        tuple[ClaimId, ...],
        Field(max_length=50),
    ] = ()
    supporting_source_ids: Annotated[
        tuple[SourceId, ...],
        Field(max_length=50),
    ] = ()

    @model_validator(mode="after")
    def validate_item(self) -> ItineraryItem:
        """Require a positive local-time interval and paired evidence refs."""
        _validate_local_time(self.start_local_time)
        _validate_local_time(self.end_local_time)
        if self.start_local_time >= self.end_local_time:
            raise ValueError("Itinerary item start must be before end.")
        if bool(self.supporting_claim_ids) is not bool(
            self.supporting_source_ids
        ):
            raise ValueError(
                "Itinerary item claim/source references must be paired."
            )
        validate_sorted_unique(
            self.supporting_claim_ids,
            label="Item claim IDs",
        )
        validate_sorted_unique(
            self.supporting_source_ids,
            label="Item source IDs",
        )
        return self


class ItineraryOutput(ContractModel):
    """Ordered local-time itinerary that is always explicitly draft-only."""

    local_date: date
    timezone: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=64),
    ]
    start_local_time: time
    end_local_time: time
    items: Annotated[
        tuple[ItineraryItem, ...],
        Field(min_length=1, max_length=20),
    ]
    assumptions: Annotated[
        tuple[PlainShortText, ...],
        Field(min_length=1, max_length=10),
    ]
    warnings: Annotated[
        tuple[AgentWarning, ...],
        Field(max_length=10),
    ] = ()
    draft_only: Literal[True]

    @model_validator(mode="after")
    def validate_schedule(self) -> ItineraryOutput:
        """Reject ambiguous timezones, unstable order, and overlapping stops."""
        _validate_timezone(self.timezone)
        _validate_local_time(self.start_local_time)
        _validate_local_time(self.end_local_time)
        if self.start_local_time >= self.end_local_time:
            raise ValueError("Itinerary start must be before end.")
        item_ids = tuple(item.item_id for item in self.items)
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Itinerary item IDs must be unique.")
        expected_items = tuple(
            sorted(
                self.items,
                key=lambda item: (item.start_local_time, item.item_id),
            )
        )
        if self.items != expected_items:
            raise ValueError("Itinerary items must use chronological order.")
        previous_end = self.start_local_time
        for item in self.items:
            if item.start_local_time < previous_end:
                raise ValueError("Itinerary items must not overlap.")
            if (
                item.start_local_time < self.start_local_time
                or item.end_local_time > self.end_local_time
            ):
                raise ValueError("Itinerary item is outside the day window.")
            previous_end = item.end_local_time
        if len(self.assumptions) != len(set(self.assumptions)):
            raise ValueError("Itinerary assumptions must not be duplicated.")
        for warning in self.warnings:
            validate_issue_stage(warning, AgentKind.ITINERARY)
        return self

    def validate_against(self, request: ItineraryRequest) -> Self:
        """Close schedule identity and evidence over the exact request."""
        if (
            self.local_date != request.local_date
            or self.timezone != request.timezone
            or self.start_local_time != request.start_local_time
            or self.end_local_time != request.end_local_time
        ):
            raise ValueError("Itinerary output window differs from request.")
        known_candidates = {candidate.id for candidate in request.candidates}
        output_pois = {item.poi_id for item in self.items}
        if not output_pois.issubset(known_candidates):
            raise ValueError("Itinerary references an unknown candidate POI.")
        if len(self.items) > request.constraints.maximum_stops:
            raise ValueError("Itinerary exceeds the maximum stop count.")
        if not set(request.constraints.required_poi_ids).issubset(output_pois):
            raise ValueError("Itinerary omits a required POI.")
        if set(request.constraints.excluded_poi_ids) & output_pois:
            raise ValueError("Itinerary includes an excluded POI.")
        for item in self.items:
            if item.supporting_claim_ids:
                validate_references(
                    used_claim_ids=item.supporting_claim_ids,
                    used_source_ids=item.supporting_source_ids,
                    evidence=request.evidence,
                )
        return self
