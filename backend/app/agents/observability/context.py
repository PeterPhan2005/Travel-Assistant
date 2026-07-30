"""Request-local correlation, attempt, and usage state."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator

from app.agents.contracts import AgentKind
from app.agents.observability.contracts import (
    AgentTokenUsage,
    add_token_usage,
)


@dataclass(slots=True)
class _UsageAccumulator:
    attempts: dict[AgentKind, set[int]] = field(default_factory=dict)
    usage: dict[AgentKind, AgentTokenUsage] = field(default_factory=dict)

    def begin_attempt(self, agent: AgentKind, attempt: int) -> None:
        if attempt not in {1, 2}:
            raise ValueError("Attempt number must be one or two.")
        self.attempts.setdefault(agent, set()).add(attempt)

    def add(self, agent: AgentKind, usage: AgentTokenUsage) -> None:
        current = self.usage.get(agent, AgentTokenUsage())
        self.usage[agent] = add_token_usage(current, usage)

    def attempt_count(self, agent: AgentKind) -> int:
        return len(self.attempts.get(agent, set()))

    def usage_for(self, agent: AgentKind) -> AgentTokenUsage:
        value = self.usage.get(agent, AgentTokenUsage())
        return AgentTokenUsage.model_validate(value.model_dump(mode="python"))


@dataclass(frozen=True, slots=True)
class _RequestObservation:
    request_id: str
    trace_id: str
    sdk_export_enabled: bool
    accumulator: _UsageAccumulator


@dataclass(frozen=True, slots=True)
class ObservationIdentity:
    """Safe immutable view of the active observation correlation."""

    request_id: str
    trace_id: str
    agent: AgentKind | None
    attempt: int | None
    sdk_export_enabled: bool


_request_observation: ContextVar[_RequestObservation | None] = ContextVar(
    "agent_request_observation",
    default=None,
)
_current_agent: ContextVar[AgentKind | None] = ContextVar(
    "agent_observation_agent",
    default=None,
)
_current_attempt: ContextVar[int | None] = ContextVar(
    "agent_observation_attempt",
    default=None,
)


@contextmanager
def bind_request_observation(
    *,
    request_id: str,
    trace_id: str,
    sdk_export_enabled: bool,
) -> Iterator[_UsageAccumulator]:
    """Bind only safe correlation values and reset them on every exit path."""
    accumulator = _UsageAccumulator()
    request_token = _request_observation.set(
        _RequestObservation(
            request_id=request_id,
            trace_id=trace_id,
            sdk_export_enabled=sdk_export_enabled,
            accumulator=accumulator,
        )
    )
    agent_token = _current_agent.set(None)
    attempt_token = _current_attempt.set(None)
    try:
        yield accumulator
    finally:
        _current_attempt.reset(attempt_token)
        _current_agent.reset(agent_token)
        _request_observation.reset(request_token)


@contextmanager
def observation_attempt(
    agent: AgentKind,
    attempt: int,
) -> Iterator[None]:
    """Bind one attempted service call and restore any enclosing scope."""
    observation = _request_observation.get()
    if observation is not None:
        observation.accumulator.begin_attempt(agent, attempt)
    agent_token = _current_agent.set(agent)
    attempt_token = _current_attempt.set(attempt)
    try:
        yield
    finally:
        _current_attempt.reset(attempt_token)
        _current_agent.reset(agent_token)


def current_observation_identity() -> ObservationIdentity | None:
    """Return a safe immutable identity view for tests and SDK adaptation."""
    observation = _request_observation.get()
    if observation is None:
        return None
    return ObservationIdentity(
        request_id=observation.request_id,
        trace_id=observation.trace_id,
        agent=_current_agent.get(),
        attempt=_current_attempt.get(),
        sdk_export_enabled=observation.sdk_export_enabled,
    )


def capture_usage_for_current_attempt(usage: AgentTokenUsage) -> bool:
    """Attach one completed SDK usage event to its active stage."""
    observation = _request_observation.get()
    agent = _current_agent.get()
    attempt = _current_attempt.get()
    if observation is None or agent is None or attempt is None:
        return False
    observation.accumulator.add(agent, usage)
    return True
