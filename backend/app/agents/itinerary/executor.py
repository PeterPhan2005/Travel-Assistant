"""OpenAI Agents SDK adapter for one independent Itinerary Agent run."""

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

from app.agents.contracts import ItineraryOutput, ItineraryRequest
from app.agents.itinerary.instructions import (
    APPROVED_ASSUMPTIONS,
    ITINERARY_INSTRUCTIONS,
)
from app.agents.itinerary.planner import plan_itinerary
from app.agents.itinerary.validation import validate_itinerary_output
from app.agents.observability.sdk import (
    capture_sdk_result_usage,
    run_config_for_observation,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_ITINERARY_MODEL_ENV = "OPENAI_ITINERARY_MODEL"
ITINERARY_MAX_TURNS = 1


@runtime_checkable
class ItineraryExecutor(Protocol):
    """Public boundary for one validated request and ItineraryOutput."""

    async def draft(
        self,
        request: ItineraryRequest,
    ) -> ItineraryOutput:
        """Return only a validated ItineraryOutput."""
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


class OpenAIItineraryExecutor:
    """Configured no-tool/no-handoff adapter for one itinerary run."""

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
            raise ValueError("OpenAI itinerary configuration must be nonblank.")

        self._agent: Agent[None] = Agent(
            name="travel_itinerary",
            instructions=ITINERARY_INSTRUCTIONS,
            model=normalized_model,
            model_settings=ModelSettings(
                tool_choice="none",
                parallel_tool_calls=False,
                retry=ModelRetrySettings(max_retries=0),
            ),
            output_type=ItineraryOutput,
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
    def from_environment(cls) -> OpenAIItineraryExecutor | None:
        """Read optional key and explicit itinerary model lazily."""
        api_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
        model = os.environ.get(OPENAI_ITINERARY_MODEL_ENV, "").strip()
        if not api_key or not model:
            return None
        return cls(api_key=api_key, model=model)

    async def draft(
        self,
        request: ItineraryRequest,
    ) -> ItineraryOutput:
        """Run once and return a closed model result or pure fallback."""
        fallback = plan_itinerary(request)
        try:
            result = await self._runner.run(
                self._agent,
                serialize_itinerary_request(request),
                max_turns=ITINERARY_MAX_TURNS,
                run_config=run_config_for_observation(self._run_config),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return fallback

        final_output = result.final_output
        if not isinstance(final_output, ItineraryOutput):
            return fallback
        try:
            return validate_itinerary_output(final_output, request)
        except (TypeError, ValueError):
            return fallback


def serialize_itinerary_request(request: ItineraryRequest) -> str:
    """Serialize only approved planning fields without coordinates or metadata."""
    candidate_ids = {candidate.id for candidate in request.candidates}
    claims = tuple(
        claim
        for claim in request.evidence.claims
        if claim.poi_id in candidate_ids
    )
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
        "local_date": request.local_date.isoformat(),
        "timezone": request.timezone,
        "start_local_time": request.start_local_time.isoformat(),
        "end_local_time": request.end_local_time.isoformat(),
        "candidates": [
            {
                "id": candidate.id,
                "canonical_name": candidate.canonical_name,
                "category": candidate.category,
                **(
                    {"distance_metres": candidate.distance_metres}
                    if candidate.distance_metres is not None
                    else {}
                ),
            }
            for candidate in request.candidates
        ],
        "constraints": request.constraints.model_dump(mode="json"),
        "claims": [
            {
                "claim_id": claim.claim_id,
                "fact_kind": claim.fact_kind.value,
                "statement": claim.statement,
                "poi_id": claim.poi_id,
                "supporting_source_ids": list(
                    claim.supporting_source_ids
                ),
            }
            for claim in claims
        ],
        "source_ids": list(source_ids),
        "approved_assumptions": list(APPROVED_ASSUMPTIONS),
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
