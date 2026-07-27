"""Nearby normalized POI HTTP API."""

from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    HttpUrl,
    ValidationError,
)

from app.auth.dependencies import FirebaseAuthentication
from app.auth.models import AuthenticatedPrincipal
from app.providers.poi.contracts import PoiProvider
from app.providers.poi.errors import PoiProviderError, ProviderErrorCode
from app.providers.poi.models import (
    Coordinates,
    PoiDiscoveryRequest,
    PoiDiscoveryResult,
    PoiProviderKind,
    PoiResultEnvelope,
    PriceLevel,
    SourceReference,
    SupportedCity,
)

DEFAULT_RADIUS_METRES = 5_000
DEFAULT_LIMIT = 5

ProviderDependency = Callable[[], AsyncIterator[PoiProvider]]


class NearbySourceResponse(BaseModel):
    """Typed safe provenance exposed by the nearby API."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    source_type: str
    label: str
    publisher: str | None = None
    url: HttpUrl | None = None
    published_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime | None = None

    @classmethod
    def from_provider(
        cls,
        source: SourceReference,
    ) -> "NearbySourceResponse":
        return cls.model_validate(source.model_dump())


class NearbyPoiResponse(BaseModel):
    """Normalized destination POI with no request-origin or raw payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    provider: PoiProviderKind
    provider_id: str
    canonical_name: str
    city: SupportedCity
    category: str
    address: str | None = None
    coordinates: Coordinates
    distance_metres: float | None = None
    rating: Decimal | None = None
    rating_count: int | None = None
    price_level: PriceLevel | None = None
    opening_hours_summary: str | None = None
    sources: tuple[NearbySourceResponse, ...] = ()
    retrieved_at: AwareDatetime | None = None
    is_curated: bool
    is_externally_supplied: bool

    @classmethod
    def from_provider(
        cls,
        item: PoiDiscoveryResult,
    ) -> "NearbyPoiResponse":
        return cls(
            id=item.id,
            provider=item.provider,
            provider_id=item.provider_id,
            canonical_name=item.canonical_name,
            city=item.city,
            category=item.category,
            address=item.address,
            coordinates=item.coordinates,
            distance_metres=item.distance_metres,
            rating=item.rating,
            rating_count=item.rating_count,
            price_level=item.price_level,
            opening_hours_summary=item.opening_hours_summary,
            sources=tuple(
                NearbySourceResponse.from_provider(source)
                for source in item.sources
            ),
            retrieved_at=item.retrieved_at,
            is_curated=item.is_curated,
            is_externally_supplied=item.is_externally_supplied,
        )


class NearbyPoiEnvelopeResponse(BaseModel):
    """Bounded normalized nearby result envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: PoiProviderKind
    items: tuple[NearbyPoiResponse, ...]
    returned_count: int
    is_complete: bool
    freshness_at: AwareDatetime | None = None

    @classmethod
    def from_provider(
        cls,
        result: PoiResultEnvelope,
    ) -> "NearbyPoiEnvelopeResponse":
        return cls(
            provider=result.provider,
            items=tuple(
                NearbyPoiResponse.from_provider(item)
                for item in result.items
            ),
            returned_count=result.returned_count,
            is_complete=result.is_complete,
            freshness_at=result.freshness_at,
        )


class ProviderHTTPException(HTTPException):
    """Controlled provider failure carrying a stable application code."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code


_PROVIDER_ERROR_HTTP: Mapping[
    ProviderErrorCode,
    tuple[int, str, str],
] = {
    ProviderErrorCode.INVALID_REQUEST: (
        400,
        "poi_provider_invalid_request",
        "The nearby request could not be processed.",
    ),
    ProviderErrorCode.RATE_LIMITED: (
        429,
        "poi_provider_rate_limited",
        "Nearby search is temporarily unavailable.",
    ),
    ProviderErrorCode.TIMEOUT: (
        503,
        "poi_provider_timeout",
        "Nearby search is temporarily unavailable.",
    ),
    ProviderErrorCode.UNAVAILABLE: (
        503,
        "poi_provider_unavailable",
        "Nearby search is temporarily unavailable.",
    ),
    ProviderErrorCode.MISCONFIGURED: (
        503,
        "poi_provider_misconfigured",
        "Nearby search is temporarily unavailable.",
    ),
    ProviderErrorCode.UNSUPPORTED: (
        501,
        "poi_provider_unsupported",
        "Nearby search is not supported.",
    ),
    ProviderErrorCode.INVALID_RESPONSE: (
        502,
        "poi_provider_invalid_response",
        "Nearby search is temporarily unavailable.",
    ),
    ProviderErrorCode.INTERNAL: (
        500,
        "poi_provider_internal",
        "Nearby search could not be completed.",
    ),
}


def create_pois_router(
    provider_dependency: ProviderDependency,
    authentication: FirebaseAuthentication,
) -> APIRouter:
    """Create the canonical nearby router with injected boundaries."""
    router = APIRouter()

    @router.get(
        "/pois/nearby",
        response_model=NearbyPoiEnvelopeResponse,
    )
    async def nearby_pois(
        principal: Annotated[
            AuthenticatedPrincipal | None,
            Depends(authentication.optional),
        ],
        provider: Annotated[
            PoiProvider,
            Depends(provider_dependency),
        ],
        city: str,
        latitude: float,
        longitude: float,
        radius_metres: int = DEFAULT_RADIUS_METRES,
        limit: int = DEFAULT_LIMIT,
        query: str | None = None,
        category: str | None = None,
    ) -> NearbyPoiEnvelopeResponse:
        """Return normalized nearby POIs without persisting the origin."""
        del principal
        request = _provider_request(
            city=city,
            latitude=latitude,
            longitude=longitude,
            radius_metres=radius_metres,
            limit=limit,
            query=query,
            category=category,
        )
        try:
            result = await provider.discover(request)
        except PoiProviderError as error:
            status_code, code, message = _PROVIDER_ERROR_HTTP[
                error.failure.code
            ]
            raise ProviderHTTPException(
                status_code=status_code,
                code=code,
                message=message,
            ) from error
        return NearbyPoiEnvelopeResponse.from_provider(result)

    return router


def _provider_request(
    *,
    city: str,
    latitude: float,
    longitude: float,
    radius_metres: int,
    limit: int,
    query: str | None,
    category: str | None,
) -> PoiDiscoveryRequest:
    try:
        return PoiDiscoveryRequest.model_validate(
            {
                "city": city,
                "origin": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius_metres": radius_metres,
                "limit": limit,
                "query": query,
                "category": category,
            }
        )
    except ValidationError as error:
        raise RequestValidationError(
            _http_validation_errors(error.errors())
        ) from error


def _http_validation_errors(
    errors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for error in errors:
        issue = dict(error)
        location = tuple(issue.get("loc", ()))
        issue["loc"] = ("query", *_http_location(location))
        normalized.append(issue)
    return normalized


def _http_location(location: tuple[object, ...]) -> tuple[object, ...]:
    if location == ("origin", "latitude"):
        return ("latitude",)
    if location == ("origin", "longitude"):
        return ("longitude",)
    if location and location[0] == "origin":
        return location[1:]
    return location
