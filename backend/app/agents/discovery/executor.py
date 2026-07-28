"""Deterministic and OpenAI Agents SDK Discovery execution adapters."""

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
    RunContextWrapper,
    Runner,
    function_tool,
)
from agents.models.openai_provider import OpenAIProvider

from app.agents.contracts import DiscoveryOutput, DiscoveryRequest
from app.agents.discovery.evidence import (
    assemble_discovery_output,
    validate_output_closure,
)
from app.agents.discovery.instructions import DISCOVERY_INSTRUCTIONS
from app.agents.discovery.menu import PoiMenuReader
from app.agents.discovery.tools import DiscoveryRunRegistry
from app.providers.poi.contracts import PoiProvider

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_DISCOVERY_MODEL_ENV = "OPENAI_DISCOVERY_MODEL"
DISCOVERY_MAX_TURNS = 3


@runtime_checkable
class DiscoveryExecutor(Protocol):
    """Public boundary accepting and returning only validated T040 values."""

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> DiscoveryOutput:
        """Return one validated DiscoveryOutput or a sanitized total failure."""
        ...


class _RunResultLike(Protocol):
    @property
    def final_output(self) -> object:
        """Return the SDK's final structured output."""
        ...


class _RunnerAdapter(Protocol):
    async def run(
        self,
        starting_agent: Agent[DiscoveryRunRegistry],
        model_input: str,
        *,
        context: DiscoveryRunRegistry,
        max_turns: int,
        run_config: RunConfig,
    ) -> _RunResultLike:
        """Execute one isolated async SDK run."""
        ...


class _AgentsSdkRunner:
    async def run(
        self,
        starting_agent: Agent[DiscoveryRunRegistry],
        model_input: str,
        *,
        context: DiscoveryRunRegistry,
        max_turns: int,
        run_config: RunConfig,
    ) -> _RunResultLike:
        result = await Runner.run(
            starting_agent,
            model_input,
            context=context,
            max_turns=max_turns,
            run_config=run_config,
        )
        return cast(_RunResultLike, result)


@function_tool(
    name_override="normalized_poi_search",
    description_override=(
        "Run the validated request's normalized POI search exactly once. "
        "This tool accepts no model-supplied location or filters."
    ),
    failure_error_function=None,
    strict_mode=True,
)
async def normalized_poi_search(
    context: RunContextWrapper[DiscoveryRunRegistry],
) -> str:
    """Return strict normalized POI facts without request origin."""
    result = await context.context.search_pois()
    return result.model_dump_json(exclude_none=True)


@function_tool(
    name_override="normalized_menu_lookup",
    description_override=(
        "Read menus once for curated POIs selected by normalized POI search. "
        "This tool accepts no model-supplied POI identity."
    ),
    failure_error_function=None,
    strict_mode=True,
)
async def normalized_menu_lookup(
    context: RunContextWrapper[DiscoveryRunRegistry],
) -> str:
    """Return strict selected-POI menu facts without arbitrary IDs."""
    result = await context.context.read_menus()
    return result.model_dump_json(exclude_none=True)


class DeterministicDiscoveryExecutor:
    """Execute normalized tools directly and assemble a pure result."""

    def __init__(
        self,
        provider: PoiProvider,
        menu_reader: PoiMenuReader,
    ) -> None:
        self._provider = provider
        self._menu_reader = menu_reader

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> DiscoveryOutput:
        """Call each applicable tool once and return deterministic output."""
        registry = DiscoveryRunRegistry(
            request,
            self._provider,
            self._menu_reader,
        )
        await registry.complete_missing_operations()
        return assemble_discovery_output(request, registry.snapshot())


class OpenAIDiscoveryExecutor:
    """One two-tool/no-handoff Discovery agent with registry fallback."""

    def __init__(
        self,
        provider: PoiProvider,
        menu_reader: PoiMenuReader,
        *,
        api_key: str,
        model: str,
        runner: _RunnerAdapter | None = None,
    ) -> None:
        normalized_api_key = api_key.strip()
        normalized_model = model.strip()
        if not normalized_api_key or not normalized_model:
            raise ValueError("OpenAI discovery configuration must be nonblank.")
        self._provider = provider
        self._menu_reader = menu_reader
        self._agent: Agent[DiscoveryRunRegistry] = Agent(
            name="travel_discovery",
            instructions=DISCOVERY_INSTRUCTIONS,
            model=normalized_model,
            model_settings=ModelSettings(
                tool_choice="auto",
                parallel_tool_calls=False,
                retry=ModelRetrySettings(max_retries=0),
            ),
            output_type=DiscoveryOutput,
            tools=[normalized_poi_search, normalized_menu_lookup],
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
        provider: PoiProvider,
        menu_reader: PoiMenuReader,
    ) -> OpenAIDiscoveryExecutor | None:
        """Read optional key and explicit model lazily."""
        api_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
        model = os.environ.get(OPENAI_DISCOVERY_MODEL_ENV, "").strip()
        if not api_key or not model:
            return None
        return cls(
            provider,
            menu_reader,
            api_key=api_key,
            model=model,
        )

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> DiscoveryOutput:
        """Run once, then close or fall back over the same tool registry."""
        registry = DiscoveryRunRegistry(
            request,
            self._provider,
            self._menu_reader,
        )
        final_output: object = None
        try:
            result = await self._runner.run(
                self._agent,
                serialize_discovery_request(request),
                context=registry,
                max_turns=DISCOVERY_MAX_TURNS,
                run_config=self._run_config,
            )
            final_output = result.final_output
        except asyncio.CancelledError:
            raise
        except Exception:
            final_output = None

        await registry.complete_missing_operations()
        expected = assemble_discovery_output(request, registry.snapshot())
        try:
            return validate_output_closure(final_output, expected)
        except Exception:
            return expected


def serialize_discovery_request(request: DiscoveryRequest) -> str:
    """Serialize only nonsensitive fields needed to enforce tool policy."""
    value = {
        "city": request.city.value,
        "radius_metres": request.radius_metres,
        "limit": request.limit,
        "requested_fact_kinds": [
            fact_kind.value for fact_kind in request.requested_fact_kinds
        ],
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
