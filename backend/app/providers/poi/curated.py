"""Read-only curated PostgreSQL/PostGIS POI provider."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, cast as type_cast

from geoalchemy2 import Geography, Geometry
from pydantic import ValidationError
from sqlalchemy import Select, cast, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Poi, PoiSource, Source
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
    ProviderTimeoutPolicy,
    SourceReference,
    SupportedCity,
    build_normalized_poi_id,
    latest_timestamp,
)

_PROVIDER = PoiProviderKind.CURATED
_GEOGRAPHY_POINT = Geography(
    geometry_type="POINT",
    srid=4326,
    spatial_index=False,
)
_GEOMETRY_POINT = Geometry(
    geometry_type="POINT",
    srid=4326,
    spatial_index=False,
)


class CuratedPoiProvider:
    """Discover normalized POIs using one injected async database session."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        timeout_policy: ProviderTimeoutPolicy | None = None,
    ) -> None:
        self._session = session
        self._timeout_policy = timeout_policy or ProviderTimeoutPolicy()

    async def discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        """Execute one bounded read while preserving caller cancellation."""
        failure_code: ProviderErrorCode
        try:
            async with asyncio.timeout(self._timeout_policy.seconds):
                return await self._discover(request)
        except TimeoutError:
            failure_code = ProviderErrorCode.TIMEOUT
        except asyncio.CancelledError:
            raise
        except PoiProviderError:
            raise
        except SQLAlchemyError:
            failure_code = ProviderErrorCode.UNAVAILABLE
        except Exception:
            failure_code = ProviderErrorCode.INTERNAL
        raise self._error(failure_code)

    async def _discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        statement = self._statement(request)
        rows = type_cast(
            Sequence[Mapping[str, Any]],
            (await self._session.execute(statement)).mappings().all(),
        )
        try:
            return self._normalize(rows, request.limit)
        except (TypeError, ValueError, ValidationError):
            pass
        raise self._error(ProviderErrorCode.INVALID_RESPONSE)

    @staticmethod
    def _statement(request: PoiDiscoveryRequest) -> Select[Any]:
        origin = cast(
            func.ST_SetSRID(
                func.ST_MakePoint(
                    request.origin.longitude,
                    request.origin.latitude,
                ),
                4326,
            ),
            _GEOGRAPHY_POINT,
        )
        poi_geometry = cast(Poi.location, _GEOMETRY_POINT)
        distance = func.ST_Distance(Poi.location, origin).label("distance_metres")
        conditions = [
            Poi.city == request.city.value,
            func.ST_DWithin(
                Poi.location,
                origin,
                request.radius_metres,
            ),
        ]
        if request.category is not None:
            conditions.append(func.lower(Poi.category) == request.category)
        if request.query is not None:
            conditions.append(
                or_(
                    Poi.canonical_name.icontains(
                        request.query,
                        autoescape=True,
                    ),
                    Poi.category.icontains(
                        request.query,
                        autoescape=True,
                    ),
                )
            )

        candidates = (
            select(
                Poi.id.label("provider_id"),
                Poi.canonical_name,
                Poi.city,
                Poi.category,
                Poi.address,
                func.ST_Y(poi_geometry).label("latitude"),
                func.ST_X(poi_geometry).label("longitude"),
                distance,
            )
            .where(*conditions)
            .order_by(distance, Poi.id)
            .limit(request.limit + 1)
            .cte("candidate_pois")
        )
        return (
            select(
                *candidates.c,
                Source.id.label("source_id"),
                Source.source_type,
                Source.label.label("source_label"),
                Source.publisher,
                Source.url.label("source_url"),
                Source.published_at,
                Source.retrieved_at.label("source_retrieved_at"),
            )
            .select_from(
                candidates.outerjoin(
                    PoiSource,
                    PoiSource.poi_id == candidates.c.provider_id,
                ).outerjoin(
                    Source,
                    Source.id == PoiSource.source_id,
                )
            )
            .order_by(
                candidates.c.distance_metres,
                candidates.c.provider_id,
                Source.id,
            )
        )

    @staticmethod
    def _normalize(
        rows: Sequence[Mapping[str, Any]],
        limit: int,
    ) -> PoiResultEnvelope:
        grouped: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            provider_id = str(row["provider_id"])
            grouped.setdefault(provider_id, []).append(row)

        candidate_ids = tuple(grouped)
        is_complete = len(candidate_ids) <= limit
        result_ids = candidate_ids[:limit]
        items = tuple(
            CuratedPoiProvider._normalize_item(grouped[provider_id])
            for provider_id in result_ids
        )
        freshness_at = latest_timestamp(tuple(item.retrieved_at for item in items))
        return PoiResultEnvelope(
            provider=_PROVIDER,
            items=items,
            returned_count=len(items),
            is_complete=is_complete,
            freshness_at=freshness_at,
        )

    @staticmethod
    def _normalize_item(
        rows: Sequence[Mapping[str, Any]],
    ) -> PoiDiscoveryResult:
        first = rows[0]
        sources_by_id: dict[str, SourceReference] = {}
        for row in rows:
            source_id = row["source_id"]
            if source_id is None:
                continue
            normalized_source_id = _required_str(source_id)
            source = SourceReference.model_validate(
                {
                    "source_id": normalized_source_id,
                    "source_type": _required_str(row["source_type"]),
                    "label": _required_str(row["source_label"]),
                    "publisher": _optional_str(row["publisher"]),
                    "url": _optional_str(row["source_url"]),
                    "published_at": _datetime_or_none(row["published_at"]),
                    "retrieved_at": _datetime_or_none(row["source_retrieved_at"]),
                }
            )
            sources_by_id[source.source_id] = source

        sources = tuple(sources_by_id[source_id] for source_id in sorted(sources_by_id))
        retrieved_at = latest_timestamp(
            tuple(source.retrieved_at for source in sources)
        )
        provider_id = _required_str(first["provider_id"])
        return PoiDiscoveryResult(
            id=build_normalized_poi_id(_PROVIDER, provider_id),
            provider=_PROVIDER,
            provider_id=provider_id,
            canonical_name=_required_str(first["canonical_name"]),
            city=SupportedCity(_required_str(first["city"])),
            category=_required_str(first["category"]),
            address=_optional_str(first["address"]),
            coordinates=Coordinates(
                latitude=_required_float(first["latitude"]),
                longitude=_required_float(first["longitude"]),
            ),
            distance_metres=_required_float(first["distance_metres"]),
            sources=sources,
            retrieved_at=retrieved_at,
            is_curated=True,
            is_externally_supplied=False,
        )

    @staticmethod
    def _error(code: ProviderErrorCode) -> PoiProviderError:
        return PoiProviderError(ProviderFailure.for_code(_PROVIDER, code))


def _datetime_or_none(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    raise TypeError("Expected a datetime or None.")


def _required_str(value: object) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("Expected a string.")


def _optional_str(value: object) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise TypeError("Expected a string or None.")


def _required_float(value: object) -> float:
    if isinstance(value, float):
        return value
    raise TypeError("Expected a float.")
