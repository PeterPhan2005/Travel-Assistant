"""Strict private models used by Discovery's normalized tool registry."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictBool,
    StrictFloat,
    StrictInt,
    model_validator,
)

from app.agents.contracts import AgentFailure, SourceType
from app.providers.poi.models import (
    MAX_DISCOVERY_RESULTS,
    PoiProviderKind,
    PriceLevel,
    SupportedCity,
)

MAX_MENU_ITEMS = 200


class PrivateToolModel(BaseModel):
    """Immutable strict base with no arbitrary extension field."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        validate_default=True,
        revalidate_instances="always",
    )


class ToolCoordinates(PrivateToolModel):
    """Plain finite WGS84 destination coordinates."""

    latitude: Annotated[
        StrictFloat,
        Field(ge=-90, le=90, allow_inf_nan=False),
    ]
    longitude: Annotated[
        StrictFloat,
        Field(ge=-180, le=180, allow_inf_nan=False),
    ]


class ToolSource(PrivateToolModel):
    """Normalized source metadata accepted by deterministic evidence assembly."""

    source_id: Annotated[str, Field(strict=True, min_length=1, max_length=120)]
    source_type: SourceType
    label: Annotated[str, Field(strict=True, min_length=1, max_length=200)]
    publisher: (
        Annotated[str, Field(strict=True, min_length=1, max_length=200)] | None
    ) = None
    url: HttpUrl | None = None
    published_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime | None = None


class PoiToolCandidate(PrivateToolModel):
    """One provider-normalized candidate with no request origin or raw values."""

    id: Annotated[str, Field(strict=True, min_length=1, max_length=280)]
    provider: PoiProviderKind
    provider_id: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=255),
    ]
    canonical_name: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=200),
    ]
    city: SupportedCity
    category: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=80),
    ]
    address: (
        Annotated[str, Field(strict=True, min_length=1, max_length=500)] | None
    ) = None
    coordinates: ToolCoordinates
    distance_metres: (
        Annotated[
            StrictFloat,
            Field(ge=0, allow_inf_nan=False),
        ]
        | None
    ) = None
    rating: Annotated[Decimal, Field(ge=0, le=5)] | None = None
    rating_count: Annotated[StrictInt, Field(ge=0)] | None = None
    price_level: PriceLevel | None = None
    opening_hours_summary: (
        Annotated[str, Field(strict=True, min_length=1, max_length=500)] | None
    ) = None
    sources: Annotated[tuple[ToolSource, ...], Field(max_length=20)] = ()
    retrieved_at: AwareDatetime | None = None
    is_curated: StrictBool
    is_externally_supplied: StrictBool

    @model_validator(mode="after")
    def validate_candidate(self) -> PoiToolCandidate:
        """Close identity, flags, and local source uniqueness."""
        expected_id = f"{self.provider.value}:{self.provider_id}"
        if self.id != expected_id:
            raise ValueError("Tool candidate identity is inconsistent.")
        expected_curated = self.provider is PoiProviderKind.CURATED
        if self.is_curated is not expected_curated:
            raise ValueError("Tool candidate curated flag is inconsistent.")
        if self.is_externally_supplied is expected_curated:
            raise ValueError("Tool candidate external flag is inconsistent.")
        source_ids = tuple(source.source_id for source in self.sources)
        if source_ids != tuple(sorted(set(source_ids))):
            raise ValueError("Tool candidate sources must be unique and sorted.")
        return self


class PoiToolResult(PrivateToolModel):
    """One normalized POI operation result in provider ranking order."""

    provider: PoiProviderKind
    items: Annotated[
        tuple[PoiToolCandidate, ...],
        Field(max_length=MAX_DISCOVERY_RESULTS),
    ]
    returned_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_DISCOVERY_RESULTS),
    ]
    is_complete: StrictBool
    freshness_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_result(self) -> PoiToolResult:
        """Reject count drift, duplicates, mixed providers, and source conflict."""
        if self.returned_count != len(self.items):
            raise ValueError("POI tool count does not match items.")
        item_ids = tuple(item.id for item in self.items)
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("POI tool candidate IDs must be unique.")
        if any(item.provider is not self.provider for item in self.items):
            raise ValueError("POI tool result mixes providers.")
        expected_freshness = max(
            (
                item.retrieved_at
                for item in self.items
                if item.retrieved_at is not None
            ),
            default=None,
        )
        if self.freshness_at != expected_freshness:
            raise ValueError("POI tool freshness does not match candidates.")
        sources: dict[str, ToolSource] = {}
        for item in self.items:
            for source in item.sources:
                existing = sources.setdefault(source.source_id, source)
                if existing != source:
                    raise ValueError("POI tool source identity conflicts.")
        return self


class MenuItemResult(PrivateToolModel):
    """One source-grounded menu item for a selected curated POI."""

    menu_item_id: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=120),
    ]
    poi_provider_id: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=255),
    ]
    item_name: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=200),
    ]
    price_minor_units: Annotated[
        StrictInt,
        Field(ge=0, le=9_223_372_036_854_775_807),
    ]
    currency: Annotated[
        str,
        Field(
            strict=True,
            min_length=3,
            max_length=3,
            pattern=r"^[A-Z]{3}$",
        ),
    ]
    source_updated_at: AwareDatetime
    source: ToolSource


class MenuResultEnvelope(PrivateToolModel):
    """Deterministically ordered menu data for selected curated POIs."""

    items: Annotated[
        tuple[MenuItemResult, ...],
        Field(max_length=MAX_MENU_ITEMS),
    ] = ()

    @model_validator(mode="after")
    def validate_menu_result(self) -> MenuResultEnvelope:
        """Require unique IDs and POI/menu ordering."""
        ordered_keys = tuple(
            (item.poi_provider_id, item.menu_item_id) for item in self.items
        )
        if ordered_keys != tuple(sorted(set(ordered_keys))):
            raise ValueError("Menu items must be unique and sorted.")
        item_ids = tuple(item.menu_item_id for item in self.items)
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Menu item IDs must be globally unique.")
        return self


class PoiToolResponse(PrivateToolModel):
    """Exactly one POI tool success or sanitized failure."""

    result: PoiToolResult | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_response(self) -> PoiToolResponse:
        """Require exactly one result branch."""
        if (self.result is None) is (self.failure is None):
            raise ValueError("POI tool response must contain one outcome.")
        return self


class MenuToolResponse(PrivateToolModel):
    """Exactly one menu tool success or sanitized failure."""

    result: MenuResultEnvelope | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_response(self) -> MenuToolResponse:
        """Require exactly one result branch."""
        if (self.result is None) is (self.failure is None):
            raise ValueError("Menu tool response must contain one outcome.")
        return self


class DiscoveryRegistrySnapshot(PrivateToolModel):
    """Immutable run-local values consumed by the pure output assembler."""

    poi_result: PoiToolResult | None = None
    menu_result: MenuResultEnvelope | None = None
    failures: Annotated[tuple[AgentFailure, ...], Field(max_length=10)] = ()

    @model_validator(mode="after")
    def validate_snapshot(self) -> DiscoveryRegistrySnapshot:
        """Reject duplicate failures and menus without successful POIs."""
        failure_keys = tuple(
            (failure.code.value, failure.message) for failure in self.failures
        )
        if len(failure_keys) != len(set(failure_keys)):
            raise ValueError("Discovery failures must be unique.")
        if self.menu_result is not None and self.poi_result is None:
            raise ValueError("Menu results require successful POI results.")
        return self


def latest_timestamp(values: tuple[datetime | None, ...]) -> datetime | None:
    """Return the latest supplied timestamp without reading the current clock."""
    present = tuple(value for value in values if value is not None)
    return max(present, default=None)
