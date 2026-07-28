"""Service selecting configured composition or deterministic rendering."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.agents.composer.executor import (
    OpenAIResponseComposerExecutor,
    ResponseComposerExecutor,
)
from app.agents.composer.renderer import build_deterministic_response
from app.agents.composer.validation import (
    validate_response_composer_output,
)
from app.agents.contracts import (
    ResponseComposerOutput,
    ResponseComposerRequest,
)

logger = logging.getLogger("travel_assistant.agents.composer")

ResponseComposerExecutorFactory = Callable[
    [],
    ResponseComposerExecutor | None,
]


class ResponseComposerService:
    """Return one closed response with deterministic rendering as baseline."""

    def __init__(
        self,
        executor_factory: ResponseComposerExecutorFactory | None = None,
    ) -> None:
        self._executor_factory = (
            executor_factory
            if executor_factory is not None
            else OpenAIResponseComposerExecutor.from_environment
        )

    async def compose(
        self,
        request: ResponseComposerRequest,
    ) -> ResponseComposerOutput:
        """Use one configured execution or exact deterministic fallback."""
        deterministic = build_deterministic_response(request)
        try:
            executor = self._executor_factory()
        except Exception:
            self._log_result(
                "deterministic",
                "configuration_failure",
                deterministic,
            )
            return deterministic
        if executor is None:
            self._log_result(
                "deterministic",
                "not_configured",
                deterministic,
            )
            return deterministic
        try:
            candidate = await executor.compose(request)
            if not isinstance(candidate, ResponseComposerOutput):
                raise TypeError("Composer executor returned an invalid type.")
            output = validate_response_composer_output(
                candidate,
                request,
                deterministic,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            self._log_result(
                "deterministic",
                "model_failure",
                deterministic,
            )
            return deterministic
        self._log_result("model", "success", output)
        return output

    @staticmethod
    def _log_result(
        path: str,
        reason: str,
        output: ResponseComposerOutput,
    ) -> None:
        logger.info(
            "operation=compose path=%s poi_items=%d warnings=%d "
            "used_claims=%d reason=%s",
            path,
            len(output.poi_items),
            len(output.warnings),
            len(output.used_claim_ids),
            reason,
        )
