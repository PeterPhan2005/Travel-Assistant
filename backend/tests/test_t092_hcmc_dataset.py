"""Focused acceptance coverage for the canonical T092 HCMC dataset."""

from __future__ import annotations

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
from app.travel_packages.builder import artifact_from_curated, canonical_json_bytes

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_CATEGORY_COUNTS = {
    "cultural_space": 1,
    "entertainment": 1,
    "family_attraction": 1,
    "heritage_site": 1,
    "history_site": 1,
    "landmark": 2,
    "market": 3,
    "modern_attraction": 2,
    "museum": 7,
    "nature": 1,
    "park": 2,
    "performing_arts": 1,
    "public_space": 1,
    "religious_site": 5,
    "restaurant": 1,
}
EXPECTED_AREA_COUNTS = {
    "Phường Bến Thành": 5,
    "Phường Bình Tây": 1,
    "Phường Bảy Hiền": 1,
    "Phường Chợ Lớn": 1,
    "Phường Gia Định": 1,
    "Phường Long Phước": 1,
    "Phường Sài Gòn": 11,
    "Phường Thạnh Mỹ Tây": 1,
    "Phường Tân Định": 2,
    "Phường Xuân Hòa": 3,
    "Phường Xóm Chiếu": 1,
    "Xã An Nhơn Tây": 1,
    "Xã An Thới Đông": 1,
}
OBSOLETE_HCMC_ADDRESS_COMPONENTS = (
    "Quận ",
    "Huyện ",
    "Thành phố Thủ Đức",
)


def _package() -> CuratedPackageV1:
    result = load_package(CITY_PACKAGE_PATHS["hcmc"])
    assert result.is_valid
    return result.packages[0].package


def test_t092_has_exactly_30_unique_hcmc_pois_with_valid_coordinates() -> None:
    package = _package()
    assert len(package.pois) == 30
    assert len({poi.id for poi in package.pois}) == 30
    latitude_bounds = CITY_BOUNDS[CityCode.HCMC]["latitude"]
    longitude_bounds = CITY_BOUNDS[CityCode.HCMC]["longitude"]

    for poi in package.pois:
        assert poi.city_code is CityCode.HCMC
        assert latitude_bounds[0] <= poi.location.latitude <= latitude_bounds[1]
        assert longitude_bounds[0] <= poi.location.longitude <= longitude_bounds[1]


def test_t092_has_source_closure_and_approved_source_classes() -> None:
    package = _package()
    sources = {source.id: source for source in package.sources}
    approved = {
        SourceType.OFFICIAL_GOVERNMENT,
        SourceType.OFFICIAL_INSTITUTION,
        SourceType.OFFICIAL_OPERATOR,
        SourceType.OFFICIAL_TOURISM,
    }
    assert all(source.source_type in approved for source in package.sources)
    assert all(source.retrieved_at is not None for source in package.sources)
    assert all(
        source_id in sources
        for poi in package.pois
        for source_id in poi.source_ids
    )


def test_t092_menu_prices_are_direct_fresh_integer_vnd_facts() -> None:
    package = _package()
    sources = {source.id: source for source in package.sources}
    assert package.menu_items
    for item in package.menu_items:
        source = sources[item.source_id]
        assert source.source_type is SourceType.OFFICIAL_OPERATOR
        assert source.retrieved_at is not None
        assert isinstance(item.price_minor_units, int)
        assert item.currency_code == "VND"
        assert item.source_updated_at <= source.retrieved_at
        assert item.source_updated_at <= datetime.now(item.source_updated_at.tzinfo)


def test_t092_every_poi_has_one_source_grounded_vietnamese_narration() -> None:
    package = _package()
    poi_ids = {poi.id for poi in package.pois}
    source_ids = {source.id for source in package.sources}
    assert len(package.narrations) == len(package.pois) == 30
    assert {narration.poi_id for narration in package.narrations} == poi_ids
    for narration in package.narrations:
        assert narration.language_code == "vi-VN"
        assert narration.verification_status is VerificationStatus.VERIFIED
        assert narration.source_id in source_ids
        assert narration.fallback_source_label is None
        assert 100 <= len(narration.content.split()) <= 200


def test_t092_category_and_area_coverage_is_reviewable_and_not_food_dominated(
) -> None:
    package = _package()
    category_counts = Counter(poi.category for poi in package.pois)
    area_counts = Counter(poi.area for poi in package.pois)
    assert dict(sorted(category_counts.items())) == EXPECTED_CATEGORY_COUNTS
    assert len(area_counts) == 13
    assert category_counts["restaurant"] < len(package.pois) // 2


def test_t092_uses_current_post_2025_hcmc_locality_labels() -> None:
    package = _package()
    assert Counter(poi.area for poi in package.pois) == Counter(
        EXPECTED_AREA_COUNTS
    )
    for poi in package.pois:
        assert poi.area is not None
        assert poi.address is not None
        assert poi.area.startswith(("Phường ", "Xã "))
        assert poi.area in poi.address
        assert not any(
            component in poi.area or component in poi.address
            for component in OBSOLETE_HCMC_ADDRESS_COMPONENTS
        )


def test_t092_public_artifact_generation_is_deterministic_and_source_closed(
) -> None:
    package = _package()
    first = artifact_from_curated(package)
    second = artifact_from_curated(package)
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert len(first.pois) == 30
    assert len(first.menu_items) == 3
    assert len(first.narrations) == 30
    assert first.aliases == ()


def test_t092_preserves_the_published_1_0_0_artifact_bytes() -> None:
    artifact_dir = REPOSITORY_ROOT / "data" / "travel-packages" / "hcmc" / "1.0.0"
    data_path = artifact_dir / "hcmc-starter-v1-1.0.0.data.json"
    manifest_path = artifact_dir / "hcmc-starter-v1-1.0.0.manifest.json"
    assert len(data_path.read_bytes()) == 934
    assert (
        manifest_path.read_text(encoding="utf-8")
        == '{"artifactSchemaVersion":1,"byteSize":934,"city":"hcmc",'
        '"contentVersion":"1.0.0","dataFilename":'
        '"hcmc-starter-v1-1.0.0.data.json","mediaType":"application/json",'
        '"packageId":"hcmc-starter-v1","publishedAt":'
        '"2026-07-26T17:00:00Z","schemaVersion":1,"sha256":'
        '"daa7678e1998348c6904f12f6e96026aa7ac33068fab7d8dcdc2ec0b23ae6be3"}\n'
    )
