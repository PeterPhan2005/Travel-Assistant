"""Deterministic authored-package fixtures for curated pipeline tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.data_pipeline.models import CuratedPackageV1


def valid_package_document(city: str = "hcmc") -> dict[str, Any]:
    """Return a complete synthetic contract fixture, not production content."""
    if city == "hcmc":
        latitude, longitude = 10.77, 106.70
        currency = "VND"
    else:
        latitude, longitude = 13.75, 100.50
        currency = "THB"
    return {
        "schema_version": 1,
        "package": {
            "package_id": f"{city}-test-package",
            "city_code": city,
            "content_version": "1.0.0",
            "published_at": "2026-01-01T00:00:00Z",
        },
        "sources": [
            {
                "id": f"{city}-source-test",
                "city_code": city,
                "source_type": "official_operator",
                "label": "Test operator source",
                "publisher": "Test publisher",
                "url": "https://example.test/source",
                "published_at": "2025-12-31T00:00:00Z",
                "retrieved_at": "2026-01-01T00:00:00Z",
            }
        ],
        "pois": [
            {
                "id": f"{city}-poi-test",
                "city_code": city,
                "canonical_name": "Test POI",
                "category": "test_category",
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "source_ids": [f"{city}-source-test"],
            }
        ],
        "menu_items": [
            {
                "id": f"{city}-menu-test",
                "city_code": city,
                "poi_id": f"{city}-poi-test",
                "source_id": f"{city}-source-test",
                "item_name": "Test menu item",
                "price_minor_units": 12500,
                "currency_code": currency,
                "source_type": "official_operator",
                "source_updated_at": "2026-01-01T00:00:00Z",
            }
        ],
        "narrations": [
            {
                "id": f"{city}-narration-test",
                "city_code": city,
                "poi_id": f"{city}-poi-test",
                "source_id": f"{city}-source-test",
                "language_code": "vi",
                "content": (
                    "Synthetic narration content used only to verify "
                    "deterministic database mapping."
                ),
                "verification_status": "verified",
            }
        ],
    }


def copied_document(city: str = "hcmc") -> dict[str, Any]:
    """Return a deep copy suitable for focused mutation."""
    return deepcopy(valid_package_document(city))


def valid_package(city: str = "hcmc") -> CuratedPackageV1:
    """Return the typed valid synthetic package."""
    return CuratedPackageV1.model_validate(valid_package_document(city))
