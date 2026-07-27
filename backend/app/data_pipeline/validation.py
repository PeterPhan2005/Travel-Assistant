"""Semantic validation beyond Pydantic's structural contract."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from app.data_pipeline.errors import ValidationIssue
from app.data_pipeline.models import (
    CityCode,
    CuratedPackageV1,
    NarrationRecord,
    VerificationStatus,
)

FUTURE_CLOCK_SKEW = timedelta(minutes=5)


class IdentifiedRecord(Protocol):
    """Common identifier shape used by duplicate checks."""

    id: str


CITY_BOUNDS = {
    CityCode.HCMC: {
        "latitude": (10.3, 11.2),
        "longitude": (106.3, 107.1),
    },
    CityCode.BANGKOK: {
        "latitude": (13.4, 14.2),
        "longitude": (100.2, 100.9),
    },
}


def _issue(
    path: Path,
    code: str,
    entity: str,
    record_id: str | None,
    field: str,
    message: str,
) -> ValidationIssue:
    return ValidationIssue(
        source_path=path,
        code=code,
        entity_type=entity,
        record_id=record_id,
        field_path=field,
        message=message,
    )


def _duplicate_issues(
    path: Path,
    entity: str,
    records: tuple[IdentifiedRecord, ...],
    field_prefix: str,
) -> list[ValidationIssue]:
    counts = Counter(record.id for record in records)
    return [
        _issue(
            path,
            "duplicate_id",
            entity,
            record.id,
            f"$.{field_prefix}[{index}].id",
            f"Identifier {record.id!r} is duplicated within this entity type.",
        )
        for index, record in enumerate(records)
        if counts[record.id] > 1
    ]


def _timestamp_issues(
    package: CuratedPackageV1,
    path: Path,
    now: datetime,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    maximum = now + FUTURE_CLOCK_SKEW
    timestamps: list[
        tuple[str, str | None, str, datetime | None]
    ] = [
        (
            "package",
            package.package.package_id,
            "$.package.published_at",
            package.package.published_at,
        )
    ]
    for index, source in enumerate(package.sources):
        timestamps.extend(
            (
                (
                    "source",
                    source.id,
                    f"$.sources[{index}].published_at",
                    source.published_at,
                ),
                (
                    "source",
                    source.id,
                    f"$.sources[{index}].retrieved_at",
                    source.retrieved_at,
                ),
            )
        )
        if (
            source.published_at is not None
            and source.retrieved_at is not None
            and source.retrieved_at < source.published_at
        ):
            issues.append(
                _issue(
                    path,
                    "retrieval_precedes_publication",
                    "source",
                    source.id,
                    f"$.sources[{index}].retrieved_at",
                    "Retrieval timestamp cannot precede publication.",
                )
            )
    for index, item in enumerate(package.menu_items):
        timestamps.append(
            (
                "menu_item",
                item.id,
                f"$.menu_items[{index}].source_updated_at",
                item.source_updated_at,
            )
        )

    for entity, record_id, field, value in timestamps:
        if value is not None and value > maximum:
            issues.append(
                _issue(
                    path,
                    "timestamp_in_future",
                    entity,
                    record_id,
                    field,
                    "Timestamp exceeds the documented five-minute clock skew.",
                )
            )
    return issues


def _narration_grounding_issue(
    path: Path,
    narration: NarrationRecord,
    index: int,
) -> ValidationIssue | None:
    has_source = narration.source_id is not None
    has_fallback = narration.fallback_source_label is not None
    if has_source and not has_fallback:
        if narration.verification_status is VerificationStatus.VERIFIED:
            return None
        return _issue(
            path,
            "invalid_verification_status",
            "narration",
            narration.id,
            f"$.narrations[{index}].verification_status",
            "A sourced narration must use verification status 'verified'.",
        )
    if not has_source and has_fallback:
        if narration.verification_status is VerificationStatus.FALLBACK:
            return None
        return _issue(
            path,
            "invalid_verification_status",
            "narration",
            narration.id,
            f"$.narrations[{index}].verification_status",
            "An explicit fallback must use verification status 'fallback'.",
        )
    return _issue(
        path,
        "narration_source_required",
        "narration",
        narration.id,
        f"$.narrations[{index}]",
        "Provide exactly one source_id or fallback_source_label.",
    )


def validate_package_semantics(
    package: CuratedPackageV1,
    path: Path,
    *,
    now: datetime | None = None,
) -> tuple[ValidationIssue, ...]:
    """Collect independent reference, city, freshness, and identity errors."""
    issues: list[ValidationIssue] = []
    city = package.package.city_code
    prefix = f"{city.value}-"

    if not package.package.package_id.startswith(prefix):
        issues.append(
            _issue(
                path,
                "city_id_prefix_mismatch",
                "package",
                package.package.package_id,
                "$.package.package_id",
                f"Package identifiers for {city.value!r} must start with {prefix!r}.",
            )
        )

    entity_groups: tuple[
        tuple[str, tuple[IdentifiedRecord, ...], str],
        ...,
    ] = (
        ("source", package.sources, "sources"),
        ("poi", package.pois, "pois"),
        ("menu_item", package.menu_items, "menu_items"),
        ("narration", package.narrations, "narrations"),
    )
    for entity, records, field_prefix in entity_groups:
        issues.extend(
            _duplicate_issues(path, entity, records, field_prefix)
        )
        for index, record in enumerate(records):
            if not record.id.startswith(prefix):
                issues.append(
                    _issue(
                        path,
                        "city_id_prefix_mismatch",
                        entity,
                        record.id,
                        f"$.{field_prefix}[{index}].id",
                        f"Identifiers for {city.value!r} must start with {prefix!r}.",
                    )
                )

    sources = {source.id: source for source in package.sources}
    poi_ids = {poi.id for poi in package.pois}
    for index, source in enumerate(package.sources):
        if source.city_code is not city:
            issues.append(
                _issue(
                    path,
                    "city_mismatch",
                    "source",
                    source.id,
                    f"$.sources[{index}].city_code",
                    "Record city_code must equal the package city_code.",
                )
            )

    bounds = CITY_BOUNDS[city]
    for index, poi in enumerate(package.pois):
        if poi.city_code is not city:
            issues.append(
                _issue(
                    path,
                    "city_mismatch",
                    "poi",
                    poi.id,
                    f"$.pois[{index}].city_code",
                    "Record city_code must equal the package city_code.",
                )
            )
        latitude_range = bounds["latitude"]
        longitude_range = bounds["longitude"]
        if not (
            latitude_range[0]
            <= poi.location.latitude
            <= latitude_range[1]
        ):
            issues.append(
                _issue(
                    path,
                    "coordinate_outside_city_bounds",
                    "poi",
                    poi.id,
                    f"$.pois[{index}].location.latitude",
                    "Latitude is outside the accepted city bounds; verify coordinate order.",
                )
            )
        if not (
            longitude_range[0]
            <= poi.location.longitude
            <= longitude_range[1]
        ):
            issues.append(
                _issue(
                    path,
                    "coordinate_outside_city_bounds",
                    "poi",
                    poi.id,
                    f"$.pois[{index}].location.longitude",
                    "Longitude is outside the accepted city bounds; verify coordinate order.",
                )
            )
        if len(set(poi.source_ids)) != len(poi.source_ids):
            issues.append(
                _issue(
                    path,
                    "duplicate_reference",
                    "poi",
                    poi.id,
                    f"$.pois[{index}].source_ids",
                    "POI source references must be unique.",
                )
            )
        for source_index, source_id in enumerate(poi.source_ids):
            if source_id not in sources:
                issues.append(
                    _issue(
                        path,
                        "broken_source_reference",
                        "poi",
                        poi.id,
                        f"$.pois[{index}].source_ids[{source_index}]",
                        f"Source {source_id!r} does not exist in this package.",
                    )
                )

    for index, item in enumerate(package.menu_items):
        if item.city_code is not city:
            issues.append(
                _issue(
                    path,
                    "city_mismatch",
                    "menu_item",
                    item.id,
                    f"$.menu_items[{index}].city_code",
                    "Record city_code must equal the package city_code.",
                )
            )
        if item.poi_id not in poi_ids:
            issues.append(
                _issue(
                    path,
                    "broken_poi_reference",
                    "menu_item",
                    item.id,
                    f"$.menu_items[{index}].poi_id",
                    f"POI {item.poi_id!r} does not exist in this package.",
                )
            )
        referenced_source = sources.get(item.source_id)
        if referenced_source is None:
            issues.append(
                _issue(
                    path,
                    "broken_source_reference",
                    "menu_item",
                    item.id,
                    f"$.menu_items[{index}].source_id",
                    f"Source {item.source_id!r} does not exist in this package.",
                )
            )
        elif item.source_type is not referenced_source.source_type:
            issues.append(
                _issue(
                    path,
                    "source_type_mismatch",
                    "menu_item",
                    item.id,
                    f"$.menu_items[{index}].source_type",
                    "Menu source_type must match its referenced source.",
                )
            )

    narration_keys = Counter(
        (narration.poi_id, narration.language_code)
        for narration in package.narrations
    )
    for index, narration in enumerate(package.narrations):
        if narration.city_code is not city:
            issues.append(
                _issue(
                    path,
                    "city_mismatch",
                    "narration",
                    narration.id,
                    f"$.narrations[{index}].city_code",
                    "Record city_code must equal the package city_code.",
                )
            )
        if narration.poi_id not in poi_ids:
            issues.append(
                _issue(
                    path,
                    "broken_poi_reference",
                    "narration",
                    narration.id,
                    f"$.narrations[{index}].poi_id",
                    f"POI {narration.poi_id!r} does not exist in this package.",
                )
            )
        if (
            narration.source_id is not None
            and narration.source_id not in sources
        ):
            issues.append(
                _issue(
                    path,
                    "broken_source_reference",
                    "narration",
                    narration.id,
                    f"$.narrations[{index}].source_id",
                    f"Source {narration.source_id!r} does not exist in this package.",
                )
            )
        grounding_issue = _narration_grounding_issue(
            path, narration, index
        )
        if grounding_issue is not None:
            issues.append(grounding_issue)
        if narration_keys[
            (narration.poi_id, narration.language_code)
        ] > 1:
            issues.append(
                _issue(
                    path,
                    "duplicate_poi_language",
                    "narration",
                    narration.id,
                    f"$.narrations[{index}].language_code",
                    "Only one narration per POI and language is allowed.",
                )
            )

    resolved_now = now or datetime.now(timezone.utc)
    issues.extend(_timestamp_issues(package, path, resolved_now))
    return tuple(sorted(issues, key=ValidationIssue.sort_key))
