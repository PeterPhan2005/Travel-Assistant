"""Request-scoped curated candidate and evidence resolution for T062."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Protocol, cast, runtime_checkable

from geoalchemy2 import Geometry
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError
from sqlalchemy import cast as sql_cast, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    DiscoveryOrigin,
    DiscoveryOutput,
    DiscoveryRequest,
    FactKind,
    FailureCode,
    SourceType,
    SupportedCity,
)
from app.agents.discovery.errors import DiscoveryExecutionError
from app.agents.discovery.executor import DiscoveryExecutor
from app.agents.discovery.evidence import (
    assemble_discovery_output_for_fact_kinds,
)
from app.agents.discovery.menu import (
    MenuErrorCode,
    MenuReaderError,
    PoiMenuReader,
)
from app.agents.discovery.models import (
    DiscoveryRegistrySnapshot,
    PoiToolCandidate,
    PoiToolResult,
    ToolCoordinates,
    ToolSource,
)
from app.db.models import Poi, PoiSource, Source
from app.itinerary_generation.contracts import ItineraryDraftGenerationRequest
from app.providers.poi.models import PoiProviderKind

_PROVIDER = PoiProviderKind.CURATED
_GEOMETRY_POINT = Geometry(
    geometry_type="POINT",
    srid=4326,
    spatial_index=False,
)
_REQUESTED_FACT_KINDS = tuple(
    sorted(
        {
            FactKind.CATEGORY,
            FactKind.IDENTITY,
            FactKind.LOCATION,
            FactKind.MENU_ITEM,
            FactKind.OPENING_HOURS,
            FactKind.PRICE,
            FactKind.RATING,
        },
        key=lambda item: item.value,
    )
)


class CandidateResolutionErrorCode(StrEnum):
    """Stable application-level candidate resolution failures."""

    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_OUTPUT = "invalid_output"


class CandidateResolutionError(Exception):
    """Sanitized failure from a curated candidate boundary."""

    __slots__ = ("code", "retryable")

    def __init__(
        self,
        code: CandidateResolutionErrorCode,
        *,
        retryable: bool,
    ) -> None:
        self.code = code
        self.retryable = retryable
        super().__init__(code.value)


class CityCandidateReaderPolicy(BaseModel):
    """Bounded timeout for one city-only curated read."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    timeout_seconds: Annotated[
        float,
        Field(strict=True, gt=0, le=60, allow_inf_nan=False),
    ] = 5.0


@runtime_checkable
class CuratedCityCandidateReader(Protocol):
    """Read bounded canonical curated candidates without an origin."""

    async def read(
        self,
        city: SupportedCity,
        limit: int,
    ) -> PoiToolResult:
        """Return stable POI-ID ordered candidates with absent distances."""
        ...


class SqlAlchemyCuratedCityCandidateReader:
    """One injected-session read over canonical POI/source rows only."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        policy: CityCandidateReaderPolicy | None = None,
    ) -> None:
        self._session = session
        self._policy = policy or CityCandidateReaderPolicy()

    async def read(
        self,
        city: SupportedCity,
        limit: int,
    ) -> PoiToolResult:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit not in range(1, 21)
        ):
            raise CandidateResolutionError(
                CandidateResolutionErrorCode.INVALID_OUTPUT,
                retryable=False,
            )
        try:
            async with asyncio.timeout(self._policy.timeout_seconds):
                return await self._read(city, limit)
        except TimeoutError:
            raise CandidateResolutionError(
                CandidateResolutionErrorCode.TIMEOUT,
                retryable=True,
            ) from None
        except asyncio.CancelledError:
            raise
        except CandidateResolutionError:
            raise
        except SQLAlchemyError:
            raise CandidateResolutionError(
                CandidateResolutionErrorCode.UNAVAILABLE,
                retryable=True,
            ) from None
        except Exception:
            raise CandidateResolutionError(
                CandidateResolutionErrorCode.INVALID_OUTPUT,
                retryable=False,
            ) from None

    async def _read(
        self,
        city: SupportedCity,
        limit: int,
    ) -> PoiToolResult:
        poi_geometry = sql_cast(Poi.location, _GEOMETRY_POINT)
        candidates = (
            select(
                Poi.id.label("provider_id"),
                Poi.canonical_name,
                Poi.city,
                Poi.category,
                Poi.address,
                func.ST_Y(poi_geometry).label("latitude"),
                func.ST_X(poi_geometry).label("longitude"),
            )
            .where(Poi.city == city.value)
            .order_by(Poi.id)
            .limit(limit + 1)
            .cte("itinerary_city_candidates")
        )
        statement = (
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
            .order_by(candidates.c.provider_id, Source.id)
        )
        rows = cast(
            Sequence[Mapping[str, object]],
            (await self._session.execute(statement)).mappings().all(),
        )
        return _normalize_city_rows(rows, limit)


class ResolvedItineraryCandidates(BaseModel):
    """Strict resolved candidate/evidence result consumed by generation."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    discovery: DiscoveryOutput


@runtime_checkable
class ItineraryCandidateResolver(Protocol):
    """Resolve request-scoped candidates and evidence from approved sources."""

    async def resolve(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ResolvedItineraryCandidates:
        """Return candidates in canonical provider/reader order."""
        ...


class DefaultItineraryCandidateResolver:
    """Use nearby Discovery with origin or deterministic curated city reads."""

    def __init__(
        self,
        discovery: DiscoveryExecutor,
        city_reader: CuratedCityCandidateReader,
        menu_reader: PoiMenuReader,
    ) -> None:
        self._discovery = discovery
        self._city_reader = city_reader
        self._menu_reader = menu_reader

    async def resolve(
        self,
        request: ItineraryDraftGenerationRequest,
    ) -> ResolvedItineraryCandidates:
        if request.latitude is not None and request.longitude is not None:
            try:
                output = await self._discovery.discover(
                    DiscoveryRequest(
                        city=request.city,
                        origin=DiscoveryOrigin(
                            latitude=request.latitude,
                            longitude=request.longitude,
                        ),
                        radius_metres=5_000,
                        limit=request.maximum_stops,
                        query=None,
                        category=None,
                        requested_fact_kinds=_REQUESTED_FACT_KINDS,
                    )
                )
            except asyncio.CancelledError:
                raise
            except DiscoveryExecutionError as error:
                raise CandidateResolutionError(
                    CandidateResolutionErrorCode.UNAVAILABLE,
                    retryable=error.failure.retryable,
                ) from None
            return ResolvedItineraryCandidates(discovery=output)

        poi_result = await self._city_reader.read(
            request.city,
            request.maximum_stops,
        )
        failures: tuple[AgentFailure, ...] = ()
        menu_result = None
        selected_ids = tuple(item.provider_id for item in poi_result.items)
        if selected_ids:
            try:
                menu_result = await self._menu_reader.read_menu_items(selected_ids)
            except asyncio.CancelledError:
                raise
            except MenuReaderError as error:
                failures = (_menu_failure(error.code),)
        output = assemble_discovery_output_for_fact_kinds(
            _REQUESTED_FACT_KINDS,
            DiscoveryRegistrySnapshot(
                poi_result=poi_result,
                menu_result=menu_result,
                failures=failures,
            ),
        )
        return ResolvedItineraryCandidates(discovery=output)


def _normalize_city_rows(
    rows: Sequence[Mapping[str, object]],
    limit: int,
) -> PoiToolResult:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        provider_id = _required_str(row["provider_id"])
        grouped.setdefault(provider_id, []).append(row)
    candidate_ids = tuple(grouped)
    is_complete = len(candidate_ids) <= limit
    items = tuple(
        _normalize_city_candidate(grouped[provider_id])
        for provider_id in candidate_ids[:limit]
    )
    freshness_at = max(
        (item.retrieved_at for item in items if item.retrieved_at is not None),
        default=None,
    )
    try:
        return PoiToolResult(
            provider=_PROVIDER,
            items=items,
            returned_count=len(items),
            is_complete=is_complete,
            freshness_at=freshness_at,
        )
    except (TypeError, ValueError, ValidationError):
        raise CandidateResolutionError(
            CandidateResolutionErrorCode.INVALID_OUTPUT,
            retryable=False,
        ) from None


def _normalize_city_candidate(
    rows: Sequence[Mapping[str, object]],
) -> PoiToolCandidate:
    first = rows[0]
    sources: dict[str, ToolSource] = {}
    for row in rows:
        if row["source_id"] is None:
            continue
        source_url = _optional_str(row["source_url"])
        source = ToolSource(
            source_id=_required_str(row["source_id"]),
            source_type=SourceType(_required_str(row["source_type"])),
            label=_required_str(row["source_label"]),
            publisher=_optional_str(row["publisher"]),
            url=HttpUrl(source_url) if source_url is not None else None,
            published_at=_datetime_or_none(row["published_at"]),
            retrieved_at=_datetime_or_none(row["source_retrieved_at"]),
        )
        existing = sources.setdefault(source.source_id, source)
        if existing != source:
            raise ValueError("Conflicting canonical source identity.")
    ordered_sources = tuple(sources[source_id] for source_id in sorted(sources))
    retrieved_at = max(
        (
            source.retrieved_at
            for source in ordered_sources
            if source.retrieved_at is not None
        ),
        default=None,
    )
    provider_id = _required_str(first["provider_id"])
    return PoiToolCandidate(
        id=f"{_PROVIDER.value}:{provider_id}",
        provider=_PROVIDER,
        provider_id=provider_id,
        canonical_name=_required_str(first["canonical_name"]),
        city=SupportedCity(_required_str(first["city"])),
        category=_required_str(first["category"]),
        address=_optional_str(first["address"]),
        coordinates=ToolCoordinates(
            latitude=_required_float(first["latitude"]),
            longitude=_required_float(first["longitude"]),
        ),
        distance_metres=None,
        sources=ordered_sources,
        retrieved_at=retrieved_at,
        is_curated=True,
        is_externally_supplied=False,
    )


def _menu_failure(code: MenuErrorCode) -> AgentFailure:
    if code is MenuErrorCode.TIMEOUT:
        return AgentFailure(
            stage=AgentKind.DISCOVERY,
            code=FailureCode.PROVIDER_TIMEOUT,
            message="Menu data could not be retrieved in time.",
            retryable=True,
        )
    if code is MenuErrorCode.INVALID_OUTPUT:
        return AgentFailure(
            stage=AgentKind.DISCOVERY,
            code=FailureCode.INVALID_OUTPUT,
            message="Menu data could not be validated.",
            retryable=False,
        )
    return AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PROVIDER_UNAVAILABLE,
        message="Menu data is temporarily unavailable.",
        retryable=True,
    )


def _required_str(value: object) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("Expected string.")


def _optional_str(value: object) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise TypeError("Expected optional string.")


def _required_float(value: object) -> float:
    if isinstance(value, float):
        return value
    raise TypeError("Expected float.")


def _datetime_or_none(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    raise TypeError("Expected optional datetime.")
