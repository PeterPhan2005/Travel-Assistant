"""Deterministic, database-free travel-package artifact tests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.data_pipeline.models import CuratedPackageV1
from app.travel_packages.builder import (
    ArtifactBuildError,
    ArtifactVerificationError,
    artifact_from_curated,
    build_city_package,
    build_package_path,
    canonical_json_bytes,
    check_committed_artifact,
    committed_output_dir,
    verify_manifest,
)
from app.travel_packages.cli import main
from app.travel_packages.models import (
    ARTIFACT_FIELD_ALLOWLIST,
    ArtifactPoiV1,
)
from tests.curated_fixtures import valid_package_document

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ANDROID_ROOT = REPOSITORY_ROOT / "android" / "app"
HCMC_MANIFEST_NAME = "hcmc-starter-v1-1.1.0.manifest.json"
FORBIDDEN_PUBLIC_KEYS = {
    "user",
    "userId",
    "firebaseUid",
    "preferences",
    "trips",
    "itineraries",
    "origin",
    "locationHistory",
    "token",
    "credentials",
    "payload",
    "raw",
    "metadata",
    "databaseId",
}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key
            for child in value.values()
            for key in _all_keys(child)
        }
    if isinstance(value, list):
        return {
            key
            for child in value
            for key in _all_keys(child)
        }
    return set()


def _manifest_for(directory: Path) -> Path:
    return directory / HCMC_MANIFEST_NAME


def test_builds_valid_hcmc_and_generic_bangkok(tmp_path: Path) -> None:
    hcmc = build_city_package("hcmc", tmp_path / "hcmc")
    bangkok = build_city_package("bkk", tmp_path / "bkk")

    assert hcmc.manifest.city.value == "hcmc"
    assert len(hcmc.artifact.pois) == 30
    assert bangkok.manifest.city.value == "bkk"
    assert bangkok.artifact.package_metadata.city == "Bangkok"
    assert len(bangkok.artifact.pois) == 1
    assert len(list((tmp_path / "hcmc").iterdir())) == 2
    assert len(list((tmp_path / "bkk").iterdir())) == 2


def test_cli_requires_exactly_one_supported_city(tmp_path: Path) -> None:
    assert (
        main(
            [
                "build",
                "--city",
                "hcmc",
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert {path.name for path in tmp_path.iterdir()} == {
        "hcmc-starter-v1-1.1.0.data.json",
        HCMC_MANIFEST_NAME,
    }
    with pytest.raises(ArtifactBuildError, match="unsupported city"):
        build_city_package("sgn", tmp_path / "unsupported")


def test_invalid_source_writes_no_artifact_or_temporary_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "invalid.yaml"
    source.write_text(
        "schema_version: 1\npackage:\n  package_id: invalid\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"

    with pytest.raises(ArtifactBuildError, match="validation failed"):
        build_package_path(source, output)

    assert not output.exists()


def test_models_forbid_unknown_fields_recursively() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        ArtifactPoiV1.model_validate(
            {
                "poiId": "hcmc-poi-test",
                "name": "Test",
                "city": "Ho Chi Minh City",
                "category": "test",
                "latitude": 10.7,
                "longitude": 106.7,
                "status": "curated",
                "updatedAtEpochMillis": 1,
                "raw": {},
            }
        )


def test_recursive_allowlist_excludes_private_and_escape_hatch_fields(
    tmp_path: Path,
) -> None:
    result = build_city_package("hcmc", tmp_path)
    document = _json(result.data_path)

    assert set(document) == set(ARTIFACT_FIELD_ALLOWLIST)
    assert not (_all_keys(document) & FORBIDDEN_PUBLIC_KEYS)
    assert "sources" not in document
    assert "sourceIds" not in _all_keys(document)


def test_all_entity_collections_and_poi_manifest_are_stably_sorted() -> None:
    raw = valid_package_document()
    second = deepcopy(raw["pois"][0])
    second["id"] = "hcmc-poi-alpha"
    second["canonical_name"] = "Á Đông"
    raw["pois"].insert(0, second)
    raw["pois"].reverse()
    package = CuratedPackageV1.model_validate(raw)

    artifact = artifact_from_curated(package)

    assert [record.poi_id for record in artifact.pois] == [
        "hcmc-poi-alpha",
        "hcmc-poi-test",
    ]
    assert artifact.package_metadata.manifest.poi_ids == (
        "hcmc-poi-alpha",
        "hcmc-poi-test",
    )


def test_canonical_serialization_has_sorted_keys_utf8_and_one_newline(
    tmp_path: Path,
) -> None:
    result = build_city_package("hcmc", tmp_path)
    raw = result.data_path.read_bytes()
    text = raw.decode("utf-8")
    top_level = json.loads(text, object_pairs_hook=dict)

    assert list(top_level) == sorted(top_level)
    assert "Bưu điện Trung tâm Sài Gòn" in text
    assert "\\u" not in text
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    assert b'": ' not in raw
    assert canonical_json_bytes(result.artifact) == raw


def test_datetime_serialization_is_deterministic_and_clock_free(
    tmp_path: Path,
) -> None:
    first = build_city_package("hcmc", tmp_path / "first")
    second = build_city_package("hcmc", tmp_path / "second")

    assert first.manifest.published_at == "2026-08-12T04:16:22Z"
    assert (
        first.artifact.package_metadata.published_at_epoch_millis
        == 1_786_508_182_000
    )
    assert (
        first.manifest_path.read_bytes()
        == second.manifest_path.read_bytes()
    )


def test_repeated_builds_are_byte_identical_across_directories(
    tmp_path: Path,
) -> None:
    first = build_city_package("hcmc", tmp_path / "a")
    second = build_city_package("hcmc", tmp_path / "different" / "b")

    assert first.data_path.name == second.data_path.name
    assert first.manifest_path.name == second.manifest_path.name
    assert first.data_path.read_bytes() == second.data_path.read_bytes()
    assert (
        first.manifest_path.read_bytes()
        == second.manifest_path.read_bytes()
    )
    assert first.manifest.sha256 == second.manifest.sha256


def test_manifest_checksum_and_size_cover_exact_data_bytes(
    tmp_path: Path,
) -> None:
    result = build_city_package("hcmc", tmp_path)
    data = result.data_path.read_bytes()

    assert result.manifest.byte_size == len(data)
    assert result.manifest.sha256 == hashlib.sha256(data).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", result.manifest.sha256)
    assert result.manifest.data_filename == result.data_path.name
    assert not Path(result.manifest.data_filename).is_absolute()


def test_verify_succeeds_and_tampered_data_fails(tmp_path: Path) -> None:
    result = build_city_package("hcmc", tmp_path)
    verified = verify_manifest(result.manifest_path)
    assert verified.artifact == result.artifact

    data = bytearray(result.data_path.read_bytes())
    data[0] = ord("[")
    result.data_path.write_bytes(bytes(data))
    with pytest.raises(
        ArtifactVerificationError,
        match="SHA-256",
    ):
        verify_manifest(result.manifest_path)


def test_verify_rejects_malformed_checksum_and_missing_data(
    tmp_path: Path,
) -> None:
    malformed_dir = tmp_path / "malformed"
    malformed = build_city_package("hcmc", malformed_dir)
    manifest = _json(malformed.manifest_path)
    manifest["sha256"] = "ABC"
    _write_json(malformed.manifest_path, manifest)
    with pytest.raises(
        ArtifactVerificationError,
        match="manifest contract",
    ):
        verify_manifest(malformed.manifest_path)

    missing = build_city_package("hcmc", tmp_path / "missing")
    missing.data_path.unlink()
    with pytest.raises(
        ArtifactVerificationError,
        match="data file could not be read",
    ):
        verify_manifest(missing.manifest_path)


def test_verify_rejects_manifest_data_identity_mismatch(
    tmp_path: Path,
) -> None:
    result = build_city_package("hcmc", tmp_path)
    document = _json(result.data_path)
    document["packageMetadata"]["packageId"] = "hcmc-other-v1"
    _write_json(result.data_path, document)
    data = result.data_path.read_bytes()
    manifest = _json(result.manifest_path)
    manifest["byteSize"] = len(data)
    manifest["sha256"] = hashlib.sha256(data).hexdigest()
    _write_json(result.manifest_path, manifest)

    with pytest.raises(
        ArtifactVerificationError,
        match="package identity",
    ):
        verify_manifest(result.manifest_path)


def test_verify_rejects_unsafe_data_filename(tmp_path: Path) -> None:
    result = build_city_package("hcmc", tmp_path)
    manifest = _json(result.manifest_path)
    manifest["dataFilename"] = "../secret.data.json"
    _write_json(result.manifest_path, manifest)

    with pytest.raises(
        ArtifactVerificationError,
        match="manifest contract",
    ):
        verify_manifest(result.manifest_path)


def test_atomic_failure_leaves_no_partial_or_temporary_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second_replace(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(
        "app.travel_packages.builder.os.replace",
        fail_second_replace,
    )

    with pytest.raises(ArtifactBuildError, match="atomic"):
        build_city_package("hcmc", tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_rebuild_replaces_only_known_artifact_files(tmp_path: Path) -> None:
    unrelated = tmp_path / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")
    first = build_city_package("hcmc", tmp_path)
    second = build_city_package("hcmc", tmp_path)

    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert first.data_path.read_bytes() == second.data_path.read_bytes()
    assert not list(tmp_path.glob("*.tmp"))


def test_committed_hcmc_artifact_matches_regenerated_output() -> None:
    verified = check_committed_artifact()

    assert verified.manifest_path.parent == committed_output_dir()
    assert verified.manifest.package_id == "hcmc-starter-v1"
    assert len(verified.artifact.pois) == 30


def test_artifact_is_ordinary_static_json_without_fabricated_content(
    tmp_path: Path,
) -> None:
    result = build_city_package("hcmc", tmp_path)

    assert result.manifest.media_type == "application/json"
    assert result.data_path.suffix == ".json"
    assert result.manifest_path.suffix == ".json"
    assert result.artifact.aliases == ()
    assert len(result.artifact.menu_items) == 3
    assert len(result.artifact.narrations) == 30


def test_supported_menu_and_narration_fields_are_preserved_not_synthesized() -> None:
    package = CuratedPackageV1.model_validate(valid_package_document())
    artifact = artifact_from_curated(package)

    assert artifact.menu_items[0].price_minor_units == 12_500
    assert artifact.menu_items[0].currency_code == "VND"
    assert artifact.menu_items[0].source_type.value == "official_operator"
    assert artifact.narrations[0].source_label == "Test operator source"
    assert artifact.narrations[0].verification_status.value == "verified"


def test_build_subprocess_does_not_initialize_server_integrations(
    tmp_path: Path,
) -> None:
    script = (
        "import sys;"
        "from pathlib import Path;"
        "from app.travel_packages import build_city_package;"
        f"build_city_package('hcmc', Path({str(tmp_path)!r}));"
        "blocked={'firebase_admin','fastapi','sqlalchemy','asyncpg'};"
        "seen={name.split('.')[0] for name in sys.modules};"
        "raise SystemExit(1 if blocked & seen else 0)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPOSITORY_ROOT / "backend",
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_android_seed_dto_and_room_v2_cover_artifact_fields(
    tmp_path: Path,
) -> None:
    result = build_city_package("hcmc", tmp_path)
    document = _json(result.data_path)
    seed_dto = (
        ANDROID_ROOT
        / "src/main/java/com/kltn/travelassistant/data/seed/SeedDocument.kt"
    ).read_text(encoding="utf-8")
    room_schema = _json(
        ANDROID_ROOT
        / (
            "schemas/com.kltn.travelassistant.data.local."
            "TravelAssistantDatabase/2.json"
        )
    )

    top_level_dto_fields = {
        "formatVersion",
        "packageMetadata",
        "pois",
        "aliases",
        "menuItems",
        "narrations",
        "cultureItems",
    }
    assert set(document) <= top_level_dto_fields
    for key in document:
        assert f"val {key}:" in seed_dto

    room_columns = {
        field["columnName"]
        for entity in room_schema["database"]["entities"]
        for field in entity["fields"]
    }
    required_room_columns = {
        "package_id",
        "city",
        "version",
        "manifest_json",
        "published_at_epoch_millis",
        "poi_id",
        "name",
        "area",
        "category",
        "latitude",
        "longitude",
        "address",
        "short_description",
        "status",
        "updated_at_epoch_millis",
        "alias_id",
        "alias",
        "normalized_alias",
        "language_code",
        "menu_item_id",
        "dish_name",
        "price_minor_units",
        "currency_code",
        "source_type",
        "narration_id",
        "content",
        "verification_status",
        "generated_at_epoch_millis",
        "source_label",
    }
    assert required_room_columns <= room_columns


def test_cli_verify_check_and_failures_have_nonzero_exit_codes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = build_city_package("hcmc", tmp_path)

    assert main(["verify", "--manifest", str(result.manifest_path)]) == 0
    assert main(["check"]) == 0
    result.data_path.unlink()
    assert main(["verify", "--manifest", str(result.manifest_path)]) == 1
    assert "failed" in capsys.readouterr().err
