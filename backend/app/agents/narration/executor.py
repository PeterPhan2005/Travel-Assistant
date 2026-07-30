"""OpenAI Agents SDK adapter for one independent Narration Agent run."""

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

from app.agents.contracts import NarrationOutput, NarrationRequest
from app.agents.narration.fallback import (
    NarrationLimitationReason,
    build_limited_narration,
)
from app.agents.narration.instructions import NARRATION_INSTRUCTIONS
from app.agents.narration.validation import (
    usable_claims,
    validate_narration_output,
)
from app.agents.observability.sdk import (
    capture_sdk_result_usage,
    run_config_for_observation,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_NARRATION_MODEL_ENV = "OPENAI_NARRATION_MODEL"
NARRATION_MAX_TURNS = 1


@runtime_checkable
class NarrationExecutor(Protocol):
    """Public boundary for one validated request and NarrationOutput."""

    async def narrate(
        self,
        request: NarrationRequest,
    ) -> NarrationOutput:
        """Return only a validated NarrationOutput."""
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


class OpenAINarrationExecutor:
    """Configured no-tool/no-handoff adapter for one narration run."""

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
            raise ValueError("OpenAI narration configuration must be nonblank.")

        self._agent: Agent[None] = Agent(
            name="travel_narration",
            instructions=NARRATION_INSTRUCTIONS,
            model=normalized_model,
            model_settings=ModelSettings(
                tool_choice="none",
                parallel_tool_calls=False,
                retry=ModelRetrySettings(max_retries=0),
            ),
            output_type=NarrationOutput,
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
    def from_environment(cls) -> OpenAINarrationExecutor | None:
        """Read optional key and explicit narration model lazily."""
        api_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
        model = os.environ.get(OPENAI_NARRATION_MODEL_ENV, "").strip()
        if not api_key or not model:
            return None
        return cls(api_key=api_key, model=model)

    async def narrate(
        self,
        request: NarrationRequest,
    ) -> NarrationOutput:
        """Run once and return a validated result or deterministic fallback."""
        try:
            result = await self._runner.run(
                self._agent,
                serialize_narration_request(request),
                max_turns=NARRATION_MAX_TURNS,
                run_config=run_config_for_observation(self._run_config),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return build_limited_narration(
                request,
                NarrationLimitationReason.MODEL_UNAVAILABLE,
            )

        final_output = result.final_output
        if not isinstance(final_output, NarrationOutput):
            return build_limited_narration(
                request,
                NarrationLimitationReason.INVALID_MODEL_OUTPUT,
            )
        try:
            return validate_narration_output(final_output, request)
        except (TypeError, ValueError):
            return build_limited_narration(
                request,
                NarrationLimitationReason.INVALID_MODEL_OUTPUT,
            )


def serialize_narration_request(request: NarrationRequest) -> str:
    """Serialize only POI-scoped claims and their source identities."""
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
        "poi": request.poi.model_dump(mode="json"),
        "locale": request.locale,
        "word_range": request.word_range.model_dump(mode="json"),
        "claims": [
            {
                "claim_id": claim.claim_id,
                "fact_kind": claim.fact_kind.value,
                "statement": claim.statement,
                "supporting_source_ids": list(
                    claim.supporting_source_ids
                ),
                **(
                    {"freshness_at": claim.freshness_at.isoformat()}
                    if claim.freshness_at is not None
                    else {}
                ),
                **(
                    {"price": claim.price.model_dump(mode="json")}
                    if claim.price is not None
                    else {}
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
