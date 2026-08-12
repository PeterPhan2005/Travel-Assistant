"""Focused acceptance coverage for the canonical T093 Bangkok dataset."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.data_pipeline.loader import load_package
from app.data_pipeline.models import (
    CityCode,
    CuratedPackageV1,
    SourceType,
    VerificationStatus,
)
from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from app.data_pipeline.validation import CITY_BOUNDS
from app.travel_packages.builder import (
    artifact_from_curated,
    canonical_json_bytes,
    verify_manifest,
)
from tests.curated_fixtures import valid_package

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BANGKOK_ARTIFACT_DIR = (
    REPOSITORY_ROOT / "data" / "travel-packages" / "bkk" / "1.1.0"
)
BANGKOK_MANIFEST = (
    BANGKOK_ARTIFACT_DIR / "bkk-starter-v1-1.1.0.manifest.json"
)
EXPECTED_CATEGORY_COUNTS = {
    "cultural_space": 1,
    "landmark": 1,
    "market": 2,
    "modern_attraction": 1,
    "museum": 1,
    "park": 1,
    "performing_arts": 1,
    "public_space": 1,
    "restaurant": 1,
    "temple": 2,
}
EXPECTED_AREA_COUNTS = {
    "Bang Rak": 1,
    "Bangkok Yai": 1,
    "Chatuchak": 1,
    "Huai Khwang": 1,
    "Khlong Toei": 1,
    "Pathum Wan": 1,
    "Phra Nakhon": 6,
}
PRE_T093_HCMC_SHA256 = {
    "data/curated/hcmc/package-v1.yaml": (
        "82e14e6c9ad903a5332c9a4ccae8eb2f6670785a45b0d9e2e4013a6ce27ba7af"
    ),
    "data/travel-packages/hcmc/1.0.0/hcmc-starter-v1-1.0.0.data.json": (
        "daa7678e1998348c6904f12f6e96026aa7ac33068fab7d8dcdc2ec0b23ae6be3"
    ),
    "data/travel-packages/hcmc/1.0.0/hcmc-starter-v1-1.0.0.manifest.json": (
        "438c860d79b6e7d8f2dd7e49a2850f4bc9c4b9041504c4a7611ef97132359332"
    ),
    "data/travel-packages/hcmc/1.1.0/hcmc-starter-v1-1.1.0.data.json": (
        "9632ff38d7dd798bf6c89298c4560c6093ccc59c9668490b8dd51672e548138d"
    ),
    "data/travel-packages/hcmc/1.1.0/hcmc-starter-v1-1.1.0.manifest.json": (
        "2f1ee4fc27df42e978d951897f9ccc829257a9104f256b34b46c4715e606c51c"
    ),
}


def _package(city: str) -> CuratedPackageV1:
    result = load_package(CITY_PACKAGE_PATHS[city])
    assert result.is_valid
    return result.packages[0].package


def test_t093_has_exactly_12_unique_bangkok_pois_and_42_total() -> None:
    bangkok = _package("bkk")
    hcmc = _package("hcmc")
    assert len(bangkok.pois) == 12
    assert len(hcmc.pois) == 30
    assert len(bangkok.pois) + len(hcmc.pois) == 42
    assert len({poi.id for poi in bangkok.pois}) == 12
    assert all(poi.city_code is CityCode.BANGKOK for poi in bangkok.pois)


def test_t093_coordinates_are_valid_and_physical_pois_are_unique() -> None:
    package = _package("bkk")
    latitude_bounds = CITY_BOUNDS[CityCode.BANGKOK]["latitude"]
    longitude_bounds = CITY_BOUNDS[CityCode.BANGKOK]["longitude"]
    names: set[str] = set()
    addresses: set[str] = set()
    coordinates: set[tuple[float, float]] = set()

    for poi in package.pois:
        assert latitude_bounds[0] <= poi.location.latitude <= latitude_bounds[1]
        assert longitude_bounds[0] <= poi.location.longitude <= longitude_bounds[1]
        normalized_name = poi.canonical_name.casefold()
        normalized_address = (poi.address or "").casefold()
        coordinate = (poi.location.latitude, poi.location.longitude)
        assert normalized_name not in names
        assert normalized_address and normalized_address not in addresses
        assert coordinate not in coordinates
        names.add(normalized_name)
        addresses.add(normalized_address)
        coordinates.add(coordinate)


def test_t093_sources_are_current_closed_and_authoritative() -> None:
    package = _package("bkk")
    sources = {source.id: source for source in package.sources}
    approved = {
        SourceType.OFFICIAL_GOVERNMENT,
        SourceType.OFFICIAL_INSTITUTION,
        SourceType.OFFICIAL_OPERATOR,
        SourceType.OFFICIAL_TOURISM,
    }
    assert len(sources) == 13
    assert all(source.source_type in approved for source in sources.values())
    assert all(source.url is not None for source in sources.values())
    assert all(source.retrieved_at is not None for source in sources.values())
    assert all(
        source.retrieved_at is not None
        and source.retrieved_at <= datetime.now(source.retrieved_at.tzinfo)
        for source in sources.values()
    )
    assert all(
        source_id in sources
        for poi in package.pois
        for source_id in poi.source_ids
    )


def test_t093_narrations_are_grounded_verified_and_vietnamese_facing() -> None:
    package = _package("bkk")
    poi_ids = {poi.id for poi in package.pois}
    source_ids = {source.id for source in package.sources}
    assert len(package.narrations) == len(package.pois) == 12
    assert {narration.poi_id for narration in package.narrations} == poi_ids
    for narration in package.narrations:
        assert narration.language_code == "vi-VN"
        assert narration.verification_status is VerificationStatus.VERIFIED
        assert narration.source_id in source_ids
        assert narration.fallback_source_label is None
        assert 100 <= len(narration.content.split()) <= 200


def test_t093_category_area_and_current_address_coverage_is_reviewable() -> None:
    package = _package("bkk")
    category_counts = Counter(poi.category for poi in package.pois)
    area_counts = Counter(poi.area for poi in package.pois)
    assert dict(sorted(category_counts.items())) == EXPECTED_CATEGORY_COUNTS
    assert dict(sorted(area_counts.items())) == EXPECTED_AREA_COUNTS
    assert category_counts["restaurant"] < len(package.pois) // 2
    for poi in package.pois:
        assert poi.area is not None
        assert poi.address is not None
        assert poi.area in poi.address


def test_t093_omits_unverified_prices_and_preserves_thb_minor_units() -> None:
    package = _package("bkk")
    assert package.menu_items == ()

    synthetic = artifact_from_curated(valid_package("bkk"))
    assert len(synthetic.menu_items) == 1
    assert synthetic.menu_items[0].currency_code == "THB"
    assert synthetic.menu_items[0].price_minor_units == 12500


def test_t093_artifact_is_deterministic_current_and_source_closed() -> None:
    package = _package("bkk")
    first = artifact_from_curated(package)
    second = artifact_from_curated(package)
    verified = verify_manifest(BANGKOK_MANIFEST)
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert canonical_json_bytes(first) == verified.data_path.read_bytes()
    assert verified.manifest.content_version == "1.1.0"
    assert verified.manifest.byte_size == 17_535
    assert verified.manifest.sha256 == (
        "419350ad82ae0a74eb2af7901dfa3f612688d91904c6bac26d7112abbd6c61d7"
    )
    assert len(verified.artifact.pois) == 12
    assert len(verified.artifact.menu_items) == 0
    assert len(verified.artifact.narrations) == 12
    assert verified.artifact.aliases == ()


def test_t093_preserves_all_preexisting_hcmc_bytes() -> None:
    for relative_path, expected_hash in PRE_T093_HCMC_SHA256.items():
        content = (REPOSITORY_ROOT / relative_path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_hash


def test_t093_does_not_retroactively_create_a_bangkok_1_0_0_artifact() -> None:
    assert not (
        REPOSITORY_ROOT / "data" / "travel-packages" / "bkk" / "1.0.0"
    ).exists()
