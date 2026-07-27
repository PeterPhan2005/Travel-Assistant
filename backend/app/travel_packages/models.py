"""Strict public contracts for downloadable travel-package artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Final, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

from app.data_pipeline.models import (
    CONTENT_VERSION_PATTERN,
    CURRENCY_PATTERN,
    LANGUAGE_PATTERN,
    SAFE_ID_PATTERN,
    CityCode,
    SourceType,
    VerificationStatus,
)

ARTIFACT_SCHEMA_VERSION: Final[Literal[1]] = 1
MANIFEST_SCHEMA_VERSION: Final[Literal[1]] = 1
JSON_MEDIA_TYPE: Final[Literal["application/json"]] = "application/json"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
SAFE_DATA_FILENAME_PATTERN = (
    r"^[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+"
    r"(?:\.[0-9]+){0,2}\.data\.json$"
)

StableId = Annotated[
    str,
    Field(min_length=1, max_length=120, pattern=SAFE_ID_PATTERN),
]
PositiveEpochMillis = Annotated[
    StrictInt,
    Field(ge=1, le=9_223_372_036_854_775_807),
]
ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class FrozenArtifactModel(BaseModel):
    """Immutable, unknown-field-forbidden artifact boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ArtifactPoiManifestV1(FrozenArtifactModel):
    """Android seed-compatible identity list for package validation."""

    format_version: Literal[1] = Field(alias="formatVersion")
    poi_ids: tuple[StableId, ...] = Field(alias="poiIds")


class ArtifactPackageMetadataV1(FrozenArtifactModel):
    """Package identity mapped directly to Room package metadata fields."""

    package_id: StableId = Field(alias="packageId")
    city: Annotated[str, Field(min_length=1, max_length=100)]
    version: Annotated[
        str,
        Field(
            min_length=1,
            max_length=32,
            pattern=CONTENT_VERSION_PATTERN,
        ),
    ]
    published_at_epoch_millis: PositiveEpochMillis = Field(
        alias="publishedAtEpochMillis"
    )
    manifest: ArtifactPoiManifestV1


class ArtifactPoiV1(FrozenArtifactModel):
    """Approved offline POI fields representable by Room version 2."""

    poi_id: StableId = Field(alias="poiId")
    name: ShortText
    city: Annotated[str, Field(min_length=1, max_length=100)]
    area: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    category: Annotated[str, Field(min_length=1, max_length=80)]
    latitude: Annotated[
        float,
        Field(strict=True, ge=-90, le=90, allow_inf_nan=False),
    ]
    longitude: Annotated[
        float,
        Field(strict=True, ge=-180, le=180, allow_inf_nan=False),
    ]
    address: Annotated[
        str,
        Field(min_length=1, max_length=500),
    ] | None = None
    short_description: Annotated[
        str,
        Field(min_length=1, max_length=2000),
    ] | None = Field(default=None, alias="shortDescription")
    status: Literal["curated"]
    updated_at_epoch_millis: PositiveEpochMillis = Field(
        alias="updatedAtEpochMillis"
    )


class ArtifactAliasV1(FrozenArtifactModel):
    """Approved alias fields, emitted only when accepted input supports them."""

    alias_id: StableId = Field(alias="aliasId")
    poi_id: StableId = Field(alias="poiId")
    alias: ShortText
    normalized_alias: ShortText = Field(alias="normalizedAlias")
    language_code: Annotated[
        str,
        Field(min_length=2, max_length=16, pattern=LANGUAGE_PATTERN),
    ] | None = Field(default=None, alias="languageCode")


class ArtifactMenuItemV1(FrozenArtifactModel):
    """Integer-money menu fields representable by Room version 2."""

    menu_item_id: StableId = Field(alias="menuItemId")
    poi_id: StableId = Field(alias="poiId")
    dish_name: ShortText = Field(alias="dishName")
    price_minor_units: Annotated[
        StrictInt,
        Field(ge=0, le=9_223_372_036_854_775_807),
    ] = Field(alias="priceMinorUnits")
    currency_code: Annotated[
        str,
        Field(min_length=3, max_length=3, pattern=CURRENCY_PATTERN),
    ] = Field(alias="currencyCode")
    source_type: SourceType = Field(alias="sourceType")
    updated_at_epoch_millis: PositiveEpochMillis = Field(
        alias="updatedAtEpochMillis"
    )


class ArtifactNarrationV1(FrozenArtifactModel):
    """Grounded narration fields representable by Room version 2."""

    narration_id: StableId = Field(alias="narrationId")
    poi_id: StableId = Field(alias="poiId")
    language_code: Annotated[
        str,
        Field(min_length=2, max_length=16, pattern=LANGUAGE_PATTERN),
    ] = Field(alias="languageCode")
    content: Annotated[str, Field(min_length=20, max_length=4000)]
    verification_status: VerificationStatus = Field(
        alias="verificationStatus"
    )
    generated_at_epoch_millis: PositiveEpochMillis = Field(
        alias="generatedAtEpochMillis"
    )
    source_label: ShortText = Field(alias="sourceLabel")


class TravelPackageArtifactV1(FrozenArtifactModel):
    """Complete schema-version-1 downloadable public data file."""

    format_version: Literal[1] = Field(alias="formatVersion")
    package_metadata: ArtifactPackageMetadataV1 = Field(
        alias="packageMetadata"
    )
    pois: tuple[ArtifactPoiV1, ...] = ()
    aliases: tuple[ArtifactAliasV1, ...] = ()
    menu_items: tuple[ArtifactMenuItemV1, ...] = Field(
        default=(),
        alias="menuItems",
    )
    narrations: tuple[ArtifactNarrationV1, ...] = ()

    @model_validator(mode="after")
    def validate_identity_and_order(self) -> TravelPackageArtifactV1:
        """Reject inconsistent references and noncanonical entity order."""
        groups = (
            ("pois", tuple(record.poi_id for record in self.pois)),
            (
                "aliases",
                tuple(record.alias_id for record in self.aliases),
            ),
            (
                "menuItems",
                tuple(record.menu_item_id for record in self.menu_items),
            ),
            (
                "narrations",
                tuple(record.narration_id for record in self.narrations),
            ),
        )
        for name, identifiers in groups:
            if identifiers != tuple(sorted(identifiers)):
                raise ValueError(f"{name} must be sorted by stable identifier")
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{name} identifiers must be unique")

        poi_ids = tuple(record.poi_id for record in self.pois)
        if self.package_metadata.manifest.poi_ids != poi_ids:
            raise ValueError("package POI manifest must equal sorted POI IDs")
        known_pois = set(poi_ids)
        child_poi_ids = (
            *(record.poi_id for record in self.aliases),
            *(record.poi_id for record in self.menu_items),
            *(record.poi_id for record in self.narrations),
        )
        if any(poi_id not in known_pois for poi_id in child_poi_ids):
            raise ValueError("child record references an unknown POI")
        if any(
            record.city != self.package_metadata.city
            for record in self.pois
        ):
            raise ValueError("POI city must equal package city")
        return self


class TravelPackageManifestV1(FrozenArtifactModel):
    """Stable public metadata for one exact downloadable data file."""

    schema_version: Literal[1] = Field(alias="schemaVersion")
    artifact_schema_version: Literal[1] = Field(
        alias="artifactSchemaVersion"
    )
    package_id: StableId = Field(alias="packageId")
    city: CityCode
    content_version: Annotated[
        str,
        Field(
            min_length=1,
            max_length=32,
            pattern=CONTENT_VERSION_PATTERN,
        ),
    ] = Field(alias="contentVersion")
    published_at: Annotated[
        str,
        Field(
            min_length=20,
            max_length=32,
            pattern=(
                r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
                r"[0-9]{2}:[0-9]{2}:[0-9]{2}"
                r"(?:\.[0-9]{1,6})?Z$"
            ),
        ),
    ] = Field(alias="publishedAt")
    data_filename: Annotated[
        str,
        Field(
            min_length=1,
            max_length=180,
            pattern=SAFE_DATA_FILENAME_PATTERN,
        ),
    ] = Field(alias="dataFilename")
    media_type: Literal["application/json"] = Field(alias="mediaType")
    byte_size: Annotated[
        StrictInt,
        Field(ge=1, le=2_147_483_647),
    ] = Field(alias="byteSize")
    sha256: Annotated[
        str,
        Field(min_length=64, max_length=64, pattern=SHA256_PATTERN),
    ]

    @field_validator("published_at")
    @classmethod
    def validate_publication_timestamp(cls, value: str) -> str:
        """Require a real canonical UTC timestamp, not only a matching shape."""
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("publishedAt must be a valid timestamp") from error
        return value


# Recursive, reviewable public allowlist. The builder never dumps authoring
# models and has no raw/payload/metadata dictionary field.
ARTIFACT_FIELD_ALLOWLIST = {
    "formatVersion": None,
    "packageMetadata": {
        "packageId": None,
        "city": None,
        "version": None,
        "publishedAtEpochMillis": None,
        "manifest": {
            "formatVersion": None,
            "poiIds": None,
        },
    },
    "pois": {
        "poiId": None,
        "name": None,
        "city": None,
        "area": None,
        "category": None,
        "latitude": None,
        "longitude": None,
        "address": None,
        "shortDescription": None,
        "status": None,
        "updatedAtEpochMillis": None,
    },
    "aliases": {
        "aliasId": None,
        "poiId": None,
        "alias": None,
        "normalizedAlias": None,
        "languageCode": None,
    },
    "menuItems": {
        "menuItemId": None,
        "poiId": None,
        "dishName": None,
        "priceMinorUnits": None,
        "currencyCode": None,
        "sourceType": None,
        "updatedAtEpochMillis": None,
    },
    "narrations": {
        "narrationId": None,
        "poiId": None,
        "languageCode": None,
        "content": None,
        "verificationStatus": None,
        "generatedAtEpochMillis": None,
        "sourceLabel": None,
    },
}
