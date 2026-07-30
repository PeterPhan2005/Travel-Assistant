"""Strict privacy-safe contracts for agent traces and aggregate usage."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Annotated

from pydantic import AfterValidator, Field, StrictInt, model_validator

from app.agents.contracts import (
    AgentKind,
    ContractModel,
    FailureCode,
    RequestId,
    RuntimeResultStatus,
    StageStatus,
)
from app.agents.contracts.orchestration import DurationMilliseconds

MAX_TOKEN_COUNT = 1_000_000_000_000_000
MAX_OBSERVABILITY_RESULTS = 100
MAX_OBSERVABILITY_STAGES = 7
MAX_OBSERVABILITY_ISSUES = 30

_TRACE_ID_PATTERN = re.compile(r"^trace_[0-9a-f]{32}$")
_STAGE_ORDER = {
    AgentKind.ROUTER: 0,
    AgentKind.DISCOVERY: 1,
    AgentKind.NARRATION: 2,
    AgentKind.LOCAL_CULTURE: 3,
    AgentKind.ITINERARY: 4,
    AgentKind.GROUNDING_REVIEWER: 5,
    AgentKind.RESPONSE_COMPOSER: 6,
}


def _validate_trace_id(value: str) -> str:
    if _TRACE_ID_PATTERN.fullmatch(value) is None:
        raise ValueError("Trace ID must use the Agents SDK trace format.")
    return value


TraceId = Annotated[
    str,
    Field(strict=True, min_length=38, max_length=38),
    AfterValidator(_validate_trace_id),
]
BoundedCount = Annotated[
    StrictInt,
    Field(ge=0, le=MAX_TOKEN_COUNT),
]
QueryLimit = Annotated[
    StrictInt,
    Field(ge=1, le=MAX_OBSERVABILITY_RESULTS),
]


class AgentTokenUsage(ContractModel):
    """Aggregate numeric SDK usage with no provider or response details."""

    requests: BoundedCount = 0
    input_tokens: BoundedCount = 0
    output_tokens: BoundedCount = 0
    total_tokens: BoundedCount = 0
    cached_input_tokens: BoundedCount = 0
    reasoning_tokens: BoundedCount = 0

    @model_validator(mode="after")
    def validate_total(self) -> AgentTokenUsage:
        """Require the SDK's total=input+output invariant."""
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("Total tokens must equal input plus output tokens.")
        return self


class AgentStageObservation(ContractModel):
    """One canonical runtime stage without inputs, outputs, or issue messages."""

    agent: AgentKind
    status: StageStatus
    duration_ms: DurationMilliseconds
    attempt_count: Annotated[StrictInt, Field(ge=0, le=2)]
    usage: AgentTokenUsage = AgentTokenUsage()
    failure_code: FailureCode | None = None

    @model_validator(mode="after")
    def validate_attempt_shape(self) -> AgentStageObservation:
        """Reserve zero attempts for planned stages with no service invocation."""
        if self.attempt_count == 0:
            if (
                self.status is not StageStatus.FAILED
                or self.failure_code is None
                or self.usage != AgentTokenUsage()
            ):
                raise ValueError(
                    "A zero-attempt stage must be a failed zero-usage stage."
                )
        elif self.status is StageStatus.FAILED and self.failure_code is None:
            raise ValueError("A failed attempted stage requires a failure code.")
        if self.status is StageStatus.SUCCESS and self.failure_code is not None:
            raise ValueError("A successful stage cannot have a failure code.")
        return self


class AgentTraceRecord(ContractModel):
    """One bounded local trace correlated with an exact runtime request."""

    trace_id: TraceId
    request_id: RequestId
    runtime_status: RuntimeResultStatus
    stages: Annotated[
        tuple[AgentStageObservation, ...],
        Field(min_length=1, max_length=MAX_OBSERVABILITY_STAGES),
    ]
    usage: AgentTokenUsage
    warning_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_OBSERVABILITY_ISSUES),
    ]
    failure_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_OBSERVABILITY_ISSUES),
    ]

    @model_validator(mode="after")
    def validate_aggregates(self) -> AgentTraceRecord:
        """Require canonical stages and exact aggregate usage."""
        agents = tuple(stage.agent for stage in self.stages)
        expected = tuple(sorted(set(agents), key=_STAGE_ORDER.__getitem__))
        if agents != expected:
            raise ValueError(
                "Stage observations must be unique and in canonical order."
            )
        if self.usage != sum_token_usage(
            stage.usage for stage in self.stages
        ):
            raise ValueError("Trace usage must equal summed stage usage.")
        return self


class AgentTraceQuery(ContractModel):
    """Typed exact trace lookup."""

    trace_id: TraceId


class AgentRequestTraceQuery(ContractModel):
    """Typed bounded request-to-trace lookup."""

    request_id: RequestId
    limit: QueryLimit = MAX_OBSERVABILITY_RESULTS


class AgentUsageQuery(ContractModel):
    """Typed request usage query with an optional canonical agent filter."""

    request_id: RequestId
    agent: AgentKind | None = None
    limit: QueryLimit = MAX_OBSERVABILITY_RESULTS


class AgentUsageByAgent(ContractModel):
    """Aggregate usage and stage count for one canonical agent."""

    agent: AgentKind
    stage_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_OBSERVABILITY_RESULTS),
    ]
    usage: AgentTokenUsage


class AgentUsageSummary(ContractModel):
    """Deterministic aggregate derived only from stored trace records."""

    request_id: RequestId
    trace_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_OBSERVABILITY_RESULTS),
    ]
    stage_count: Annotated[
        StrictInt,
        Field(
            ge=0,
            le=MAX_OBSERVABILITY_RESULTS * MAX_OBSERVABILITY_STAGES,
        ),
    ]
    model_request_count: BoundedCount
    input_tokens: BoundedCount
    output_tokens: BoundedCount
    total_tokens: BoundedCount
    cached_input_tokens: BoundedCount
    reasoning_tokens: BoundedCount
    success_trace_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_OBSERVABILITY_RESULTS),
    ]
    partial_trace_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_OBSERVABILITY_RESULTS),
    ]
    failed_trace_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_OBSERVABILITY_RESULTS),
    ]
    per_agent: Annotated[
        tuple[AgentUsageByAgent, ...],
        Field(max_length=MAX_OBSERVABILITY_STAGES),
    ] = ()

    @model_validator(mode="after")
    def validate_summary(self) -> AgentUsageSummary:
        """Keep redundant query totals internally consistent."""
        if (
            self.success_trace_count
            + self.partial_trace_count
            + self.failed_trace_count
            != self.trace_count
        ):
            raise ValueError("Trace status counts must equal trace count.")
        if self.model_request_count < 0:
            raise ValueError("Model request count must be nonnegative.")
        usage = AgentTokenUsage(
            requests=self.model_request_count,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            cached_input_tokens=self.cached_input_tokens,
            reasoning_tokens=self.reasoning_tokens,
        )
        agents = tuple(item.agent for item in self.per_agent)
        expected_agents = tuple(
            sorted(set(agents), key=_STAGE_ORDER.__getitem__)
        )
        if agents != expected_agents:
            raise ValueError(
                "Per-agent summaries must be unique and canonical."
            )
        if self.stage_count != sum(
            item.stage_count for item in self.per_agent
        ):
            raise ValueError("Stage count must equal per-agent stage counts.")
        if usage != sum_token_usage(
            item.usage for item in self.per_agent
        ):
            raise ValueError("Summary usage must equal per-agent usage.")
        return self


def add_token_usage(
    left: AgentTokenUsage,
    right: AgentTokenUsage,
) -> AgentTokenUsage:
    """Add usage with contract validation and bounded overflow checks."""
    values = {
        field: getattr(left, field) + getattr(right, field)
        for field in AgentTokenUsage.model_fields
    }
    if any(value > MAX_TOKEN_COUNT for value in values.values()):
        raise ValueError("Token usage aggregate exceeds its safe bound.")
    return AgentTokenUsage(**values)


def sum_token_usage(
    usages: Iterable[AgentTokenUsage],
) -> AgentTokenUsage:
    """Sum an iterable of typed usage values from a zero identity."""
    total = AgentTokenUsage()
    for usage in usages:
        total = add_token_usage(total, usage)
    return total
