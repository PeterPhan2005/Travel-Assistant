"""Service selecting configured Local Culture execution or safe fallback."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.agents.contracts import (
    AnswerStatus,
    LocalCultureOutput,
    LocalCultureRequest,
)
from app.agents.local_culture.executor import (
    LocalCultureExecutor,
    OpenAILocalCultureExecutor,
)
from app.agents.local_culture.fallback import (
    LocalCultureLimitationReason,
    build_limited_local_culture,
    limitation_reason_code,
)
from app.agents.local_culture.validation import (
    UnsafeLocalCultureOutputError,
    has_sufficient_evidence,
    validate_local_culture_output,
)

logger = logging.getLogger("travel_assistant.agents.local_culture")

LocalCultureExecutorFactory = Callable[[], LocalCultureExecutor | None]


class LocalCultureService:
    """Return only source-closed respectful guidance or a limited result."""

    def __init__(
        self,
        executor_factory: LocalCultureExecutorFactory | None = None,
    ) -> None:
        self._executor_factory = (
            executor_factory
            if executor_factory is not None
            else OpenAILocalCultureExecutor.from_environment
        )

    async def advise(
        self,
        request: LocalCultureRequest,
    ) -> LocalCultureOutput:
        """Attempt one configured run only with usable approved evidence."""
        if not has_sufficient_evidence(request):
            output = build_limited_local_culture(
                request,
                LocalCultureLimitationReason.INSUFFICIENT_EVIDENCE,
            )
            self._log_result("fallback", output)
            return output

        try:
            executor = self._executor_factory()
        except Exception:
            output = build_limited_local_culture(
                request,
                LocalCultureLimitationReason.MODEL_UNAVAILABLE,
            )
            self._log_result("fallback", output)
            return output

        if executor is None:
            output = build_limited_local_culture(
                request,
                LocalCultureLimitationReason.MODEL_UNCONFIGURED,
            )
            self._log_result("fallback", output)
            return output

        try:
            candidate = await executor.advise(request)
            if not isinstance(candidate, LocalCultureOutput):
                raise TypeError(
                    "Local Culture executor returned an invalid type."
                )
            output = validate_local_culture_output(candidate, request)
        except asyncio.CancelledError:
            raise
        except UnsafeLocalCultureOutputError:
            output = build_limited_local_culture(
                request,
                LocalCultureLimitationReason.UNSAFE_GENERALIZATION,
            )
        except Exception:
            output = build_limited_local_culture(
                request,
                LocalCultureLimitationReason.INVALID_MODEL_OUTPUT,
            )

        self._log_result("model", output)
        return output

    @staticmethod
    def _log_result(path: str, output: LocalCultureOutput) -> None:
        reason = (
            "none"
            if output.status is AnswerStatus.COMPLETE
            else limitation_reason_code(output)
        )
        logger.info(
            "operation=advise path=%s status=%s reason=%s items=%d",
            path,
            output.status.value,
            reason,
            len(output.guidance),
        )
