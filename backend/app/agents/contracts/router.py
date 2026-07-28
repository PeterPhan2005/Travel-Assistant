"""Strict Router Agent request and structured-output contracts."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, StrictBool, model_validator

from app.agents.contracts.common import (
    ContractModel,
    IntentKind,
    LocaleCode,
    MediumText,
    NormalizedQuery,
    PoiId,
    ShortText,
    SpecialistKind,
    SupportedCity,
    validate_sorted_unique,
)
from app.preferences.contracts import PreferenceDocument

MAX_ROUTER_SPECIALISTS = 4
MAX_REFERENCED_POIS = 20
_SPECIALIST_ORDER = {
    SpecialistKind.DISCOVERY: 0,
    SpecialistKind.NARRATION: 1,
    SpecialistKind.LOCAL_CULTURE: 2,
    SpecialistKind.ITINERARY: 3,
}


class RouterItineraryConstraints(ContractModel):
    """Small explicit constraint selection extracted from a user query."""

    duration_minutes: Annotated[int, Field(strict=True, gt=0, le=1_440)] | None = (
        None
    )
    maximum_stops: Annotated[int, Field(strict=True, gt=0, le=20)] | None = None
    notes: Annotated[
        tuple[ShortText, ...],
        Field(max_length=10),
    ] = ()

    @model_validator(mode="after")
    def validate_notes(self) -> RouterItineraryConstraints:
        """Keep stable extracted constraints unique and sorted."""
        if self.notes != tuple(sorted(set(self.notes))):
            raise ValueError("Constraint notes must be unique and sorted.")
        return self


class RouterEntities(ContractModel):
    """Closed normalized entity selection without an arbitrary dictionary."""

    city: SupportedCity | None = None
    category: ShortText | None = None
    query_term: ShortText | None = None
    referenced_poi_ids: Annotated[
        tuple[PoiId, ...],
        Field(max_length=MAX_REFERENCED_POIS),
    ] = ()
    itinerary_constraints: RouterItineraryConstraints | None = None

    @model_validator(mode="after")
    def validate_referenced_pois(self) -> RouterEntities:
        """Reject duplicate or unstable POI identity ordering."""
        validate_sorted_unique(
            self.referenced_poi_ids,
            label="Referenced POI IDs",
        )
        return self


class RouterRequest(ContractModel):
    """Minimal Router Agent input with no identity token or tool result."""

    user_query: NormalizedQuery
    locale: LocaleCode
    city: SupportedCity | None = None
    preferences: PreferenceDocument | None = None


class RouterOutput(ContractModel):
    """Closed intent, entities, and ordered optional-specialist fan-out plan."""

    primary_intent: IntentKind
    entities: RouterEntities
    specialist_plan: Annotated[
        tuple[SpecialistKind, ...],
        Field(max_length=MAX_ROUTER_SPECIALISTS),
    ] = ()
    discovery_required: StrictBool
    clarification_reason: MediumText | None = None

    @model_validator(mode="after")
    def validate_intent_plan(self) -> RouterOutput:
        """Fail closed when the intent and specialist plan are inconsistent."""
        expected_order = tuple(
            sorted(
                set(self.specialist_plan),
                key=_SPECIALIST_ORDER.__getitem__,
            )
        )
        if self.specialist_plan != expected_order:
            raise ValueError(
                "Specialist plan must be unique and in canonical order."
            )
        includes_discovery = SpecialistKind.DISCOVERY in self.specialist_plan
        if self.discovery_required is not includes_discovery:
            raise ValueError(
                "Discovery flag must match the specialist plan."
            )

        if self.primary_intent is IntentKind.UNSUPPORTED:
            if self.specialist_plan or self.discovery_required:
                raise ValueError(
                    "Unsupported intent must not schedule specialists."
                )
            if self.clarification_reason is None:
                raise ValueError(
                    "Unsupported intent requires a safe explicit reason."
                )
        elif self.primary_intent is IntentKind.NEARBY_DISCOVERY:
            self._require(SpecialistKind.DISCOVERY)
        elif self.primary_intent is IntentKind.POI_INFORMATION:
            self._require(SpecialistKind.NARRATION)
        elif self.primary_intent is IntentKind.LOCAL_CULTURE:
            self._require(SpecialistKind.LOCAL_CULTURE)
        elif self.primary_intent is IntentKind.ITINERARY_DRAFTING:
            self._require(SpecialistKind.DISCOVERY)
            self._require(SpecialistKind.ITINERARY)
        elif self.specialist_plan:
            raise ValueError(
                "General travel help must not schedule an MVP specialist."
            )
        return self

    def _require(self, specialist: SpecialistKind) -> None:
        if specialist not in self.specialist_plan:
            raise ValueError(
                f"{self.primary_intent.value} requires {specialist.value}."
            )
