"""Router service selecting one configured model run or pure fallback."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.agents.contracts import RouterOutput, RouterRequest
from app.agents.router.executor import OpenAIRouterExecutor, RouterExecutor
from app.agents.router.fallback import match_router_fallback

logger = logging.getLogger("travel_assistant.agents.router")

RouterExecutorFactory = Callable[[], RouterExecutor | None]


class RouterService:
    """Return a validated RouterOutput while sanitizing model-path failures."""

    def __init__(
        self,
        executor_factory: RouterExecutorFactory | None = None,
    ) -> None:
        self._executor_factory = (
            executor_factory
            if executor_factory is not None
            else OpenAIRouterExecutor.from_environment
        )

    async def route(self, request: RouterRequest) -> RouterOutput:
        """Use one model execution when configured, otherwise fall back."""
        try:
            executor = self._executor_factory()
        except Exception:
            return self._fallback(request, reason="configuration_failure")

        if executor is None:
            return self._fallback(request, reason="not_configured")

        try:
            output = await executor.route(request)
            validated = RouterOutput.model_validate(
                output.model_dump(mode="python")
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._fallback(request, reason="model_failure")

        logger.info(
            "operation=route path=model reason=success intent=%s",
            validated.primary_intent.value,
        )
        return validated

    @staticmethod
    def _fallback(
        request: RouterRequest,
        *,
        reason: str,
    ) -> RouterOutput:
        output = match_router_fallback(request)
        logger.info(
            "operation=route path=fallback reason=%s intent=%s",
            reason,
            output.primary_intent.value,
        )
        return output
