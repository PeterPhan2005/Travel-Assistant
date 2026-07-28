"""Service selecting configured grounding execution or pure review."""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from collections.abc import Callable

from app.agents.contracts import (
    GroundingReviewOutput,
    GroundingReviewRequest,
)
from app.agents.grounding.executor import (
    GroundingReviewerExecutor,
    OpenAIGroundingReviewerExecutor,
)
from app.agents.grounding.reviewer import build_deterministic_review
from app.agents.grounding.validation import (
    validate_grounding_review_output,
)

logger = logging.getLogger("travel_assistant.agents.grounding")

GroundingReviewerExecutorFactory = Callable[
    [],
    GroundingReviewerExecutor | None,
]


class GroundingReviewerService:
    """Return one closed review with deterministic safety as the baseline."""

    def __init__(
        self,
        executor_factory: GroundingReviewerExecutorFactory | None = None,
    ) -> None:
        self._executor_factory = (
            executor_factory
            if executor_factory is not None
            else OpenAIGroundingReviewerExecutor.from_environment
        )

    async def review(
        self,
        request: GroundingReviewRequest,
    ) -> GroundingReviewOutput:
        """Use one configured execution without weakening deterministic rules."""
        deterministic = build_deterministic_review(request)
        try:
            executor = self._executor_factory()
        except Exception:
            self._log_result("deterministic", deterministic)
            return deterministic
        if executor is None:
            self._log_result("deterministic", deterministic)
            return deterministic
        try:
            candidate = await executor.review(request)
            if not isinstance(candidate, GroundingReviewOutput):
                raise TypeError("Grounding executor returned an invalid type.")
            output = validate_grounding_review_output(
                candidate,
                request,
                deterministic,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            output = deterministic
            path = "deterministic"
        else:
            path = "model"
        self._log_result(path, output)
        return output

    @staticmethod
    def _log_result(
        path: str,
        output: GroundingReviewOutput,
    ) -> None:
        reason_counts = Counter(
            rejection.reason.value for rejection in output.rejected_claims
        )
        reason_summary = ",".join(
            f"{reason}:{reason_counts[reason]}"
            for reason in sorted(reason_counts)
        ) or "none"
        logger.info(
            "operation=review path=%s status=%s approved=%d rejected=%d "
            "reasons=%s",
            path,
            output.status.value,
            len(output.approved_claim_ids),
            len(output.rejected_claims),
            reason_summary,
        )
