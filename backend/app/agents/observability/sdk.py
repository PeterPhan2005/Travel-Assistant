"""Pinned OpenAI Agents SDK tracing and usage adaptation."""

from __future__ import annotations

import logging
import secrets
from contextlib import contextmanager
from dataclasses import replace
from typing import Iterator

from agents import RunConfig, custom_span, gen_trace_id, trace
from agents.tracing import Trace, TracingConfig
from agents.usage import Usage
from pydantic import TypeAdapter

from app.agents.contracts import AgentKind
from app.agents.observability.context import (
    capture_usage_for_current_attempt,
    current_observation_identity,
)
from app.agents.observability.contracts import (
    AgentTokenUsage,
    TraceId,
)

WORKFLOW_NAME = "travel_assistant_runtime"
ATTEMPT_SPAN_NAME = "travel_assistant_stage_attempt"

logger = logging.getLogger("travel_assistant.agents.observability")
_TRACE_ID_ADAPTER = TypeAdapter(TraceId)


class AgentUsageAdaptationError(ValueError):
    """SDK usage was not a safe internally consistent numeric value."""


def generate_trace_id() -> TraceId:
    """Generate the installed SDK format, with an equivalent local fallback."""
    try:
        candidate = gen_trace_id()
        return _validate_trace_id(candidate)
    except Exception:
        return _validate_trace_id(f"trace_{secrets.token_hex(16)}")


def start_workflow_trace(
    *,
    trace_id: str,
    request_id: str,
    tracing_api_key: str | None,
) -> Trace:
    """Start one safe application workflow trace as the active SDK trace."""
    tracing: TracingConfig | None = (
        TracingConfig(api_key=tracing_api_key)
        if tracing_api_key is not None
        else None
    )
    workflow = trace(
        workflow_name=WORKFLOW_NAME,
        trace_id=trace_id,
        group_id=request_id,
        metadata={"request_id": request_id},
        tracing=tracing,
        disabled=False,
    )
    try:
        workflow.start(mark_as_current=True)
    except Exception:
        try:
            workflow.finish(reset_current=True)
        except Exception:
            pass
        raise
    return workflow


def finish_workflow_trace(workflow: Trace) -> None:
    """Finish and reset one active SDK workflow trace."""
    workflow.finish(reset_current=True)


@contextmanager
def sdk_attempt_span(agent: AgentKind, attempt: int) -> Iterator[None]:
    """Create one safe parented attempt span when explicit export is active."""
    identity = current_observation_identity()
    if identity is None or not identity.sdk_export_enabled:
        yield
        return
    span = None
    try:
        span = custom_span(
            ATTEMPT_SPAN_NAME,
            data={
                "agent": agent.value,
                "attempt": attempt,
            },
        )
        span.start(mark_as_current=True)
    except Exception:
        if span is not None:
            try:
                span.finish(reset_current=True)
            except Exception:
                pass
        logger.error(
            "operation=agent_observability result=span_start_failed"
        )
        yield
        return
    try:
        yield
    finally:
        try:
            span.finish(reset_current=True)
        except Exception:
            logger.error(
                "operation=agent_observability result=span_finish_failed"
            )


def run_config_for_observation(base: RunConfig) -> RunConfig:
    """Return a fresh per-run config without mutating shared executor state."""
    identity = current_observation_identity()
    if identity is None or not identity.sdk_export_enabled:
        return replace(
            base,
            tracing_disabled=True,
            trace_include_sensitive_data=False,
            trace_id=None,
            group_id=None,
            trace_metadata=None,
        )
    return replace(
        base,
        tracing_disabled=False,
        trace_include_sensitive_data=False,
        workflow_name=WORKFLOW_NAME,
        trace_id=identity.trace_id,
        group_id=identity.request_id,
        trace_metadata={"request_id": identity.request_id},
    )


def token_usage_from_sdk(usage: Usage) -> AgentTokenUsage:
    """Copy only supported aggregate numeric fields from SDK Usage."""
    requests = _safe_int(usage.requests)
    input_tokens = _safe_int(usage.input_tokens)
    output_tokens = _safe_int(usage.output_tokens)
    total_tokens = _safe_int(usage.total_tokens)
    input_details = usage.input_tokens_details
    output_details = usage.output_tokens_details
    cached_input_tokens = (
        0
        if input_details is None
        else _safe_optional_int(
            getattr(input_details, "cached_tokens", None)
        )
    )
    reasoning_tokens = (
        0
        if output_details is None
        else _safe_optional_int(
            getattr(output_details, "reasoning_tokens", None)
        )
    )
    try:
        return AgentTokenUsage(
            requests=requests,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cached_input_tokens=cached_input_tokens,
            reasoning_tokens=reasoning_tokens,
        )
    except (TypeError, ValueError) as error:
        raise AgentUsageAdaptationError(
            "SDK usage is internally inconsistent."
        ) from error


def capture_sdk_result_usage(result: object) -> bool:
    """Capture usage from a successful real Runner result without retaining it."""
    try:
        context_wrapper = getattr(result, "context_wrapper")
        usage = getattr(context_wrapper, "usage")
        if not isinstance(usage, Usage):
            return False
        adapted = token_usage_from_sdk(usage)
        return capture_usage_for_current_attempt(adapted)
    except Exception:
        return False


def _safe_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AgentUsageAdaptationError(
            "SDK usage must contain nonnegative integers."
        )
    return value


def _safe_optional_int(value: object) -> int:
    return 0 if value is None else _safe_int(value)


def _validate_trace_id(value: object) -> TraceId:
    return _TRACE_ID_ADAPTER.validate_python(value)
