"""OpenAI Agents SDK adapter for one independent Local Culture run."""

from __future__ import annotations

import asyncio
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

from app.agents.contracts import LocalCultureOutput, LocalCultureRequest
from app.agents.local_culture.fallback import (
    LocalCultureLimitationReason,
    build_limited_local_culture,
)
from app.agents.local_culture.instructions import LOCAL_CULTURE_INSTRUCTIONS
from app.agents.local_culture.validation import (
    UnsafeLocalCultureOutputError,
    usable_claims,
    validate_local_culture_output,
)
from app.agents.observability.sdk import (
    capture_sdk_result_usage,
    run_config_for_observation,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_LOCAL_CULTURE_MODEL_ENV = "OPENAI_LOCAL_CULTURE_MODEL"
LOCAL_CULTURE_MAX_TURNS = 1


@runtime_checkable
class LocalCultureExecutor(Protocol):
    """Public boundary for one request and validated LocalCultureOutput."""

    async def advise(
        self,
        request: LocalCultureRequest,
    ) -> LocalCultureOutput:
        """Return only a validated LocalCultureOutput."""
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
        """Execute one isolated async SDK run."""
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
        capture_sdk_result_usage(result)
        return cast(_RunResultLike, result)


class OpenAILocalCultureExecutor:
    """Configured no-tool/no-handoff adapter for one Local Culture run."""

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
            raise ValueError(
                "OpenAI Local Culture configuration must be nonblank."
            )

        self._agent: Agent[None] = Agent(
            name="travel_local_culture",
            instructions=LOCAL_CULTURE_INSTRUCTIONS,
            model=normalized_model,
            model_settings=ModelSettings(
                tool_choice="none",
                parallel_tool_calls=False,
                retry=ModelRetrySettings(max_retries=0),
            ),
            output_type=LocalCultureOutput,
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
    def from_environment(cls) -> OpenAILocalCultureExecutor | None:
        """Read optional key and explicit Local Culture model lazily."""
        api_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
        model = os.environ.get(
            OPENAI_LOCAL_CULTURE_MODEL_ENV,
            "",
        ).strip()
        if not api_key or not model:
            return None
        return cls(api_key=api_key, model=model)

    async def advise(
        self,
        request: LocalCultureRequest,
    ) -> LocalCultureOutput:
        """Run once and return validated guidance or deterministic fallback."""
        try:
            result = await self._runner.run(
                self._agent,
                serialize_local_culture_request(request),
                max_turns=LOCAL_CULTURE_MAX_TURNS,
                run_config=run_config_for_observation(self._run_config),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return build_limited_local_culture(
                request,
                LocalCultureLimitationReason.MODEL_UNAVAILABLE,
            )

        final_output = result.final_output
        if not isinstance(final_output, LocalCultureOutput):
            return build_limited_local_culture(
                request,
                LocalCultureLimitationReason.INVALID_MODEL_OUTPUT,
            )
        try:
            return validate_local_culture_output(final_output, request)
        except UnsafeLocalCultureOutputError:
            return build_limited_local_culture(
                request,
                LocalCultureLimitationReason.UNSAFE_GENERALIZATION,
            )
        except (TypeError, ValueError):
            return build_limited_local_culture(
                request,
                LocalCultureLimitationReason.INVALID_MODEL_OUTPUT,
            )


def serialize_local_culture_request(
    request: LocalCultureRequest,
) -> str:
    """Serialize only approved claims and the minimum request context."""
    claims = usable_claims(request)
    source_ids = tuple(
        sorted(
            {
                source_id
                for claim in claims
                for source_id in claim.supporting_source_ids
            }
        )
    )
    value = {
        "city": request.city.value,
        "locale": request.locale,
        "topic": request.topic,
        "claims": [
            {
                "claim_id": claim.claim_id,
                "fact_kind": claim.fact_kind.value,
                "statement": claim.statement,
                "supporting_source_ids": list(
                    claim.supporting_source_ids
                ),
            }
            for claim in claims
        ],
        "source_ids": list(source_ids),
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
