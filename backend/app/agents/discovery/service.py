"""Discovery service selecting configured model or deterministic execution."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.agents.contracts import DiscoveryOutput, DiscoveryRequest
from app.agents.discovery.errors import DiscoveryExecutionError
from app.agents.discovery.executor import (
    DeterministicDiscoveryExecutor,
    DiscoveryExecutor,
    OpenAIDiscoveryExecutor,
)
from app.agents.discovery.menu import PoiMenuReader
from app.providers.poi.contracts import PoiProvider

logger = logging.getLogger("travel_assistant.agents.discovery")

DiscoveryExecutorFactory = Callable[
    [PoiProvider, PoiMenuReader],
    DiscoveryExecutor | None,
]


class DiscoveryService:
    """Return only validated discovery data with no final prose."""

    def __init__(
        self,
        provider: PoiProvider,
        menu_reader: PoiMenuReader,
        *,
        executor_factory: DiscoveryExecutorFactory | None = None,
    ) -> None:
        self._provider = provider
        self._menu_reader = menu_reader
        self._executor_factory = (
            executor_factory
            if executor_factory is not None
            else OpenAIDiscoveryExecutor.from_environment
        )

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> DiscoveryOutput:
        """Use one configured execution or deterministic normalized tools."""
        try:
            executor = self._executor_factory(
                self._provider,
                self._menu_reader,
            )
        except Exception:
            executor = None

        if executor is None:
            output = await self._deterministic(request)
            self._log_result("deterministic", request, output)
            return output

        try:
            output = await executor.discover(request)
            validated = DiscoveryOutput.model_validate(
                output.model_dump(mode="python")
            )
        except asyncio.CancelledError:
            raise
        except DiscoveryExecutionError:
            raise
        except Exception:
            validated = await self._deterministic(request)
            self._log_result("deterministic", request, validated)
            return validated

        self._log_result("model", request, validated)
        return validated

    async def _deterministic(
        self,
        request: DiscoveryRequest,
    ) -> DiscoveryOutput:
        executor = DeterministicDiscoveryExecutor(
            self._provider,
            self._menu_reader,
        )
        return await executor.discover(request)

    @staticmethod
    def _log_result(
        path: str,
        request: DiscoveryRequest,
        output: DiscoveryOutput,
    ) -> None:
        failure_code = (
            output.provider_failures[0].code.value
            if output.provider_failures
            else "none"
        )
        logger.info(
            "operation=discover path=%s candidates=%d "
            "completeness=%s failure=%s",
            path,
            len(output.candidates),
            output.completeness.value,
            failure_code,
        )
