"""Deterministic tests for the provider-neutral POI boundary."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from typing import Self, cast

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.poi.contracts import PoiProvider
from app.providers.poi.curated import CuratedPoiProvider
from app.providers.poi.errors import (
    PoiProviderError,
    ProviderErrorCode,
    ProviderFailure,
)
from app.providers.poi.models import (
    Coordinates,
    PoiDiscoveryRequest,
    PoiDiscoveryResult,
    PoiProviderKind,
    PoiResultEnvelope,
    PriceLevel,
    ProviderTimeoutPolicy,
    SourceReference,
    SupportedCity,
    build_normalized_poi_id,
)
import app.providers.poi.contracts as contract_module
import app.providers.poi.errors as error_module
import app.providers.poi.models as model_module


def _request(**updates: object) -> PoiDiscoveryRequest:
    values: dict[str, object] = {
        "query": "museum",
        "category": "museum",
        "city": SupportedCity.HCMC,
        "origin": Coordinates(latitude=10.7795, longitude=106.692),
        "radius_metres": 2_000,
        "limit": 5,
    }
    values.update(updates)
    return PoiDiscoveryRequest.model_validate(values)


def _external_result() -> PoiDiscoveryResult:
    provider = PoiProviderKind.GOOGLE_PLACES
    provider_id = "future-place-id"
    return PoiDiscoveryResult(
        id=build_normalized_poi_id(provider, provider_id),
        provider=provider,
        provider_id=provider_id,
        canonical_name="Future Place",
        city=SupportedCity.BANGKOK,
        category="restaurant",
        address=None,
        coordinates=Coordinates(latitude=13.75, longitude=100.5),
        distance_metres=125.5,
        rating=Decimal("4.4"),
        rating_count=120,
        price_level=PriceLevel.MODERATE,
        sources=(),
        retrieved_at=None,
        is_curated=False,
        is_externally_supplied=True,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("origin", {"latitude": -90.1, "longitude": 0.0}),
        ("origin", {"latitude": 0.0, "longitude": 180.1}),
        ("origin", {"latitude": float("nan"), "longitude": 0.0}),
        ("origin", {"latitude": 0.0, "longitude": float("inf")}),
        ("radius_metres", 0),
        ("radius_metres", 50_001),
        ("limit", 0),
        ("limit", 21),
    ],
)
def test_request_rejects_invalid_bounded_values(
    field: str,
    value: object,
) -> None:
    values: dict[str, object] = {
        "city": "hcmc",
        "origin": {"latitude": 10.77, "longitude": 106.7},
        "radius_metres": 1_000,
        "limit": 5,
    }
    values[field] = value

    with pytest.raises(ValidationError):
        PoiDiscoveryRequest.model_validate(values)


def test_request_normalizes_blank_filters_and_internal_whitespace() -> None:
    request = _request(query="  ", category="\n\t")
    normalized = _request(
        query="  War   Remnants  ",
        category="  MuSeUm ",
    )

    assert request.query is None
    assert request.category is None
    assert normalized.query == "War Remnants"
    assert normalized.category == "museum"
    assert normalized.radius_metres == 2_000


@pytest.mark.parametrize("seconds", [0.0, 60.1, float("inf")])
def test_timeout_policy_is_positive_finite_and_bounded(seconds: float) -> None:
    with pytest.raises(ValidationError):
        ProviderTimeoutPolicy(seconds=seconds)


def test_contracts_are_immutable_and_forbid_unknown_fields() -> None:
    request = _request()

    with pytest.raises(ValidationError):
        setattr(
            request,
            "origin",
            Coordinates(latitude=0.0, longitude=0.0),
        )
    with pytest.raises(ValidationError):
        PoiDiscoveryRequest.model_validate(
            {
                **request.model_dump(),
                "raw": {"provider": "escape"},
            }
        )


def test_normalized_result_serializes_without_provider_dependencies() -> None:
    source = SourceReference.model_validate(
        {
            "source_id": "bkk-source",
            "source_type": "official_operator",
            "label": "Official source",
            "url": "https://example.test/source",
            "published_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "retrieved_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    )
    provider = PoiProviderKind.CURATED
    provider_id = "bkk-poi-test"
    result = PoiDiscoveryResult(
        id=build_normalized_poi_id(provider, provider_id),
        provider=provider,
        provider_id=provider_id,
        canonical_name="Test POI",
        city=SupportedCity.BANGKOK,
        category="temple",
        coordinates=Coordinates(latitude=13.75, longitude=100.5),
        distance_metres=125.5,
        sources=(source,),
        retrieved_at=source.retrieved_at,
        is_curated=True,
        is_externally_supplied=False,
    )
    envelope = PoiResultEnvelope(
        provider=provider,
        items=(result,),
        returned_count=1,
        is_complete=True,
        freshness_at=result.retrieved_at,
    )

    serialized = envelope.model_dump(mode="json", exclude_none=True)
    assert serialized["provider"] == "curated"
    assert serialized["items"][0]["distance_metres"] == 125.5
    assert serialized["items"][0]["retrieved_at"].endswith("Z")
    assert "raw" not in envelope.model_dump_json()


def test_naive_freshness_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceReference(
            source_id="source",
            source_type="official_operator",
            label="Source",
            retrieved_at=datetime(2026, 1, 1),
        )


def test_provider_ids_are_namespaced_and_deterministic() -> None:
    curated = build_normalized_poi_id(
        PoiProviderKind.CURATED,
        "shared-id",
    )
    google = build_normalized_poi_id(
        PoiProviderKind.GOOGLE_PLACES,
        "shared-id",
    )

    assert curated == "curated:shared-id"
    assert google == "google_places:shared-id"
    assert curated != google
    with pytest.raises(ValidationError):
        PoiDiscoveryResult.model_validate(
            {
                **_external_result().model_dump(),
                "id": curated,
            }
        )


def test_public_models_have_no_payload_escape_hatch() -> None:
    forbidden = {"raw", "payload", "metadata", "extra"}
    public_models = (
        Coordinates,
        PoiDiscoveryRequest,
        PoiDiscoveryResult,
        PoiResultEnvelope,
        ProviderTimeoutPolicy,
        SourceReference,
        ProviderFailure,
    )

    for model in public_models:
        assert forbidden.isdisjoint(model.model_fields)
    assert "description" not in PoiDiscoveryResult.model_fields
    assert "menu" not in PoiDiscoveryResult.model_fields
    assert "narration" not in PoiDiscoveryResult.model_fields


@pytest.mark.parametrize(
    ("code", "retryable"),
    [
        (ProviderErrorCode.TIMEOUT, True),
        (ProviderErrorCode.UNAVAILABLE, True),
        (ProviderErrorCode.RATE_LIMITED, True),
        (ProviderErrorCode.INVALID_RESPONSE, False),
        (ProviderErrorCode.INTERNAL, False),
    ],
)
def test_error_taxonomy_has_canonical_retryability(
    code: ProviderErrorCode,
    retryable: bool,
) -> None:
    failure = ProviderFailure.for_code(
        PoiProviderKind.GOOGLE_PLACES,
        code,
    )

    assert failure.code is code
    assert failure.retryable is retryable
    assert failure.message


def test_failure_rejects_raw_exception_text() -> None:
    with pytest.raises(ValidationError):
        ProviderFailure(
            provider=PoiProviderKind.CURATED,
            code=ProviderErrorCode.UNAVAILABLE,
            message="postgresql://user:password@database token=api-key",
            retryable=True,
        )


class _FailingSession:
    async def execute(self, statement: object) -> None:
        del statement
        raise OperationalError(
            "SELECT token_sentinel",
            {},
            RuntimeError("postgresql://user:password@database api-key-sentinel"),
        )


def test_database_failure_is_sanitized_as_unavailable() -> None:
    provider = CuratedPoiProvider(cast(AsyncSession, _FailingSession()))

    with pytest.raises(PoiProviderError) as captured:
        asyncio.run(provider.discover(_request()))

    failure = captured.value.failure
    public = failure.model_dump_json()
    assert failure.code is ProviderErrorCode.UNAVAILABLE
    assert failure.retryable is True
    assert "token_sentinel" not in public
    assert "api-key-sentinel" not in public
    assert "password" not in public
    assert "postgresql" not in public
    assert str(captured.value) == "unavailable"
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


class _InvalidMappingsResult:
    def mappings(self) -> Self:
        return self

    def all(self) -> list[Mapping[str, object]]:
        return [
            {
                "provider_id": "curated-invalid",
                "canonical_name": "Invalid city row",
                "city": "unsupported-city",
                "category": "test",
                "address": None,
                "latitude": 10.0,
                "longitude": 106.0,
                "distance_metres": 10.0,
                "source_id": None,
            }
        ]


class _InvalidResponseSession:
    async def execute(self, statement: object) -> _InvalidMappingsResult:
        del statement
        return _InvalidMappingsResult()


def test_invalid_database_row_uses_invalid_response_failure() -> None:
    provider = CuratedPoiProvider(cast(AsyncSession, _InvalidResponseSession()))

    with pytest.raises(PoiProviderError) as captured:
        asyncio.run(provider.discover(_request()))

    assert captured.value.failure == ProviderFailure.for_code(
        PoiProviderKind.CURATED,
        ProviderErrorCode.INVALID_RESPONSE,
    )
    assert captured.value.__context__ is None


class _DelayedSession:
    async def execute(self, statement: object) -> None:
        del statement
        await asyncio.sleep(60)


def test_curated_timeout_uses_standardized_failure_shape() -> None:
    provider = CuratedPoiProvider(
        cast(AsyncSession, _DelayedSession()),
        timeout_policy=ProviderTimeoutPolicy(seconds=0.001),
    )

    with pytest.raises(PoiProviderError) as captured:
        asyncio.run(provider.discover(_request()))

    assert captured.value.failure == ProviderFailure.for_code(
        PoiProviderKind.CURATED,
        ProviderErrorCode.TIMEOUT,
    )


def test_caller_cancellation_propagates_unchanged() -> None:
    async def exercise() -> None:
        provider = CuratedPoiProvider(cast(AsyncSession, _DelayedSession()))
        task = asyncio.create_task(provider.discover(_request()))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())


class _FutureProvider:
    async def discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        del request
        result = _external_result()
        return PoiResultEnvelope(
            provider=PoiProviderKind.GOOGLE_PLACES,
            items=(result,),
            returned_count=1,
            is_complete=True,
            freshness_at=None,
        )


def test_future_provider_structurally_satisfies_same_protocol() -> None:
    provider: PoiProvider = _FutureProvider()
    envelope = asyncio.run(provider.discover(_request()))

    assert isinstance(provider, PoiProvider)
    assert envelope.provider is PoiProviderKind.GOOGLE_PLACES
    assert envelope.items[0].rating == Decimal("4.4")


def test_contract_modules_have_no_framework_or_provider_sdk_types() -> None:
    source = "\n".join(
        inspect.getsource(module)
        for module in (contract_module, error_module, model_module)
    ).casefold()

    for forbidden in (
        "fastapi",
        "firebase",
        "sqlalchemy",
        "geoalchemy",
        "google.cloud",
        "googlemaps",
    ):
        assert forbidden not in source
