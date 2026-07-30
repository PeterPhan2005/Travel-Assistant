"""OpenAI Agents SDK adapter for one independent Response Composer run."""

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

from app.agents.composer.instructions import (
    RESPONSE_COMPOSER_INSTRUCTIONS,
)
from app.agents.composer.renderer import build_deterministic_response
from app.agents.composer.validation import (
    validate_response_composer_output,
)
from app.agents.contracts import (
    DiscoverySpecialistOutput,
    ItinerarySpecialistOutput,
    LocalCultureSpecialistOutput,
    NarrationSpecialistOutput,
    ResponseComposerOutput,
    ResponseComposerRequest,
    SpecialistOutput,
)
from app.agents.observability.sdk import (
    capture_sdk_result_usage,
    run_config_for_observation,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_COMPOSER_MODEL_ENV = "OPENAI_COMPOSER_MODEL"
COMPOSER_MAX_TURNS = 1


@runtime_checkable
class ResponseComposerExecutor(Protocol):
    """Public boundary for one request and validated composer output."""

    async def compose(
        self,
        request: ResponseComposerRequest,
    ) -> ResponseComposerOutput:
        """Return only one validated ResponseComposerOutput."""
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


class OpenAIResponseComposerExecutor:
    """Configured no-tool/no-handoff adapter with exact output closure."""

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
            raise ValueError("OpenAI composer configuration must be nonblank.")
        self._agent: Agent[None] = Agent(
            name="travel_response_composer",
            instructions=RESPONSE_COMPOSER_INSTRUCTIONS,
            model=normalized_model,
            model_settings=ModelSettings(
                tool_choice="none",
                parallel_tool_calls=False,
                retry=ModelRetrySettings(max_retries=0),
            ),
            output_type=ResponseComposerOutput,
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
    def from_environment(
        cls,
    ) -> OpenAIResponseComposerExecutor | None:
        """Read the optional key and explicit composer model lazily."""
        api_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
        model = os.environ.get(OPENAI_COMPOSER_MODEL_ENV, "").strip()
        if not api_key or not model:
            return None
        return cls(api_key=api_key, model=model)

    async def compose(
        self,
        request: ResponseComposerRequest,
    ) -> ResponseComposerOutput:
        """Run once and return exact closed output or deterministic fallback."""
        deterministic = build_deterministic_response(request)
        try:
            result = await self._runner.run(
                self._agent,
                serialize_response_composer_request(request),
                max_turns=COMPOSER_MAX_TURNS,
                run_config=run_config_for_observation(self._run_config),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return deterministic
        final_output = result.final_output
        if not isinstance(final_output, ResponseComposerOutput):
            return deterministic
        try:
            return validate_response_composer_output(
                final_output,
                request,
                deterministic,
            )
        except (TypeError, ValueError):
            return deterministic


def serialize_response_composer_request(
    request: ResponseComposerRequest,
) -> str:
    """Serialize only approved text, references, POIs, and safe warnings."""
    approved = set(request.approved_claim_ids)
    value = {
        "user_query": " ".join(request.user_query.split()),
        "locale": request.locale,
        "approved_claims": [
            {
                "claim_id": claim.claim_id,
                "fact_kind": claim.fact_kind.value,
                "statement": claim.statement,
                "supporting_source_ids": list(
                    claim.supporting_source_ids
                ),
                **(
                    {"poi_id": claim.poi_id}
                    if claim.poi_id is not None
                    else {}
                ),
                **(
                    {"price": claim.price.model_dump(mode="json")}
                    if claim.price is not None
                    else {}
                ),
            }
            for claim in request.evidence.claims
            if claim.claim_id in approved
        ],
        "approved_specialist_outputs": [
            _serialize_specialist(output)
            for output in request.approved_specialist_outputs
        ],
        "warnings": [
            warning.model_dump(mode="json")
            for warning in request.warnings
        ],
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _serialize_specialist(output: SpecialistOutput) -> dict[str, object]:
    base: dict[str, object] = {
        "kind": output.agent.value,
        "output_id": output.output_id,
    }
    if isinstance(output, DiscoverySpecialistOutput):
        base["content"] = {
            "candidates": [
                {
                    "poi_id": candidate.id,
                    "canonical_name": candidate.canonical_name,
                    "category": candidate.category,
                    **(
                        {"address": candidate.address}
                        if candidate.address is not None
                        else {}
                    ),
                    **(
                        {"distance_metres": candidate.distance_metres}
                        if candidate.distance_metres is not None
                        else {}
                    ),
                    **(
                        {"rating": format(candidate.rating, "f")}
                        if candidate.rating is not None
                        else {}
                    ),
                    **(
                        {"rating_count": candidate.rating_count}
                        if candidate.rating_count is not None
                        else {}
                    ),
                    **(
                        {
                            "opening_hours_summary":
                            candidate.opening_hours_summary
                        }
                        if candidate.opening_hours_summary is not None
                        else {}
                    ),
                }
                for candidate in output.output.candidates
            ],
        }
    elif isinstance(output, NarrationSpecialistOutput):
        base["content"] = output.output.model_dump(mode="json")
    elif isinstance(output, LocalCultureSpecialistOutput):
        base["content"] = output.output.model_dump(mode="json")
    elif isinstance(output, ItinerarySpecialistOutput):
        base["content"] = output.output.model_dump(mode="json")
    return base
