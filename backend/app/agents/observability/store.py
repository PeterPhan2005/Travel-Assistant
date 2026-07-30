"""Bounded process-local storage for privacy-safe trace records."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Protocol

from app.agents.contracts import AgentKind, RuntimeResultStatus
from app.agents.observability.contracts import (
    AgentRequestTraceQuery,
    AgentTokenUsage,
    AgentTraceRecord,
    AgentUsageByAgent,
    AgentUsageQuery,
    AgentUsageSummary,
    add_token_usage,
)

MAX_STORE_CAPACITY = 10_000


class AgentObservabilityStoreError(RuntimeError):
    """A sanitized local store operation failure."""


class AgentObservabilityConflictError(AgentObservabilityStoreError):
    """A trace ID was reused for a different immutable record."""


class AgentObservabilityStore(Protocol):
    """Async queryable trace storage boundary."""

    async def record(self, record: AgentTraceRecord) -> None:
        """Store one immutable trace record."""
        ...

    async def get_trace(self, trace_id: str) -> AgentTraceRecord | None:
        """Return one trace by exact ID."""
        ...

    async def list_for_request(
        self,
        request_id: str,
        *,
        limit: int,
    ) -> tuple[AgentTraceRecord, ...]:
        """Return a bounded insertion-ordered request trace list."""
        ...

    async def summarize(
        self,
        query: AgentUsageQuery,
    ) -> AgentUsageSummary:
        """Return a deterministic aggregate from stored records."""
        ...


class InMemoryAgentObservabilityStore:
    """Concurrent bounded FIFO operational storage that resets on restart."""

    def __init__(self, *, capacity: int) -> None:
        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, int)
            or capacity < 1
            or capacity > MAX_STORE_CAPACITY
        ):
            raise ValueError("Observability capacity is outside safe bounds.")
        self._capacity = capacity
        self._records: OrderedDict[str, AgentTraceRecord] = OrderedDict()
        self._lock = asyncio.Lock()

    @property
    def capacity(self) -> int:
        """Return the explicit process-local record bound."""
        return self._capacity

    async def record(self, record: AgentTraceRecord) -> None:
        """Insert idempotently and evict the oldest record at capacity."""
        validated = _copy_record(record)
        async with self._lock:
            existing = self._records.get(validated.trace_id)
            if existing is not None:
                if existing == validated:
                    return
                raise AgentObservabilityConflictError(
                    "Trace identifier conflicts with an existing record."
                )
            self._records[validated.trace_id] = validated
            while len(self._records) > self._capacity:
                self._records.popitem(last=False)

    async def get_trace(self, trace_id: str) -> AgentTraceRecord | None:
        """Return a validated immutable copy without changing FIFO order."""
        async with self._lock:
            record = self._records.get(trace_id)
            return None if record is None else _copy_record(record)

    async def list_for_request(
        self,
        request_id: str,
        *,
        limit: int,
    ) -> tuple[AgentTraceRecord, ...]:
        """Return oldest-first records under the strict query limit."""
        query = AgentRequestTraceQuery(
            request_id=request_id,
            limit=limit,
        )
        async with self._lock:
            records = tuple(
                _copy_record(record)
                for record in self._records.values()
                if record.request_id == query.request_id
            )[: query.limit]
        return records

    async def summarize(
        self,
        query: AgentUsageQuery,
    ) -> AgentUsageSummary:
        """Aggregate one bounded immutable request snapshot."""
        validated_query = AgentUsageQuery.model_validate(
            query.model_dump(mode="python")
        )
        records = await self.list_for_request(
            validated_query.request_id,
            limit=validated_query.limit,
        )
        return _summarize(records, validated_query)


def _copy_record(record: AgentTraceRecord) -> AgentTraceRecord:
    try:
        return AgentTraceRecord.model_validate(
            record.model_dump(mode="python")
        )
    except (TypeError, ValueError):
        sanitized = AgentObservabilityStoreError(
            "Trace record validation failed."
        )
    raise sanitized from None


def _summarize(
    records: tuple[AgentTraceRecord, ...],
    query: AgentUsageQuery,
) -> AgentUsageSummary:
    matching_records: list[AgentTraceRecord] = []
    stage_groups: dict[AgentKind, list[AgentTokenUsage]] = {}
    for record in records:
        matching_stages = tuple(
            stage
            for stage in record.stages
            if query.agent is None or stage.agent is query.agent
        )
        if not matching_stages:
            continue
        matching_records.append(record)
        for stage in matching_stages:
            stage_groups.setdefault(stage.agent, []).append(stage.usage)

    per_agent: list[AgentUsageByAgent] = []
    total = AgentTokenUsage()
    stage_count = 0
    aggregate_error: AgentObservabilityStoreError | None = None
    try:
        for agent in AgentKind:
            usages = stage_groups.get(agent)
            if not usages:
                continue
            agent_usage = AgentTokenUsage()
            for usage in usages:
                agent_usage = add_token_usage(agent_usage, usage)
            stage_count += len(usages)
            total = add_token_usage(total, agent_usage)
            per_agent.append(
                AgentUsageByAgent(
                    agent=agent,
                    stage_count=len(usages),
                    usage=agent_usage,
                )
            )
    except (TypeError, ValueError):
        aggregate_error = AgentObservabilityStoreError(
            "Usage aggregate exceeds safe bounds."
        )
    if aggregate_error is not None:
        raise aggregate_error from None

    success_count = sum(
        record.runtime_status is RuntimeResultStatus.SUCCESS
        for record in matching_records
    )
    partial_count = sum(
        record.runtime_status is RuntimeResultStatus.PARTIAL
        for record in matching_records
    )
    failed_count = sum(
        record.runtime_status is RuntimeResultStatus.FAILED
        for record in matching_records
    )
    try:
        return AgentUsageSummary(
            request_id=query.request_id,
            trace_count=len(matching_records),
            stage_count=stage_count,
            model_request_count=total.requests,
            input_tokens=total.input_tokens,
            output_tokens=total.output_tokens,
            total_tokens=total.total_tokens,
            cached_input_tokens=total.cached_input_tokens,
            reasoning_tokens=total.reasoning_tokens,
            success_trace_count=success_count,
            partial_trace_count=partial_count,
            failed_trace_count=failed_count,
            per_agent=tuple(per_agent),
        )
    except (TypeError, ValueError):
        sanitized_summary = AgentObservabilityStoreError(
            "Usage summary validation failed."
        )
    raise sanitized_summary from None
