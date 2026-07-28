"""OpenAI Agents SDK adapter for one independent grounding review."""

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

from app.agents.contracts import (
    DiscoverySpecialistOutput,
    GroundingReviewOutput,
    GroundingReviewRequest,
    ItinerarySpecialistOutput,
    LocalCultureSpecialistOutput,
    NarrationSpecialistOutput,
    SpecialistOutput,
)
from app.agents.grounding.instructions import (
    GROUNDING_REVIEWER_INSTRUCTIONS,
)
from app.agents.grounding.reviewer import build_deterministic_review
from app.agents.grounding.validation import (
    validate_grounding_review_output,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_GROUNDING_MODEL_ENV = "OPENAI_GROUNDING_MODEL"
GROUNDING_MAX_TURNS = 1


@runtime_checkable
class GroundingReviewerExecutor(Protocol):
    """Public boundary for one request and validated review output."""

    async def review(
        self,
        request: GroundingReviewRequest,
    ) -> GroundingReviewOutput:
        """Return only one validated GroundingReviewOutput."""
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
        return cast(_RunResultLike, result)


class OpenAIGroundingReviewerExecutor:
    """Configured no-tool/no-handoff adapter with deterministic closure."""

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
            raise ValueError("OpenAI grounding configuration must be nonblank.")
        self._agent: Agent[None] = Agent(
            name="travel_grounding_reviewer",
            instructions=GROUNDING_REVIEWER_INSTRUCTIONS,
            model=normalized_model,
            model_settings=ModelSettings(
                tool_choice="none",
                parallel_tool_calls=False,
                retry=ModelRetrySettings(max_retries=0),
            ),
            output_type=GroundingReviewOutput,
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
    ) -> OpenAIGroundingReviewerExecutor | None:
        """Read the optional key and explicit grounding model lazily."""
        api_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
        model = os.environ.get(OPENAI_GROUNDING_MODEL_ENV, "").strip()
        if not api_key or not model:
            return None
        return cls(api_key=api_key, model=model)

    async def review(
        self,
        request: GroundingReviewRequest,
    ) -> GroundingReviewOutput:
        """Run once and return a closed result or deterministic fallback."""
        deterministic = build_deterministic_review(request)
        try:
            result = await self._runner.run(
                self._agent,
                serialize_grounding_review_request(request),
                max_turns=GROUNDING_MAX_TURNS,
                run_config=self._run_config,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return deterministic
        final_output = result.final_output
        if not isinstance(final_output, GroundingReviewOutput):
            return deterministic
        try:
            return validate_grounding_review_output(
                final_output,
                request,
                deterministic,
            )
        except (TypeError, ValueError):
            return deterministic


def serialize_grounding_review_request(
    request: GroundingReviewRequest,
) -> str:
    """Serialize only evidence and specialist fields required for review."""
    value = {
        "reviewed_claim_ids": sorted(request.evidence.claim_ids),
        "reviewed_specialist_output_ids": [
            output.output_id for output in request.specialist_outputs
        ],
        "sources": [
            {
                "source_id": source.source_id,
                "source_type": source.source_type.value,
                **(
                    {"published_at": source.published_at.isoformat()}
                    if source.published_at is not None
                    else {}
                ),
                **(
                    {"retrieved_at": source.retrieved_at.isoformat()}
                    if source.retrieved_at is not None
                    else {}
                ),
            }
            for source in request.evidence.sources
        ],
        "claims": [
            {
                "claim_id": claim.claim_id,
                "evidence_id": claim.evidence_id,
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
            for claim in request.evidence.claims
        ],
        "specialist_outputs": [
            _serialize_specialist(output)
            for output in request.specialist_outputs
        ],
        "freshness_requirements": [
            requirement.model_dump(mode="json")
            for requirement in request.freshness_requirements
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
        "agent": output.agent.value,
        "output_id": output.output_id,
    }
    if isinstance(output, DiscoverySpecialistOutput):
        base["output"] = {
            "candidates": [
                {
                    "id": candidate.id,
                    "canonical_name": candidate.canonical_name,
                    "city": candidate.city.value,
                    "category": candidate.category,
                    "address": candidate.address,
                    "distance_metres": candidate.distance_metres,
                    "rating": candidate.rating,
                    "rating_count": candidate.rating_count,
                    "price_level": candidate.price_level,
                    "opening_hours_summary": candidate.opening_hours_summary,
                    "source_ids": [
                        source.source_id for source in candidate.sources
                    ],
                }
                for candidate in output.output.candidates
            ],
            "claim_ids": [
                claim.claim_id for claim in output.output.evidence.claims
            ],
            "completeness": output.output.completeness.value,
            "is_truncated": output.output.is_truncated,
        }
    elif isinstance(output, NarrationSpecialistOutput):
        base["output"] = output.output.model_dump(mode="json")
    elif isinstance(output, LocalCultureSpecialistOutput):
        base["output"] = output.output.model_dump(mode="json")
    elif isinstance(output, ItinerarySpecialistOutput):
        base["output"] = output.output.model_dump(mode="json")
    return base
