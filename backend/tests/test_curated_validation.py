"""Unit coverage for strict curated package loading and semantics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.data_pipeline.cli import main
from app.data_pipeline.errors import ValidationIssue
from app.data_pipeline.loader import load_all_packages, load_package
from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from tests.curated_fixtures import copied_document


def _write_package(
    tmp_path: Path,
    document: dict[str, Any],
    *,
    suffix: str = ".yaml",
) -> Path:
    path = tmp_path / f"package{suffix}"
    if suffix == ".json":
        path.write_text(json.dumps(document), encoding="utf-8")
    else:
        path.write_text(
            yaml.safe_dump(document, sort_keys=False),
            encoding="utf-8",
        )
    return path


def _codes(path: Path) -> list[str]:
    return [issue.code for issue in load_package(path).issues]


def test_committed_hcmc_and_bangkok_packages_are_valid() -> None:
    result = load_all_packages()

    assert result.is_valid
    assert {
        loaded.package.package.city_code.value
        for loaded in result.packages
    } == {"hcmc", "bkk"}
    assert {
        loaded.package.package.package_id
        for loaded in result.packages
    } == {"hcmc-starter-v1", "bkk-starter-v1"}


@pytest.mark.parametrize("city", ["hcmc", "bkk"])
def test_each_committed_city_package_is_valid(city: str) -> None:
    result = load_package(CITY_PACKAGE_PATHS[city])

    assert result.is_valid
    assert result.packages[0].package.package.city_code.value == city


def test_json_is_an_accepted_deterministic_format(tmp_path: Path) -> None:
    path = _write_package(
        tmp_path,
        copied_document(),
        suffix=".json",
    )

    result = load_package(path)

    assert result.is_valid
    assert result.packages[0].package.package.package_id == (
        "hcmc-test-package"
    )


def test_unsupported_schema_version_is_actionable(tmp_path: Path) -> None:
    document = copied_document()
    document["schema_version"] = 2

    issues = load_package(_write_package(tmp_path, document)).issues

    assert [issue.code for issue in issues] == [
        "unsupported_schema_version"
    ]
    assert issues[0].field_path == "$.schema_version"


def test_unknown_and_missing_fields_are_collected(tmp_path: Path) -> None:
    document = copied_document()
    document["unexpected"] = "not allowed"
    del document["package"]["content_version"]

    issues = load_package(_write_package(tmp_path, document)).issues

    assert {issue.code for issue in issues} == {
        "missing_field",
        "unknown_field",
    }
    assert {issue.field_path for issue in issues} == {
        "$.package.content_version",
        "$.unexpected",
    }


@pytest.mark.parametrize(
    ("collection", "expected_entity"),
    [
        ("sources", "source"),
        ("pois", "poi"),
        ("menu_items", "menu_item"),
        ("narrations", "narration"),
    ],
)
def test_duplicate_entity_ids_fail(
    tmp_path: Path,
    collection: str,
    expected_entity: str,
) -> None:
    document = copied_document()
    records = document[collection]
    assert isinstance(records, list)
    records.append(records[0].copy())

    issues = load_package(_write_package(tmp_path, document)).issues

    duplicates = [
        issue for issue in issues if issue.code == "duplicate_id"
    ]
    assert duplicates
    assert {issue.entity_type for issue in duplicates} == {
        expected_entity
    }


@pytest.mark.parametrize(
    ("collection", "field", "value", "code"),
    [
        ("pois", "source_ids", ["hcmc-source-missing"], "broken_source_reference"),
        ("menu_items", "poi_id", "hcmc-poi-missing", "broken_poi_reference"),
        ("menu_items", "source_id", "hcmc-source-missing", "broken_source_reference"),
        ("narrations", "poi_id", "hcmc-poi-missing", "broken_poi_reference"),
        ("narrations", "source_id", "hcmc-source-missing", "broken_source_reference"),
    ],
)
def test_broken_references_fail_actionably(
    tmp_path: Path,
    collection: str,
    field: str,
    value: object,
    code: str,
) -> None:
    document = copied_document()
    records = document[collection]
    assert isinstance(records, list)
    records[0][field] = value

    issues = load_package(_write_package(tmp_path, document)).issues

    assert code in {issue.code for issue in issues}
    assert any(field in issue.field_path for issue in issues)


@pytest.mark.parametrize(
    "collection",
    ["sources", "pois", "menu_items", "narrations"],
)
def test_record_city_mismatch_is_rejected(
    tmp_path: Path,
    collection: str,
) -> None:
    document = copied_document()
    records = document[collection]
    assert isinstance(records, list)
    records[0]["city_code"] = "bkk"

    assert "city_mismatch" in _codes(_write_package(tmp_path, document))


@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        (("package", "published_at"), "not-a-timestamp"),
        (("sources", 0, "retrieved_at"), "2026-01-01"),
        (("menu_items", 0, "source_updated_at"), "invalid"),
    ],
)
def test_malformed_or_naive_timestamps_fail(
    tmp_path: Path,
    field_path: tuple[str | int, ...],
    value: str,
) -> None:
    document = copied_document()
    target: Any = document
    for part in field_path[:-1]:
        target = target[part]
    target[field_path[-1]] = value

    assert "invalid_timestamp" in _codes(
        _write_package(tmp_path, document)
    )


def test_invalid_source_url_fails(tmp_path: Path) -> None:
    document = copied_document()
    document["sources"][0]["url"] = "not a URL"

    assert "invalid_url" in _codes(_write_package(tmp_path, document))


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (91.0, 106.7),
        (10.7, 181.0),
        (106.7, 10.7),
        (0.0, 0.0),
        (float("nan"), 106.7),
        (10.7, float("inf")),
    ],
)
def test_invalid_or_swapped_coordinates_fail(
    tmp_path: Path,
    latitude: float,
    longitude: float,
) -> None:
    document = copied_document()
    location = document["pois"][0]["location"]
    location["latitude"] = latitude
    location["longitude"] = longitude

    codes = _codes(_write_package(tmp_path, document))

    assert (
        "invalid_coordinate" in codes
        or "coordinate_outside_city_bounds" in codes
    )


def test_timestamp_beyond_clock_skew_fails(tmp_path: Path) -> None:
    document = copied_document()
    document["package"]["published_at"] = "2999-01-01T00:00:00Z"

    assert "timestamp_in_future" in _codes(
        _write_package(tmp_path, document)
    )


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (-1, "invalid_price"),
        (12.5, "price_not_integer"),
    ],
)
def test_negative_and_floating_point_money_fail(
    tmp_path: Path,
    value: int | float,
    code: str,
) -> None:
    document = copied_document()
    document["menu_items"][0]["price_minor_units"] = value

    assert code in _codes(_write_package(tmp_path, document))


@pytest.mark.parametrize("currency", ["vnd", "VN", "VND1"])
def test_malformed_currency_fails(
    tmp_path: Path,
    currency: str,
) -> None:
    document = copied_document()
    document["menu_items"][0]["currency_code"] = currency

    assert "invalid_currency" in _codes(
        _write_package(tmp_path, document)
    )


@pytest.mark.parametrize("field", ["source_id", "source_updated_at"])
def test_menu_without_provenance_or_freshness_fails(
    tmp_path: Path,
    field: str,
) -> None:
    document = copied_document()
    del document["menu_items"][0][field]

    issues = load_package(_write_package(tmp_path, document)).issues

    assert any(
        issue.code == "missing_field" and field in issue.field_path
        for issue in issues
    )


def test_menu_requires_direct_operator_source(tmp_path: Path) -> None:
    document = copied_document()
    document["sources"][0]["source_type"] = "official_tourism"
    document["menu_items"][0]["source_type"] = "official_tourism"

    assert "menu_source_not_direct" in _codes(
        _write_package(tmp_path, document)
    )


def test_menu_source_requires_retrieval_freshness(tmp_path: Path) -> None:
    document = copied_document()
    del document["sources"][0]["retrieved_at"]

    assert "menu_source_freshness_required" in _codes(
        _write_package(tmp_path, document)
    )


def test_duplicate_physical_poi_is_rejected(tmp_path: Path) -> None:
    document = copied_document()
    duplicate = document["pois"][0].copy()
    duplicate["id"] = "hcmc-poi-duplicate-physical-place"
    duplicate["canonical_name"] = "Alternate spelling of the same place"
    document["pois"].append(duplicate)

    assert "duplicate_physical_poi" in _codes(
        _write_package(tmp_path, document)
    )


def test_duplicate_canonical_poi_name_is_rejected(tmp_path: Path) -> None:
    document = copied_document()
    duplicate = document["pois"][0].copy()
    duplicate["id"] = "hcmc-poi-duplicate-canonical-name"
    duplicate["address"] = "Different address"
    duplicate["location"] = {"latitude": 10.8, "longitude": 106.8}
    document["pois"].append(duplicate)

    assert "duplicate_physical_poi" in _codes(
        _write_package(tmp_path, document)
    )


def test_narration_without_source_or_fallback_fails(
    tmp_path: Path,
) -> None:
    document = copied_document()
    del document["narrations"][0]["source_id"]

    assert "narration_source_required" in _codes(
        _write_package(tmp_path, document)
    )


def test_validation_errors_are_deterministic_and_actionable(
    tmp_path: Path,
) -> None:
    document = copied_document()
    document["pois"][0]["source_ids"] = ["hcmc-source-missing"]
    document["menu_items"][0]["poi_id"] = "hcmc-poi-missing"
    path = _write_package(tmp_path, document)

    first = load_package(path).issues
    second = load_package(path).issues

    assert first == second
    assert list(first) == sorted(first, key=ValidationIssue.sort_key)
    assert all(issue.source_path == path for issue in first)
    assert all(issue.code and issue.field_path.startswith("$") for issue in first)
    assert all("DATABASE_URL" not in issue.render() for issue in first)


def test_validation_cli_never_accesses_database_or_firebase(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("validation-only mode touched an external service")

    monkeypatch.setattr("asyncpg.connect", fail)
    monkeypatch.setattr("firebase_admin.initialize_app", fail)
    monkeypatch.setattr("sqlalchemy.ext.asyncio.create_async_engine", fail)

    exit_code = main(["validate"])

    assert exit_code == 0
    assert "validated package=bkk-starter-v1" in capsys.readouterr().out


def test_invalid_cli_is_nonzero_and_does_not_print_document(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_marker = "SENTINEL_DOCUMENT_CONTENT"
    document = copied_document()
    document["unexpected"] = secret_marker
    path = _write_package(tmp_path, document)

    exit_code = main(["validate", "--path", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "code=unknown_field" in captured.err
    assert "field=$.unexpected" in captured.err
    assert secret_marker not in captured.err
