"""Offline deterministic YAML/JSON loading with actionable errors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import ValidationError

from app.data_pipeline.errors import ValidationIssue
from app.data_pipeline.models import CuratedPackageV1
from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from app.data_pipeline.validation import validate_package_semantics


@dataclass(frozen=True)
class LoadedPackage:
    """A fully validated package paired with its authoring file."""

    source_path: Path
    package: CuratedPackageV1


@dataclass(frozen=True)
class PackageValidationResult:
    """All accepted packages and all independent validation issues."""

    packages: tuple[LoadedPackage, ...]
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues


def _json_path(location: tuple[int | str, ...]) -> str:
    path = "$"
    for part in location:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _record_context(
    raw: object,
    location: tuple[int | str, ...],
) -> tuple[str, str | None]:
    entity_names = {
        "package": "package",
        "sources": "source",
        "pois": "poi",
        "menu_items": "menu_item",
        "narrations": "narration",
    }
    if not location or not isinstance(location[0], str):
        return ("package", None)
    container = location[0]
    entity = entity_names.get(container, "package")
    if container == "package":
        if isinstance(raw, dict):
            package = raw.get("package")
            if isinstance(package, dict):
                value = package.get("package_id")
                return (entity, value if isinstance(value, str) else None)
        return (entity, None)
    if (
        len(location) > 1
        and isinstance(location[1], int)
        and isinstance(raw, dict)
    ):
        records = raw.get(container)
        if (
            isinstance(records, list)
            and 0 <= location[1] < len(records)
            and isinstance(records[location[1]], dict)
        ):
            value = records[location[1]].get("id")
            return (entity, value if isinstance(value, str) else None)
    return (entity, None)


def _error_code(
    error_type: str,
    location: tuple[int | str, ...],
) -> str:
    field = str(location[-1]) if location else ""
    if error_type == "extra_forbidden":
        return "unknown_field"
    if error_type == "missing":
        return "missing_field"
    if location == ("schema_version",):
        return "unsupported_schema_version"
    if "datetime" in error_type or field.endswith("_at"):
        return "invalid_timestamp"
    if "url" in error_type:
        return "invalid_url"
    if field == "price_minor_units" and error_type in {
        "int_type",
        "int_parsing",
    }:
        return "price_not_integer"
    if field == "price_minor_units":
        return "invalid_price"
    if field == "currency_code":
        return "invalid_currency"
    if field in {"latitude", "longitude"}:
        return "invalid_coordinate"
    if field in {"id", "package_id", "poi_id", "source_id"}:
        return "invalid_id"
    if error_type == "enum":
        return "invalid_enum"
    return "invalid_value"


def _validation_issues(
    path: Path,
    raw: object,
    error: ValidationError,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for detail in error.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    ):
        location = detail["loc"]
        entity, record_id = _record_context(raw, location)
        issues.append(
            ValidationIssue(
                source_path=path,
                code=_error_code(detail["type"], location),
                entity_type=entity,
                record_id=record_id,
                field_path=_json_path(location),
                message=detail["msg"],
            )
        )
    return tuple(sorted(issues, key=ValidationIssue.sort_key))


def _parse_document(path: Path) -> tuple[object | None, ValidationIssue | None]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return (
            None,
            ValidationIssue(
                source_path=path,
                code="source_unavailable",
                entity_type="package",
                record_id=None,
                field_path="$",
                message="Curated package file could not be read.",
            ),
        )

    try:
        if path.suffix.lower() == ".json":
            return (json.loads(source), None)
        if path.suffix.lower() in {".yaml", ".yml"}:
            return (yaml.safe_load(source), None)
        return (
            None,
            ValidationIssue(
                source_path=path,
                code="unsupported_format",
                entity_type="package",
                record_id=None,
                field_path="$",
                message="Only .yaml, .yml, and .json packages are supported.",
            ),
        )
    except json.JSONDecodeError as error:
        message = (
            f"Could not parse JSON at line {error.lineno}, "
            f"column {error.colno}."
        )
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        message = (
            "Could not parse YAML."
            if mark is None
            else (
                f"Could not parse YAML at line {mark.line + 1}, "
                f"column {mark.column + 1}."
            )
        )
    return (
        None,
        ValidationIssue(
            source_path=path,
            code="malformed_document",
            entity_type="package",
            record_id=None,
            field_path="$",
            message=message,
        ),
    )


def load_package(path: Path) -> PackageValidationResult:
    """Load and fully validate one YAML or JSON package without a database."""
    raw, parse_issue = _parse_document(path)
    if parse_issue is not None:
        return PackageValidationResult((), (parse_issue,))
    try:
        package = CuratedPackageV1.model_validate(raw)
    except ValidationError as error:
        return PackageValidationResult(
            (),
            _validation_issues(path, raw, error),
        )
    issues = validate_package_semantics(package, path)
    if issues:
        return PackageValidationResult((), issues)
    return PackageValidationResult((LoadedPackage(path, package),), ())


def _global_duplicate_issues(
    packages: tuple[LoadedPackage, ...],
) -> tuple[ValidationIssue, ...]:
    seen: dict[tuple[str, str], Path] = {}
    issues: list[ValidationIssue] = []
    groups = (
        ("source", "sources"),
        ("poi", "pois"),
        ("menu_item", "menu_items"),
        ("narration", "narrations"),
    )
    for loaded in packages:
        for entity, attribute in groups:
            records = cast(
                tuple[Any, ...],
                getattr(loaded.package, attribute),
            )
            for index, record in enumerate(records):
                key = (entity, cast(str, record.id))
                prior = seen.get(key)
                if prior is None:
                    seen[key] = loaded.source_path
                    continue
                issues.append(
                    ValidationIssue(
                        source_path=loaded.source_path,
                        code="duplicate_id_across_packages",
                        entity_type=entity,
                        record_id=cast(str, record.id),
                        field_path=f"$.{attribute}[{index}].id",
                        message=(
                            "Identifier collides with the same entity type "
                            f"in {prior.as_posix()}."
                        ),
                    )
                )
    return tuple(sorted(issues, key=ValidationIssue.sort_key))


def load_all_packages() -> PackageValidationResult:
    """Validate both required city packages and collect every failure."""
    packages: list[LoadedPackage] = []
    issues: list[ValidationIssue] = []
    for path in sorted(CITY_PACKAGE_PATHS.values()):
        result = load_package(path)
        packages.extend(result.packages)
        issues.extend(result.issues)
    loaded = tuple(packages)
    issues.extend(_global_duplicate_issues(loaded))
    return PackageValidationResult(
        packages=loaded if not issues else (),
        issues=tuple(sorted(issues, key=ValidationIssue.sort_key)),
    )
