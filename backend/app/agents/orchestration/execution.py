"""Bounded retry and timeout execution for one isolated service call."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    ContractModel,
    FailureCode,
)
from app.agents.discovery.errors import DiscoveryExecutionError
from app.agents.itinerary.errors import ItineraryExecutionError
from app.agents.observability.context import observation_attempt
from app.agents.observability.sdk import sdk_attempt_span

MAX_DURATION_MS = 3_600_000.0

_TIMEOUT_MESSAGE = "Công đoạn xử lý đã vượt quá thời hạn cho phép."
_BUDGET_MESSAGE = "Yêu cầu đã vượt quá tổng thời gian xử lý cho phép."
_FAILED_MESSAGE = "Công đoạn xử lý không thể hoàn tất an toàn."
_INVALID_OUTPUT_MESSAGE = "Kết quả công đoạn không đáp ứng định dạng an toàn."

OutputT = TypeVar("OutputT", bound=ContractModel)
MonotonicClock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class StageExecution(Generic[OutputT]):
    """Internal completed attempt summary without exception or task objects."""

    output: OutputT | None
    failure: AgentFailure | None
    duration_ms: float
    attempt_count: int


async def execute_stage(
    *,
    agent: AgentKind,
    invoke: Callable[[], Awaitable[OutputT]],
    output_type: type[OutputT],
    validate: Callable[[OutputT], OutputT],
    timeout_seconds: float,
    maximum_attempts: int,
    deadline: float,
    clock: MonotonicClock,
) -> StageExecution[OutputT]:
    """Call one typed service with at most one eligible fresh retry."""
    started = _read_clock(clock)
    attempt = 0
    final_failure: AgentFailure | None = None
    while attempt < maximum_attempts:
        remaining = deadline - _read_clock(clock)
        if remaining <= 0:
            final_failure = latency_budget_failure(agent)
            break
        attempt += 1
        deadline_limited = remaining <= timeout_seconds
        attempt_timeout = min(timeout_seconds, remaining)
        try:
            with observation_attempt(agent, attempt):
                with sdk_attempt_span(agent, attempt):
                    async with asyncio.timeout(attempt_timeout):
                        candidate = await invoke()
            if _read_clock(clock) > deadline:
                final_failure = latency_budget_failure(agent)
                break
            if not isinstance(candidate, output_type):
                raise TypeError("Typed service returned an invalid output.")
            output = validate(candidate)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            final_failure = (
                latency_budget_failure(agent)
                if deadline_limited
                else AgentFailure(
                    stage=agent,
                    code=FailureCode.SPECIALIST_TIMEOUT,
                    message=_TIMEOUT_MESSAGE,
                    retryable=True,
                )
            )
        except (DiscoveryExecutionError, ItineraryExecutionError) as error:
            final_failure = _typed_failure(agent, error.failure)
        except (TypeError, ValueError):
            final_failure = AgentFailure(
                stage=agent,
                code=FailureCode.INVALID_OUTPUT,
                message=_INVALID_OUTPUT_MESSAGE,
                retryable=False,
            )
        except Exception:
            final_failure = AgentFailure(
                stage=agent,
                code=FailureCode.SPECIALIST_FAILED,
                message=_FAILED_MESSAGE,
                retryable=False,
            )
        else:
            return StageExecution(
                output=output,
                failure=None,
                duration_ms=_duration_ms(started, clock),
                attempt_count=attempt,
            )

        if (
            final_failure is None
            or not final_failure.retryable
            or attempt >= maximum_attempts
            or deadline - _read_clock(clock) < timeout_seconds
        ):
            break

    return StageExecution(
        output=None,
        failure=final_failure or latency_budget_failure(agent),
        duration_ms=_duration_ms(started, clock),
        attempt_count=attempt,
    )


def mapping_failure(
    agent: AgentKind,
    *,
    code: FailureCode = FailureCode.INVALID_INPUT,
) -> AgentFailure:
    """Return one fixed non-retryable failure for impossible request mapping."""
    return AgentFailure(
        stage=agent,
        code=code,
        message=_FAILED_MESSAGE,
        retryable=False,
    )


def latency_budget_failure(agent: AgentKind) -> AgentFailure:
    """Return the fixed overall-deadline failure for a planned stage."""
    return AgentFailure(
        stage=agent,
        code=FailureCode.LATENCY_BUDGET_EXCEEDED,
        message=_BUDGET_MESSAGE,
        retryable=False,
    )


def _typed_failure(
    agent: AgentKind,
    failure: AgentFailure,
) -> AgentFailure:
    if failure.stage is agent:
        return AgentFailure.model_validate(
            failure.model_dump(mode="python")
        )
    return AgentFailure(
        stage=agent,
        code=FailureCode.SPECIALIST_FAILED,
        message=_FAILED_MESSAGE,
        retryable=False,
    )


def _read_clock(clock: MonotonicClock) -> float:
    value = clock()
    if not math.isfinite(value):
        raise ValueError("Monotonic clock must be finite.")
    return value


def _duration_ms(started: float, clock: MonotonicClock) -> float:
    elapsed = _read_clock(clock) - started
    if elapsed < 0 or not math.isfinite(elapsed):
        raise ValueError("Monotonic clock moved backwards.")
    return min(elapsed * 1_000.0, MAX_DURATION_MS)
