"""Immutable provider-neutral POI request and result models."""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictFloat,
    StrictInt,
    field_validator,
    model_validator,
)

MAX_DISCOVERY_RADIUS_METRES = 50_000
MAX_DISCOVERY_RESULTS = 20
MAX_PROVIDER_TIMEOUT_SECONDS = 60.0

BoundedText = Annotated[str, Field(min_length=1, max_length=200)]
ProviderOwnedId = Annotated[str, Field(min_length=1, max_length=255)]


class FrozenProviderModel(BaseModel):
    """Strict immutable base for every public provider model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class PoiProviderKind(StrEnum):
    """Stable provider namespaces accepted by the initial boundary."""

    CURATED = "curated"
    GOOGLE_PLACES = "google_places"


class SupportedCity(StrEnum):
    """Current normalized discovery city identifiers."""

    HCMC = "hcmc"
    BANGKOK = "bkk"


class PriceLevel(StrEnum):
    """Provider-neutral qualitative price representation."""

    FREE = "free"
    INEXPENSIVE = "inexpensive"
    MODERATE = "moderate"
    EXPENSIVE = "expensive"
    VERY_EXPENSIVE = "very_expensive"


class Coordinates(FrozenProviderModel):
    """Plain WGS84 coordinates with no spatial ORM dependency."""

    latitude: Annotated[
        StrictFloat,
        Field(ge=-90, le=90, allow_inf_nan=False),
    ]
    longitude: Annotated[
        StrictFloat,
        Field(ge=-180, le=180, allow_inf_nan=False),
    ]

    @model_validator(mode="after")
    def reject_non_finite_values(self) -> Coordinates:
        """Defend explicitly against non-finite input."""
        if not math.isfinite(self.latitude) or not math.isfinite(self.longitude):
            raise ValueError("Coordinates must be finite.")
        return self


def _normalize_optional_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = " ".join(value.split())
    return normalized or None


def _normalize_optional_category(value: object) -> object:
    normalized = _normalize_optional_text(value)
    return normalized.casefold() if isinstance(normalized, str) else normalized


class PoiDiscoveryRequest(FrozenProviderModel):
    """Focused nearby-discovery input independent of HTTP transport."""

    query: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    category: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    city: SupportedCity
    origin: Coordinates
    radius_metres: Annotated[
        StrictInt,
        Field(gt=0, le=MAX_DISCOVERY_RADIUS_METRES),
    ]
    limit: Annotated[
        StrictInt,
        Field(gt=0, le=MAX_DISCOVERY_RESULTS),
    ]

    _normalize_query = field_validator("query", mode="before")(_normalize_optional_text)
    _normalize_category = field_validator("category", mode="before")(
        _normalize_optional_category
    )


class ProviderTimeoutPolicy(FrozenProviderModel):
    """Injected operation deadline for one provider adapter."""

    seconds: Annotated[
        StrictFloat,
        Field(gt=0, le=MAX_PROVIDER_TIMEOUT_SECONDS, allow_inf_nan=False),
    ] = 5.0


class SourceReference(FrozenProviderModel):
    """Safe typed provenance without source bodies or ORM rows."""

    source_id: Annotated[str, Field(min_length=1, max_length=120)]
    source_type: Annotated[str, Field(min_length=1, max_length=50)]
    label: BoundedText
    publisher: BoundedText | None = None
    url: HttpUrl | None = None
    published_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime | None = None


def build_normalized_poi_id(
    provider: PoiProviderKind,
    provider_id: str,
) -> str:
    """Namespace a provider-owned identifier without lossy rewriting."""
    return f"{provider.value}:{provider_id}"


class PoiDiscoveryResult(FrozenProviderModel):
    """Normalized POI fields accepted across present and future providers."""

    id: Annotated[str, Field(min_length=1, max_length=280)]
    provider: PoiProviderKind
    provider_id: ProviderOwnedId
    canonical_name: BoundedText
    city: SupportedCity
    category: Annotated[str, Field(min_length=1, max_length=80)]
    address: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    coordinates: Coordinates
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
        Annotated[str, Field(min_length=1, max_length=500)] | None
    ) = None
    sources: tuple[SourceReference, ...] = ()
    retrieved_at: AwareDatetime | None = None
    is_curated: bool
    is_externally_supplied: bool

    @model_validator(mode="after")
    def validate_identity_and_origin(self) -> PoiDiscoveryResult:
        """Keep normalized identity and provenance flags consistent."""
        expected_id = build_normalized_poi_id(
            self.provider,
            self.provider_id,
        )
        if self.id != expected_id:
            raise ValueError("Normalized POI identifier is inconsistent.")
        expected_curated = self.provider is PoiProviderKind.CURATED
        if self.is_curated is not expected_curated:
            raise ValueError("Curated provider flag is inconsistent.")
        if self.is_externally_supplied is expected_curated:
            raise ValueError("External provider flag is inconsistent.")
        source_ids = tuple(source.source_id for source in self.sources)
        if source_ids != tuple(sorted(set(source_ids))):
            raise ValueError("Sources must be unique and sorted by source ID.")
        return self


class PoiResultEnvelope(FrozenProviderModel):
    """Safe bounded execution result for one provider."""

    provider: PoiProviderKind
    items: tuple[PoiDiscoveryResult, ...]
    returned_count: Annotated[StrictInt, Field(ge=0, le=MAX_DISCOVERY_RESULTS)]
    is_complete: bool
    freshness_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_envelope(self) -> PoiResultEnvelope:
        """Prevent count drift and mixed-provider results."""
        if self.returned_count != len(self.items):
            raise ValueError("Returned count does not match items.")
        if any(item.provider is not self.provider for item in self.items):
            raise ValueError("Envelope contains a different provider.")
        expected_freshness = max(
            (item.retrieved_at for item in self.items if item.retrieved_at is not None),
            default=None,
        )
        if self.freshness_at != expected_freshness:
            raise ValueError("Envelope freshness does not match its items.")
        return self


def latest_timestamp(values: tuple[datetime | None, ...]) -> datetime | None:
    """Return the latest available timezone-aware timestamp."""
    available = tuple(value for value in values if value is not None)
    return max(available, default=None)
