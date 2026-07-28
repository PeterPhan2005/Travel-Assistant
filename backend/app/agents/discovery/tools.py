"""Run-local normalized POI/menu tools with sanitized failure registries."""

from __future__ import annotations

import asyncio

from pydantic import ValidationError

from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    DiscoveryRequest,
    FactKind,
    FailureCode,
    SourceType,
)
from app.agents.discovery.menu import (
    MenuErrorCode,
    MenuReaderError,
    PoiMenuReader,
)
from app.agents.discovery.models import (
    DiscoveryRegistrySnapshot,
    MenuResultEnvelope,
    MenuToolResponse,
    PoiToolCandidate,
    PoiToolResponse,
    PoiToolResult,
    ToolCoordinates,
    ToolSource,
)
from app.providers.poi.contracts import PoiProvider
from app.providers.poi.errors import PoiProviderError, ProviderErrorCode
from app.providers.poi.models import (
    PoiDiscoveryRequest,
    PoiDiscoveryResult,
    PoiProviderKind,
    PoiResultEnvelope,
    SourceReference,
)

_MENU_FACT_KINDS = frozenset({FactKind.MENU_ITEM, FactKind.PRICE})


class ToolInvocationError(Exception):
    """A model attempted a repeated or unauthorized normalized tool call."""


class DiscoveryRunRegistry:
    """Mutable state owned by exactly one discovery execution."""

    def __init__(
        self,
        request: DiscoveryRequest,
        provider: PoiProvider,
        menu_reader: PoiMenuReader,
    ) -> None:
        self.request = request
        self._provider = provider
        self._menu_reader = menu_reader
        self._poi_attempted = False
        self._menu_attempted = False
        self._poi_result: PoiToolResult | None = None
        self._menu_result: MenuResultEnvelope | None = None
        self._failures: list[AgentFailure] = []

    @property
    def poi_attempted(self) -> bool:
        """Whether this run already made its sole normalized POI call."""
        return self._poi_attempted

    @property
    def menu_attempted(self) -> bool:
        """Whether this run already made its optional normalized menu call."""
        return self._menu_attempted

    @property
    def menu_required(self) -> bool:
        """Whether requested fact kinds require selected curated menus."""
        return bool(
            _MENU_FACT_KINDS.intersection(self.request.requested_fact_kinds)
        )

    @property
    def selected_curated_provider_ids(self) -> tuple[str, ...]:
        """Return identities only from this run's validated curated results."""
        if self._poi_result is None:
            return ()
        return tuple(
            item.provider_id
            for item in self._poi_result.items
            if item.provider is PoiProviderKind.CURATED and item.is_curated
        )

    async def search_pois(self) -> PoiToolResponse:
        """Call the injected T032 provider exactly once."""
        if self._poi_attempted:
            raise ToolInvocationError("Normalized POI tool may run only once.")
        self._poi_attempted = True
        provider_request = discovery_to_provider_request(self.request)
        try:
            envelope = await self._provider.discover(provider_request)
            self._poi_result = _normalize_poi_envelope(envelope)
        except asyncio.CancelledError:
            raise
        except PoiProviderError as error:
            failure = _provider_failure(error.failure.code)
            self._append_failure(failure)
            return PoiToolResponse(failure=failure)
        except (AttributeError, TypeError, ValueError, ValidationError):
            failure = _invalid_poi_output_failure()
            self._append_failure(failure)
            return PoiToolResponse(failure=failure)
        except Exception:
            failure = _unavailable_poi_failure()
            self._append_failure(failure)
            return PoiToolResponse(failure=failure)
        return PoiToolResponse(result=self._poi_result)

    async def read_menus(self) -> MenuToolResponse:
        """Read selected curated menus at most once without model identities."""
        if self._menu_attempted:
            raise ToolInvocationError("Normalized menu tool may run only once.")
        if not self.menu_required:
            raise ToolInvocationError("Normalized menu tool is not requested.")
        selected_ids = self.selected_curated_provider_ids
        if not selected_ids:
            raise ToolInvocationError(
                "Normalized menu tool requires selected curated candidates."
            )
        self._menu_attempted = True
        try:
            result = await self._menu_reader.read_menu_items(selected_ids)
            validated_result = MenuResultEnvelope.model_validate(
                result.model_dump(mode="python")
            )
            if any(
                item.poi_provider_id not in selected_ids
                for item in validated_result.items
            ):
                raise ValueError("Menu result contains an unselected POI.")
            poi_result = self._poi_result
            if poi_result is None:
                raise ValueError("Menu result requires POI result.")
            poi_sources = {
                source.source_id: source
                for candidate in poi_result.items
                for source in candidate.sources
            }
            for item in validated_result.items:
                existing = poi_sources.get(item.source.source_id)
                if existing is not None and existing != item.source:
                    raise ValueError("Menu source conflicts with POI source.")
            self._menu_result = validated_result
        except asyncio.CancelledError:
            raise
        except MenuReaderError as error:
            failure = _menu_failure(error.code)
            self._append_failure(failure)
            return MenuToolResponse(failure=failure)
        except (AttributeError, TypeError, ValueError, ValidationError):
            failure = _invalid_menu_output_failure()
            self._append_failure(failure)
            return MenuToolResponse(failure=failure)
        except Exception:
            failure = _unavailable_menu_failure()
            self._append_failure(failure)
            return MenuToolResponse(failure=failure)
        return MenuToolResponse(result=self._menu_result)

    async def complete_missing_operations(self) -> None:
        """Run each still-needed deterministic tool no more than once."""
        if not self._poi_attempted:
            await self.search_pois()
        if (
            self._poi_result is not None
            and self.menu_required
            and self.selected_curated_provider_ids
            and not self._menu_attempted
        ):
            await self.read_menus()

    def snapshot(self) -> DiscoveryRegistrySnapshot:
        """Freeze the current registry for pure deterministic assembly."""
        return DiscoveryRegistrySnapshot(
            poi_result=self._poi_result,
            menu_result=self._menu_result,
            failures=tuple(self._failures),
        )

    def _append_failure(self, failure: AgentFailure) -> None:
        if failure not in self._failures:
            self._failures.append(failure)


def discovery_to_provider_request(
    request: DiscoveryRequest,
) -> PoiDiscoveryRequest:
    """Map the validated request to T032 without changing discovery fields."""
    return PoiDiscoveryRequest(
        city=request.city,
        origin=request.origin,
        radius_metres=request.radius_metres,
        limit=request.limit,
        query=request.query,
        category=request.category,
    )


def _normalize_poi_envelope(envelope: PoiResultEnvelope) -> PoiToolResult:
    validated = PoiResultEnvelope.model_validate(
        envelope.model_dump(mode="python")
    )
    items = tuple(_normalize_poi_item(item) for item in validated.items)
    return PoiToolResult(
        provider=validated.provider,
        items=items,
        returned_count=validated.returned_count,
        is_complete=validated.is_complete,
        freshness_at=validated.freshness_at,
    )


def _normalize_poi_item(item: PoiDiscoveryResult) -> PoiToolCandidate:
    return PoiToolCandidate(
        id=item.id,
        provider=item.provider,
        provider_id=item.provider_id,
        canonical_name=item.canonical_name,
        city=item.city,
        category=item.category,
        address=item.address,
        coordinates=ToolCoordinates(
            latitude=item.coordinates.latitude,
            longitude=item.coordinates.longitude,
        ),
        distance_metres=item.distance_metres,
        rating=item.rating,
        rating_count=item.rating_count,
        price_level=item.price_level,
        opening_hours_summary=item.opening_hours_summary,
        sources=tuple(_normalize_source(source) for source in item.sources),
        retrieved_at=item.retrieved_at,
        is_curated=item.is_curated,
        is_externally_supplied=item.is_externally_supplied,
    )


def _normalize_source(source: SourceReference) -> ToolSource:
    return ToolSource(
        source_id=source.source_id,
        source_type=SourceType(source.source_type),
        label=source.label,
        publisher=source.publisher,
        url=source.url,
        published_at=source.published_at,
        retrieved_at=source.retrieved_at,
    )


def _provider_failure(code: ProviderErrorCode) -> AgentFailure:
    if code is ProviderErrorCode.TIMEOUT:
        return AgentFailure(
            stage=AgentKind.DISCOVERY,
            code=FailureCode.PROVIDER_TIMEOUT,
            message="Nearby data could not be retrieved in time.",
            retryable=True,
        )
    if code is ProviderErrorCode.INVALID_RESPONSE:
        return _invalid_poi_output_failure()
    return _unavailable_poi_failure()


def _invalid_poi_output_failure() -> AgentFailure:
    return AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.INVALID_OUTPUT,
        message="Nearby data could not be validated.",
        retryable=False,
    )


def _unavailable_poi_failure() -> AgentFailure:
    return AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PROVIDER_UNAVAILABLE,
        message="Nearby data is temporarily unavailable.",
        retryable=True,
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
        return _invalid_menu_output_failure()
    return _unavailable_menu_failure()


def _invalid_menu_output_failure() -> AgentFailure:
    return AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.INVALID_OUTPUT,
        message="Menu data could not be validated.",
        retryable=False,
    )


def _unavailable_menu_failure() -> AgentFailure:
    return AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PROVIDER_UNAVAILABLE,
        message="Menu data is temporarily unavailable.",
        retryable=True,
    )
