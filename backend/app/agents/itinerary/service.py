"""Service selecting configured Itinerary execution or pure planning."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.agents.contracts import ItineraryOutput, ItineraryRequest
from app.agents.itinerary.errors import ItineraryExecutionError
from app.agents.itinerary.executor import (
    ItineraryExecutor,
    OpenAIItineraryExecutor,
)
from app.agents.itinerary.planner import plan_itinerary
from app.agents.itinerary.validation import validate_itinerary_output

logger = logging.getLogger("travel_assistant.agents.itinerary")

ItineraryExecutorFactory = Callable[[], ItineraryExecutor | None]


class ItineraryService:
    """Return one closed draft without persistent itinerary behavior."""

    def __init__(
        self,
        executor_factory: ItineraryExecutorFactory | None = None,
    ) -> None:
        self._executor_factory = (
            executor_factory
            if executor_factory is not None
            else OpenAIItineraryExecutor.from_environment
        )

    async def draft(
        self,
        request: ItineraryRequest,
    ) -> ItineraryOutput:
        """Use one configured execution or deterministic fallback."""
        try:
            fallback = plan_itinerary(request)
        except ItineraryExecutionError as error:
            self._log_failure(request, error)
            raise

        try:
            executor = self._executor_factory()
        except Exception:
            self._log_result(
                "deterministic",
                "configuration_failure",
                request,
                fallback,
            )
            return fallback

        if executor is None:
            self._log_result(
                "deterministic",
                "not_configured",
                request,
                fallback,
            )
            return fallback

        try:
            candidate = await executor.draft(request)
            if not isinstance(candidate, ItineraryOutput):
                raise TypeError("Itinerary executor returned an invalid type.")
            output = validate_itinerary_output(candidate, request)
        except asyncio.CancelledError:
            raise
        except Exception:
            self._log_result(
                "deterministic",
                "model_failure",
                request,
                fallback,
            )
            return fallback

        self._log_result("model", "success", request, output)
        return output

    @staticmethod
    def _log_result(
        path: str,
        reason: str,
        request: ItineraryRequest,
        output: ItineraryOutput,
    ) -> None:
        logger.info(
            "operation=draft path=%s items=%d reason=%s",
            path,
            len(output.items),
            reason,
        )

    @staticmethod
    def _log_failure(
        request: ItineraryRequest,
        error: ItineraryExecutionError,
    ) -> None:
        logger.info(
            "operation=draft path=deterministic items=0 reason=%s",
            error.reason.value,
        )
