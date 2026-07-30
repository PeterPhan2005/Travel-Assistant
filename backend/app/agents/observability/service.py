"""Injected observation lifecycle and typed query boundary."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from pydantic import Field, SecretStr, StrictBool, model_validator

from app.agents.contracts import AgentRuntimeResult, ContractModel
from app.agents.observability.context import (
    _UsageAccumulator,
    bind_request_observation,
)
from app.agents.observability.contracts import (
    AgentRequestTraceQuery,
    AgentStageObservation,
    AgentTraceQuery,
    AgentTraceRecord,
    AgentUsageQuery,
    AgentUsageSummary,
    sum_token_usage,
)
from app.agents.observability.sdk import (
    finish_workflow_trace,
    generate_trace_id,
    start_workflow_trace,
)
from app.agents.observability.store import (
    AgentObservabilityStore,
)

logger = logging.getLogger("travel_assistant.agents.observability")


class AgentObservabilityPolicy(ContractModel):
    """Explicit SDK export policy; local observation is always available."""

    sdk_trace_export_enabled: StrictBool = False
    tracing_api_key: SecretStr | None = Field(
        default=None,
        repr=False,
    )

    @model_validator(mode="after")
    def validate_export_key(self) -> AgentObservabilityPolicy:
        """Require an explicit nonblank secret only when export is enabled."""
        if self.sdk_trace_export_enabled:
            if (
                self.tracing_api_key is None
                or not self.tracing_api_key.get_secret_value().strip()
            ):
                raise ValueError(
                    "SDK trace export requires an explicit tracing key."
                )
        return self


class AgentObservabilityQueryError(RuntimeError):
    """A sanitized observability query failure."""


@dataclass(slots=True)
class AgentObservationSession:
    """One request-local observation builder with idempotent recording."""

    trace_id: str
    request_id: str
    _accumulator: _UsageAccumulator
    _store: AgentObservabilityStore
    _recorded: AgentTraceRecord | None = None

    async def record_result(
        self,
        result: AgentRuntimeResult,
    ) -> AgentTraceRecord | None:
        """Build and store one privacy-safe record without changing the result."""
        if self._recorded is not None:
            return self._recorded
        try:
            if result.request_id != self.request_id:
                raise ValueError("Runtime request correlation changed.")
            stages = tuple(
                AgentStageObservation(
                    agent=stage.agent,
                    status=stage.status,
                    duration_ms=stage.duration_ms,
                    attempt_count=self._accumulator.attempt_count(stage.agent),
                    usage=self._accumulator.usage_for(stage.agent),
                    failure_code=(
                        stage.failure.code
                        if stage.failure is not None
                        else None
                    ),
                )
                for stage in result.stages
            )
            record = AgentTraceRecord(
                trace_id=self.trace_id,
                request_id=result.request_id,
                runtime_status=result.status,
                stages=stages,
                usage=sum_token_usage(stage.usage for stage in stages),
                warning_count=len(result.warnings),
                failure_count=len(result.failures),
            )
            await self._store.record(record)
            self._recorded = record
            logger.info(
                "operation=agent_observability request_id=%s trace_id=%s "
                "status=%s stages=%d model_requests=%d input_tokens=%d "
                "output_tokens=%d total_tokens=%d warnings=%d failures=%d",
                record.request_id,
                record.trace_id,
                record.runtime_status.value,
                len(record.stages),
                record.usage.requests,
                record.usage.input_tokens,
                record.usage.output_tokens,
                record.usage.total_tokens,
                record.warning_count,
                record.failure_count,
            )
            return record
        except Exception:
            logger.error(
                "operation=agent_observability result=record_failed"
            )
            return None


class AgentObservabilityService:
    """Coordinate local observation, optional export, and typed queries."""

    def __init__(
        self,
        *,
        store: AgentObservabilityStore,
        policy: AgentObservabilityPolicy | None = None,
    ) -> None:
        self._store = store
        self._policy = policy or AgentObservabilityPolicy()

    @asynccontextmanager
    async def observe(
        self,
        request_id: str,
    ) -> AsyncIterator[AgentObservationSession]:
        """Bind one trace identity and reset all state on every exit path."""
        trace_id = generate_trace_id()
        workflow = None
        export_active = False
        if self._policy.sdk_trace_export_enabled:
            try:
                secret = self._policy.tracing_api_key
                workflow = start_workflow_trace(
                    trace_id=trace_id,
                    request_id=request_id,
                    tracing_api_key=(
                        secret.get_secret_value()
                        if secret is not None
                        else None
                    ),
                )
                export_active = True
            except Exception:
                logger.error(
                    "operation=agent_observability "
                    "result=trace_start_failed"
                )

        try:
            with bind_request_observation(
                request_id=request_id,
                trace_id=trace_id,
                sdk_export_enabled=export_active,
            ) as accumulator:
                yield AgentObservationSession(
                    trace_id=trace_id,
                    request_id=request_id,
                    _accumulator=accumulator,
                    _store=self._store,
                )
        finally:
            if workflow is not None:
                try:
                    finish_workflow_trace(workflow)
                except Exception:
                    logger.error(
                        "operation=agent_observability "
                        "result=trace_finish_failed"
                    )

    async def get_trace(
        self,
        query: AgentTraceQuery,
    ) -> AgentTraceRecord | None:
        """Return one exact immutable trace through a typed query."""
        try:
            record = await self._store.get_trace(query.trace_id)
            if record is None:
                return None
            return AgentTraceRecord.model_validate(
                record.model_dump(mode="python")
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            sanitized = AgentObservabilityQueryError(
                "Observability query failed."
            )
        raise sanitized from None

    async def list_for_request(
        self,
        query: AgentRequestTraceQuery,
    ) -> tuple[AgentTraceRecord, ...]:
        """Return bounded traces for one exact request ID."""
        try:
            return await self._store.list_for_request(
                query.request_id,
                limit=query.limit,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            sanitized = AgentObservabilityQueryError(
                "Observability query failed."
            )
        raise sanitized from None

    async def summarize(
        self,
        query: AgentUsageQuery,
    ) -> AgentUsageSummary:
        """Return a deterministic aggregate for one exact request ID."""
        try:
            return await self._store.summarize(query)
        except asyncio.CancelledError:
            raise
        except Exception:
            sanitized = AgentObservabilityQueryError(
                "Observability query failed."
            )
        raise sanitized from None
