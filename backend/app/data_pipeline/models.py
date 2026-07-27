"""Version 1 public contract for repository-owned curated packages."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    StrictInt,
)

SAFE_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
CONTENT_VERSION_PATTERN = r"^[0-9]+(?:\.[0-9]+){0,2}$"
CURRENCY_PATTERN = r"^[A-Z]{3}$"
LANGUAGE_PATTERN = r"^[a-z]{2,3}(?:-[A-Z]{2})?$"


def _parse_timestamp(value: object) -> object:
    if not isinstance(value, str):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value


Timestamp = Annotated[
    AwareDatetime,
    BeforeValidator(_parse_timestamp),
]
PoiId = Annotated[
    str,
    Field(min_length=1, max_length=100, pattern=SAFE_ID_PATTERN),
]
ContentId = Annotated[
    str,
    Field(min_length=1, max_length=120, pattern=SAFE_ID_PATTERN),
]
ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class CityCode(StrEnum):
    """Stable city identifiers accepted by the initial pipeline."""

    HCMC = "hcmc"
    BANGKOK = "bkk"


class SourceType(StrEnum):
    """Reviewable source classes stored in the T030 source_type column."""

    OFFICIAL_GOVERNMENT = "official_government"
    OFFICIAL_INSTITUTION = "official_institution"
    OFFICIAL_OPERATOR = "official_operator"
    OFFICIAL_TOURISM = "official_tourism"


class VerificationStatus(StrEnum):
    """Grounding status accepted for authored narrations."""

    VERIFIED = "verified"
    FALLBACK = "fallback"


class FrozenContractModel(BaseModel):
    """Immutable strict-by-shape base for every public contract model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class PackageMetadata(FrozenContractModel):
    """Package identity and publication metadata."""

    package_id: Annotated[
        str,
        Field(min_length=1, max_length=100, pattern=SAFE_ID_PATTERN),
    ]
    city_code: CityCode
    content_version: Annotated[
        str,
        Field(
            min_length=1,
            max_length=32,
            pattern=CONTENT_VERSION_PATTERN,
        ),
    ]
    published_at: Timestamp


class SourceRecord(FrozenContractModel):
    """Reusable provenance metadata without copied source bodies."""

    id: ContentId
    city_code: CityCode
    source_type: SourceType
    label: ShortText
    publisher: ShortText | None = None
    url: HttpUrl | None = None
    published_at: Timestamp | None = None
    retrieved_at: Timestamp | None = None


class Coordinates(FrozenContractModel):
    """Canonical WGS84 latitude/longitude authoring shape."""

    latitude: Annotated[
        float,
        Field(strict=True, ge=-90, le=90, allow_inf_nan=False),
    ]
    longitude: Annotated[
        float,
        Field(strict=True, ge=-180, le=180, allow_inf_nan=False),
    ]


class PoiRecord(FrozenContractModel):
    """Curated point of interest with explicit record provenance."""

    id: PoiId
    city_code: CityCode
    canonical_name: ShortText
    area: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    category: Annotated[str, Field(min_length=1, max_length=80)]
    address: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    short_description: (
        Annotated[str, Field(min_length=1, max_length=2000)] | None
    ) = None
    location: Coordinates
    source_ids: tuple[ContentId, ...] = Field(min_length=1)


class MenuItemRecord(FrozenContractModel):
    """Integer minor-unit menu price with direct source freshness."""

    id: ContentId
    city_code: CityCode
    poi_id: PoiId
    source_id: ContentId
    item_name: ShortText
    price_minor_units: Annotated[
        StrictInt,
        Field(ge=0, le=9_223_372_036_854_775_807),
    ]
    currency_code: Annotated[
        str,
        Field(min_length=3, max_length=3, pattern=CURRENCY_PATTERN),
    ]
    source_type: SourceType
    source_updated_at: Timestamp


class NarrationRecord(FrozenContractModel):
    """Grounded narration or an explicitly labelled fallback."""

    id: ContentId
    city_code: CityCode
    poi_id: PoiId
    source_id: ContentId | None = None
    language_code: Annotated[
        str,
        Field(min_length=2, max_length=16, pattern=LANGUAGE_PATTERN),
    ]
    title: ShortText | None = None
    content: Annotated[str, Field(min_length=20, max_length=4000)]
    verification_status: VerificationStatus
    fallback_source_label: ShortText | None = None


class CuratedPackageV1(FrozenContractModel):
    """Complete schema-version-1 curated package."""

    schema_version: Literal[1]
    package: PackageMetadata
    sources: tuple[SourceRecord, ...] = ()
    pois: tuple[PoiRecord, ...] = ()
    menu_items: tuple[MenuItemRecord, ...] = ()
    narrations: tuple[NarrationRecord, ...] = ()
