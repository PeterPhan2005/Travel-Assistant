"""OpenAI Agents SDK adapter for one independent Router Agent run."""

from __future__ import annotations

import json
import os
from typing import Protocol, cast, runtime_checkable

from agents import (
    Agent,
    ModelRetrySettings,
    ModelSettings,
    RunConfig,
    Runner,
)
from agents.models.openai_provider import OpenAIProvider
from pydantic import ValidationError

from app.agents.contracts import RouterOutput, RouterRequest
from app.agents.router.instructions import ROUTER_INSTRUCTIONS

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_ROUTER_MODEL_ENV = "OPENAI_ROUTER_MODEL"
ROUTER_MAX_TURNS = 1


@runtime_checkable
class RouterExecutor(Protocol):
    """Typed public boundary for one validated router request and output."""

    async def route(self, request: RouterRequest) -> RouterOutput:
        """Return only a validated RouterOutput."""
        ...


class _RunResultLike(Protocol):
    @property
    def final_output(self) -> object:
        """Return the SDK's final structured output."""
        ...


class _RunnerAdapter(Protocol):
    async def run(
        self,
        starting_agent: Agent[None],
        model_input: str,
        *,
        max_turns: int,
        run_config: RunConfig,
    ) -> _RunResultLike:
        """Execute one async SDK run."""
        ...


class _AgentsSdkRunner:
    async def run(
        self,
        starting_agent: Agent[None],
        model_input: str,
        *,
        max_turns: int,
        run_config: RunConfig,
    ) -> _RunResultLike:
        result = await Runner.run(
            starting_agent,
            model_input,
            max_turns=max_turns,
            run_config=run_config,
        )
        return cast(_RunResultLike, result)


class InvalidRouterModelOutputError(Exception):
    """The SDK did not return a value accepted by the RouterOutput contract."""


class OpenAIRouterExecutor:
    """Configured no-tool/no-handoff adapter for one model-backed router run."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        runner: _RunnerAdapter | None = None,
    ) -> None:
        normalized_api_key = api_key.strip()
        normalized_model = model.strip()
        if not normalized_api_key or not normalized_model:
            raise ValueError("OpenAI router configuration must be nonblank.")

        self._agent: Agent[None] = Agent(
            name="travel_intent_router",
            instructions=ROUTER_INSTRUCTIONS,
            model=normalized_model,
            model_settings=ModelSettings(
                tool_choice="none",
                parallel_tool_calls=False,
                retry=ModelRetrySettings(max_retries=0),
            ),
            output_type=RouterOutput,
            tools=[],
            handoffs=[],
            mcp_servers=[],
        )
        self._run_config = RunConfig(
            model_provider=OpenAIProvider(api_key=normalized_api_key),
            tracing_disabled=True,
            trace_include_sensitive_data=False,
        )
        self._runner = runner or _AgentsSdkRunner()

    @classmethod
    def from_environment(cls) -> OpenAIRouterExecutor | None:
        """Read optional model configuration lazily and reject blank values."""
        api_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
        model = os.environ.get(OPENAI_ROUTER_MODEL_ENV, "").strip()
        if not api_key or not model:
            return None
        return cls(api_key=api_key, model=model)

    async def route(self, request: RouterRequest) -> RouterOutput:
        """Run once and fail closed if the SDK output is not RouterOutput."""
        result = await self._runner.run(
            self._agent,
            serialize_router_request(request),
            max_turns=ROUTER_MAX_TURNS,
            run_config=self._run_config,
        )
        final_output = result.final_output
        if not isinstance(final_output, RouterOutput):
            raise InvalidRouterModelOutputError(
                "Router model returned invalid structured output."
            )
        try:
            return RouterOutput.model_validate(
                final_output.model_dump(mode="python")
            )
        except (TypeError, ValueError, ValidationError):
            raise InvalidRouterModelOutputError(
                "Router model returned invalid structured output."
            ) from None


def serialize_router_request(request: RouterRequest) -> str:
    """Serialize exactly the validated RouterRequest fields as compact JSON."""
    return json.dumps(
        request.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
