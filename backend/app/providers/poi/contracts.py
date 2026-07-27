"""Structural POI provider boundary consumed by later application services."""

from typing import Protocol, runtime_checkable

from app.providers.poi.models import PoiDiscoveryRequest, PoiResultEnvelope


@runtime_checkable
class PoiProvider(Protocol):
    """Discover normalized POIs without exposing adapter implementation types."""

    async def discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        """Return bounded nearby results or raise ``PoiProviderError``."""
        ...
