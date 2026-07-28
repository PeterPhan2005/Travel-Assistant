"""Narration service selecting configured execution or limited fallback."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.agents.contracts import (
    AnswerStatus,
    NarrationOutput,
    NarrationRequest,
)
from app.agents.narration.executor import (
    NarrationExecutor,
    OpenAINarrationExecutor,
)
from app.agents.narration.fallback import (
    NarrationLimitationReason,
    build_limited_narration,
    limitation_reason_code,
)
from app.agents.narration.validation import (
    has_sufficient_evidence,
    validate_narration_output,
)

logger = logging.getLogger("travel_assistant.agents.narration")

NarrationExecutorFactory = Callable[[], NarrationExecutor | None]


class NarrationService:
    """Return only safe source-grounded narration or a limited result."""

    def __init__(
        self,
        executor_factory: NarrationExecutorFactory | None = None,
    ) -> None:
        self._executor_factory = (
            executor_factory
            if executor_factory is not None
            else OpenAINarrationExecutor.from_environment
        )

    async def narrate(
        self,
        request: NarrationRequest,
    ) -> NarrationOutput:
        """Attempt one configured run only when usable evidence exists."""
        if not has_sufficient_evidence(request):
            output = build_limited_narration(
                request,
                NarrationLimitationReason.INSUFFICIENT_EVIDENCE,
            )
            self._log_result("fallback", output)
            return output

        try:
            executor = self._executor_factory()
        except Exception:
            output = build_limited_narration(
                request,
                NarrationLimitationReason.MODEL_UNAVAILABLE,
            )
            self._log_result("fallback", output)
            return output

        if executor is None:
            output = build_limited_narration(
                request,
                NarrationLimitationReason.MODEL_UNCONFIGURED,
            )
            self._log_result("fallback", output)
            return output

        try:
            candidate = await executor.narrate(request)
            if not isinstance(candidate, NarrationOutput):
                raise TypeError("Narration executor returned an invalid type.")
            output = validate_narration_output(candidate, request)
        except asyncio.CancelledError:
            raise
        except Exception:
            output = build_limited_narration(
                request,
                NarrationLimitationReason.INVALID_MODEL_OUTPUT,
            )

        self._log_result("model", output)
        return output

    @staticmethod
    def _log_result(path: str, output: NarrationOutput) -> None:
        word_count = (
            len(output.narration_text.split())
            if output.status is AnswerStatus.COMPLETE
            and output.narration_text is not None
            else 0
        )
        reason = (
            "none"
            if output.status is AnswerStatus.COMPLETE
            else limitation_reason_code(output)
        )
        logger.info(
            "operation=narrate path=%s status=%s reason=%s words=%d",
            path,
            output.status.value,
            reason,
            word_count,
        )
