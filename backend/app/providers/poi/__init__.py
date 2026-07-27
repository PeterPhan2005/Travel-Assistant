"""Provider-neutral POI discovery contracts and adapters."""

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

__all__ = [
    "Coordinates",
    "CuratedPoiProvider",
    "PoiDiscoveryRequest",
    "PoiDiscoveryResult",
    "PoiProvider",
    "PoiProviderError",
    "PoiProviderKind",
    "PoiResultEnvelope",
    "PriceLevel",
    "ProviderErrorCode",
    "ProviderFailure",
    "ProviderTimeoutPolicy",
    "SourceReference",
    "SupportedCity",
    "build_normalized_poi_id",
]
