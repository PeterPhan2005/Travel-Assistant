"""Deterministic tools, evidence, SDK closure, and privacy tests for T042."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from agents import Agent, FunctionTool, RunConfig
from pydantic import HttpUrl, ValidationError

from app.agents.contracts import (
    DiscoveryCompleteness,
    DiscoveryOrigin,
    DiscoveryOutput,
    DiscoveryRequest,
    FactKind,
    FailureCode,
    SourceType,
    SupportedCity,
)
from app.agents.discovery import (
    DiscoveryExecutionError,
    DiscoveryService,
    MenuErrorCode,
    MenuReaderError,
    OpenAIDiscoveryExecutor,
)
from app.agents.discovery.evidence import assemble_discovery_output
from app.agents.discovery.executor import (
    DISCOVERY_MAX_TURNS,
    OPENAI_API_KEY_ENV,
    OPENAI_DISCOVERY_MODEL_ENV,
    serialize_discovery_request,
)
from app.agents.discovery.instructions import DISCOVERY_INSTRUCTIONS
from app.agents.discovery.models import (
    DiscoveryRegistrySnapshot,
    MenuItemResult,
    MenuResultEnvelope,
    PoiToolCandidate,
    PoiToolResult,
    PrivateToolModel,
    ToolCoordinates,
    ToolSource,
)
from app.agents.discovery.tools import (
    DiscoveryRunRegistry,
    ToolInvocationError,
    discovery_to_provider_request,
)
from app.providers.poi.errors import (
    PoiProviderError,
    ProviderErrorCode,
    ProviderFailure,
)
from app.providers.poi.models import (
    Coordinates,
    PoiDiscoveryRequest,
    PoiDiscoveryResult,
    PoiProviderKind,
    PoiResultEnvelope,
    SourceReference,
)

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
NOW = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
UPDATED = datetime(2026, 1, 3, 4, 5, tzinfo=timezone.utc)


def _request(
    *,
    facts: tuple[FactKind, ...] = (
        FactKind.CATEGORY,
        FactKind.IDENTITY,
    ),
    city: SupportedCity = SupportedCity.HCMC,
    query: str | None = "phở gần đây",
) -> DiscoveryRequest:
    return DiscoveryRequest(
        city=city,
        origin=DiscoveryOrigin(latitude=10.7799, longitude=106.7),
        radius_metres=5_000,
        limit=5,
        query=query,
        category=None,
        requested_fact_kinds=tuple(
            sorted(facts, key=lambda fact: fact.value)
        ),
    )


def _source(
    source_id: str = "hcmc-source-a",
) -> SourceReference:
    return SourceReference(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_OPERATOR.value,
        label="Nguồn chính thức",
        publisher="Nhà xuất bản",
        url=HttpUrl("https://example.test/source"),
        published_at=None,
        retrieved_at=NOW,
    )


def _poi(
    provider_id: str = "hcmc-poi-a",
    *,
    name: str = "Phở Việt",
    distance: float = 125.5,
    source: SourceReference | None = None,
    address: str | None = None,
    rating: Decimal | None = None,
    opening_hours: str | None = None,
) -> PoiDiscoveryResult:
    sources = () if source is None else (source,)
    return PoiDiscoveryResult(
        id=f"curated:{provider_id}",
        provider=PoiProviderKind.CURATED,
        provider_id=provider_id,
        canonical_name=name,
        city=SupportedCity.HCMC,
        category="restaurant",
        address=address,
        coordinates=Coordinates(latitude=10.78, longitude=106.7),
        distance_metres=distance,
        rating=rating,
        rating_count=None,
        price_level=None,
        opening_hours_summary=opening_hours,
        sources=sources,
        retrieved_at=NOW if sources else None,
        is_curated=True,
        is_externally_supplied=False,
    )


def _envelope(
    items: tuple[PoiDiscoveryResult, ...] | None = None,
    *,
    is_complete: bool = True,
) -> PoiResultEnvelope:
    resolved = items if items is not None else (_poi(source=_source()),)
    freshness = max(
        (
            item.retrieved_at
            for item in resolved
            if item.retrieved_at is not None
        ),
        default=None,
    )
    return PoiResultEnvelope(
        provider=PoiProviderKind.CURATED,
        items=resolved,
        returned_count=len(resolved),
        is_complete=is_complete,
        freshness_at=freshness,
    )


class _FakeProvider:
    def __init__(
        self,
        result: PoiResultEnvelope | BaseException | object,
    ) -> None:
        self.result = result
        self.calls: list[PoiDiscoveryRequest] = []

    async def discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        self.calls.append(request)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result  # type: ignore[return-value]


class _FakeMenuReader:
    def __init__(
        self,
        result: MenuResultEnvelope | BaseException | object | None = None,
    ) -> None:
        self.result = result if result is not None else MenuResultEnvelope()
        self.calls: list[tuple[str, ...]] = []

    async def read_menu_items(
        self,
        poi_provider_ids: tuple[str, ...],
    ) -> MenuResultEnvelope:
        self.calls.append(poi_provider_ids)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result  # type: ignore[return-value]


def _menu() -> MenuResultEnvelope:
    return MenuResultEnvelope(
        items=(
            MenuItemResult(
                menu_item_id="hcmc-menu-pho",
                poi_provider_id="hcmc-poi-a",
                item_name="Phở đặc biệt",
                price_minor_units=75_000,
                currency="VND",
                source_updated_at=UPDATED,
                source=ToolSource(
                    source_id="hcmc-source-menu",
                    source_type=SourceType.OFFICIAL_OPERATOR,
                    label="Menu chính thức",
                    publisher=None,
                    url=HttpUrl("https://example.test/menu"),
                    published_at=None,
                    retrieved_at=NOW,
                ),
            ),
        )
    )


@dataclass
class _FakeRunResult:
    final_output: object


class _RegistryRunner:
    def __init__(
        self,
        behavior: str,
        output_transform: object | None = None,
    ) -> None:
        self.behavior = behavior
        self.output_transform = output_transform
        self.calls: list[
            tuple[
                Agent[DiscoveryRunRegistry],
                str,
                DiscoveryRunRegistry,
                int,
                RunConfig,
            ]
        ] = []

    async def run(
        self,
        starting_agent: Agent[DiscoveryRunRegistry],
        model_input: str,
        *,
        context: DiscoveryRunRegistry,
        max_turns: int,
        run_config: RunConfig,
    ) -> _FakeRunResult:
        self.calls.append(
            (
                starting_agent,
                model_input,
                context,
                max_turns,
                run_config,
            )
        )
        if self.behavior == "cancel":
            raise asyncio.CancelledError
        if self.behavior == "raise":
            raise RuntimeError("raw private model failure")
        if self.behavior == "no_tools":
            return _FakeRunResult("plain text")
        await context.search_pois()
        if context.menu_required and context.selected_curated_provider_ids:
            await context.read_menus()
        output = assemble_discovery_output(
            context.request,
            context.snapshot(),
        )
        if self.output_transform == "modified":
            candidate = output.candidates[0].model_copy(
                update={"canonical_name": "Invented name"}
            )
            output = output.model_copy(update={"candidates": (candidate,)})
        elif self.output_transform == "reversed":
            output = output.model_copy(
                update={"candidates": tuple(reversed(output.candidates))}
            )
        elif self.output_transform == "source":
            evidence = output.evidence.model_copy(
                update={"sources": ()}
            )
            output = output.model_copy(update={"evidence": evidence})
        return _FakeRunResult(output)


def _model_executor(
    provider: _FakeProvider,
    menu_reader: _FakeMenuReader,
    runner: _RegistryRunner,
) -> OpenAIDiscoveryExecutor:
    return OpenAIDiscoveryExecutor(
        provider,
        menu_reader,
        api_key="private-test-key",
        model="explicit-test-model",
        runner=runner,
    )


def test_request_maps_exactly_to_t032_without_reranking_inputs() -> None:
    request = _request()
    mapped = discovery_to_provider_request(request)

    assert mapped.city is request.city
    assert mapped.origin == request.origin
    assert mapped.radius_metres == request.radius_metres
    assert mapped.limit == request.limit
    assert mapped.query == request.query
    assert mapped.category == request.category


def test_deterministic_execution_preserves_provider_order_and_missing_fields() -> None:
    items = (
        _poi(
            "hcmc-poi-z",
            name="Gần hơn",
            distance=1.0,
            source=_source("hcmc-source-z"),
        ),
        _poi(
            "hcmc-poi-a",
            name="Xa hơn",
            distance=10.0,
            source=_source("hcmc-source-a"),
        ),
    )
    provider = _FakeProvider(_envelope(items))
    menu_reader = _FakeMenuReader()

    output = asyncio.run(
        DiscoveryService(provider, menu_reader).discover(_request())
    )

    assert [candidate.provider_id for candidate in output.candidates] == [
        "hcmc-poi-z",
        "hcmc-poi-a",
    ]
    assert [candidate.distance_metres for candidate in output.candidates] == [
        1.0,
        10.0,
    ]
    assert all(candidate.rating is None for candidate in output.candidates)
    assert all(
        candidate.opening_hours_summary is None
        for candidate in output.candidates
    )
    assert output.completeness is DiscoveryCompleteness.COMPLETE
    assert len(provider.calls) == 1
    assert menu_reader.calls == []


def test_evidence_is_deterministic_closed_unicode_and_has_no_distance_claim() -> None:
    request = _request(
        facts=(
            FactKind.CATEGORY,
            FactKind.DISTANCE,
            FactKind.IDENTITY,
            FactKind.LOCATION,
            FactKind.OPENING_HOURS,
            FactKind.RATING,
        )
    )
    item = _poi(
        name="Bảo tàng Việt Nam",
        source=_source(),
        address="28 Võ Văn Tần",
        rating=Decimal("4.50"),
        opening_hours="08:00–17:00",
    )
    snapshot = asyncio.run(_snapshot(request, _envelope((item,))))

    first = assemble_discovery_output(request, snapshot)
    second = assemble_discovery_output(request, snapshot)
    kinds = {claim.fact_kind for claim in first.evidence.claims}

    assert first.model_dump_json() == second.model_dump_json()
    assert kinds == {
        FactKind.CATEGORY,
        FactKind.IDENTITY,
        FactKind.LOCATION,
        FactKind.OPENING_HOURS,
        FactKind.RATING,
    }
    assert FactKind.DISTANCE not in kinds
    assert "Bảo tàng Việt Nam" in first.model_dump_json()
    assert first.evidence.source_ids == {"hcmc-source-a"}
    assert all(
        set(claim.supporting_source_ids).issubset(
            first.evidence.source_ids
        )
        for claim in first.evidence.claims
    )


async def _snapshot(
    request: DiscoveryRequest,
    envelope: PoiResultEnvelope,
    menu: MenuResultEnvelope | None = None,
) -> DiscoveryRegistrySnapshot:
    registry = DiscoveryRunRegistry(
        request,
        _FakeProvider(envelope),
        _FakeMenuReader(menu),
    )
    await registry.complete_missing_operations()
    return registry.snapshot()


def test_menu_and_price_use_selected_curated_identity_and_real_source() -> None:
    request = _request(
        facts=(FactKind.MENU_ITEM, FactKind.PRICE),
    )
    provider = _FakeProvider(_envelope())
    menu_reader = _FakeMenuReader(_menu())

    output = asyncio.run(
        DiscoveryService(provider, menu_reader).discover(request)
    )

    assert menu_reader.calls == [("hcmc-poi-a",)]
    claims = {claim.fact_kind: claim for claim in output.evidence.claims}
    assert set(claims) == {FactKind.MENU_ITEM, FactKind.PRICE}
    price = claims[FactKind.PRICE].price
    assert price is not None
    assert price.price_minor_units == 75_000
    assert price.currency == "VND"
    assert (
        price.source_updated_at
        == UPDATED
        == claims[FactKind.PRICE].freshness_at
    )
    assert claims[FactKind.PRICE].supporting_source_ids == (
        "hcmc-source-menu",
    )


def test_zero_menu_rows_are_complete_and_not_a_failure() -> None:
    request = _request(facts=(FactKind.MENU_ITEM, FactKind.PRICE))
    menu_reader = _FakeMenuReader(MenuResultEnvelope())

    output = asyncio.run(
        DiscoveryService(_FakeProvider(_envelope()), menu_reader).discover(
            request
        )
    )

    assert menu_reader.calls == [("hcmc-poi-a",)]
    assert output.completeness is DiscoveryCompleteness.COMPLETE
    assert output.provider_failures == ()
    assert output.evidence.claims == ()


def test_menu_failure_retains_poi_evidence_as_partial() -> None:
    request = _request(
        facts=(
            FactKind.IDENTITY,
            FactKind.MENU_ITEM,
            FactKind.PRICE,
        )
    )
    menu_reader = _FakeMenuReader(
        MenuReaderError(MenuErrorCode.UNAVAILABLE)
    )

    output = asyncio.run(
        DiscoveryService(_FakeProvider(_envelope()), menu_reader).discover(
            request
        )
    )

    assert len(output.candidates) == 1
    assert {claim.fact_kind for claim in output.evidence.claims} == {
        FactKind.IDENTITY
    }
    assert output.completeness is DiscoveryCompleteness.PARTIAL
    assert output.provider_failures[0].code is FailureCode.PROVIDER_UNAVAILABLE


def test_truncation_is_partial_but_optional_missing_facts_are_not() -> None:
    truncated = asyncio.run(
        DiscoveryService(
            _FakeProvider(_envelope(is_complete=False)),
            _FakeMenuReader(),
        ).discover(_request(facts=(FactKind.RATING,)))
    )
    missing = asyncio.run(
        DiscoveryService(
            _FakeProvider(_envelope()),
            _FakeMenuReader(),
        ).discover(_request(facts=(FactKind.RATING,)))
    )

    assert truncated.completeness is DiscoveryCompleteness.PARTIAL
    assert truncated.is_truncated is True
    assert truncated.evidence.claims == ()
    assert missing.completeness is DiscoveryCompleteness.COMPLETE
    assert missing.provider_failures == ()


def test_empty_success_is_complete() -> None:
    output = asyncio.run(
        DiscoveryService(
            _FakeProvider(_envelope(())),
            _FakeMenuReader(),
        ).discover(_request())
    )

    assert output.candidates == ()
    assert output.evidence.sources == ()
    assert output.completeness is DiscoveryCompleteness.COMPLETE


@pytest.mark.parametrize(
    ("provider_code", "failure_code"),
    [
        (ProviderErrorCode.TIMEOUT, FailureCode.PROVIDER_TIMEOUT),
        (ProviderErrorCode.UNAVAILABLE, FailureCode.PROVIDER_UNAVAILABLE),
        (ProviderErrorCode.INVALID_RESPONSE, FailureCode.INVALID_OUTPUT),
    ],
)
def test_total_provider_failure_is_sanitized_typed_error(
    provider_code: ProviderErrorCode,
    failure_code: FailureCode,
) -> None:
    raw = "raw private provider exception"
    provider_error = PoiProviderError(
        ProviderFailure.for_code(
            PoiProviderKind.CURATED,
            provider_code,
        )
    )
    provider_error.__cause__ = RuntimeError(raw)

    with pytest.raises(DiscoveryExecutionError) as captured:
        asyncio.run(
            DiscoveryService(
                _FakeProvider(provider_error),
                _FakeMenuReader(),
            ).discover(_request())
        )

    assert captured.value.failure.code is failure_code
    assert raw not in str(captured.value)
    assert raw not in captured.value.failure.model_dump_json()


def test_invalid_provider_result_fails_closed() -> None:
    with pytest.raises(DiscoveryExecutionError) as captured:
        asyncio.run(
            DiscoveryService(
                _FakeProvider({"raw": "invalid"}),
                _FakeMenuReader(),
            ).discover(_request())
        )
    assert captured.value.failure.code is FailureCode.INVALID_OUTPUT


def test_repeated_or_unauthorized_tool_calls_are_rejected_without_new_reads() -> None:
    provider = _FakeProvider(_envelope())
    menu_reader = _FakeMenuReader()
    registry = DiscoveryRunRegistry(
        _request(),
        provider,
        menu_reader,
    )

    asyncio.run(registry.search_pois())
    with pytest.raises(ToolInvocationError):
        asyncio.run(registry.search_pois())
    with pytest.raises(ToolInvocationError):
        asyncio.run(registry.read_menus())

    assert len(provider.calls) == 1
    assert menu_reader.calls == []


def test_sdk_configuration_has_exactly_two_tools_and_no_runtime_state() -> None:
    provider = _FakeProvider(_envelope())
    menu_reader = _FakeMenuReader()
    runner = _RegistryRunner("valid")

    output = asyncio.run(
        _model_executor(provider, menu_reader, runner).discover(_request())
    )

    assert len(output.candidates) == 1
    assert len(runner.calls) == 1
    agent, _, _, max_turns, run_config = runner.calls[0]
    assert agent.output_type is DiscoveryOutput
    assert [tool.name for tool in agent.tools] == [
        "normalized_poi_search",
        "normalized_menu_lookup",
    ]
    function_tools = [tool for tool in agent.tools if isinstance(tool, FunctionTool)]
    assert len(function_tools) == 2
    assert all(
        tool.params_json_schema["properties"] == {}
        for tool in function_tools
    )
    assert agent.handoffs == []
    assert agent.mcp_servers == []
    assert agent.model == "explicit-test-model"
    assert agent.model_settings.tool_choice == "auto"
    assert agent.model_settings.parallel_tool_calls is False
    assert agent.model_settings.retry is not None
    assert agent.model_settings.retry.max_retries == 0
    assert agent.model_settings.temperature is None
    assert agent.model_settings.reasoning is None
    assert max_turns == DISCOVERY_MAX_TURNS == 3
    assert run_config.tracing_disabled is True
    assert run_config.trace_include_sensitive_data is False
    assert run_config.session_settings is None


def test_default_sdk_runner_passes_no_session_or_response_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_run(
        starting_agent: Agent[DiscoveryRunRegistry],
        model_input: str,
        **kwargs: object,
    ) -> _FakeRunResult:
        captured["agent"] = starting_agent
        captured["input"] = model_input
        captured["kwargs"] = kwargs
        return _FakeRunResult("plain text")

    monkeypatch.setattr(
        "app.agents.discovery.executor.Runner.run",
        fake_run,
    )
    provider = _FakeProvider(_envelope())
    output = asyncio.run(
        OpenAIDiscoveryExecutor(
            provider,
            _FakeMenuReader(),
            api_key="private-test-key",
            model="explicit-test-model",
        ).discover(_request())
    )

    assert len(output.candidates) == 1
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert set(kwargs) == {"context", "max_turns", "run_config"}
    for forbidden in (
        "session",
        "conversation_id",
        "previous_response_id",
        "auto_previous_response_id",
        "hooks",
    ):
        assert forbidden not in kwargs


def test_model_input_excludes_origin_query_and_sensitive_values() -> None:
    serialized = serialize_discovery_request(_request())
    parsed = json.loads(serialized)

    assert parsed == {
        "city": "hcmc",
        "limit": 5,
        "radius_metres": 5_000,
        "requested_fact_kinds": ["category", "identity"],
    }
    for forbidden in (
        "latitude",
        "longitude",
        "phở",
        "uid",
        "email",
        "token",
        "database",
        "provider",
        "model",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "transform",
    ["modified", "reversed", "source"],
)
def test_model_modified_candidate_order_or_evidence_falls_back(
    transform: str,
) -> None:
    items = (
        _poi(
            "hcmc-poi-z",
            distance=1.0,
            source=_source("hcmc-source-z"),
        ),
        _poi(
            "hcmc-poi-a",
            distance=2.0,
            source=_source("hcmc-source-a"),
        ),
    )
    provider = _FakeProvider(_envelope(items))
    runner = _RegistryRunner("valid", transform)

    output = asyncio.run(
        _model_executor(provider, _FakeMenuReader(), runner).discover(
            _request()
        )
    )

    assert [item.provider_id for item in output.candidates] == [
        "hcmc-poi-z",
        "hcmc-poi-a",
    ]
    assert len(provider.calls) == 1
    assert output.evidence.sources


@pytest.mark.parametrize("behavior", ["raise", "no_tools"])
def test_model_failure_or_plain_text_uses_same_registry_without_retry(
    behavior: str,
) -> None:
    provider = _FakeProvider(_envelope())
    runner = _RegistryRunner(behavior)

    output = asyncio.run(
        _model_executor(provider, _FakeMenuReader(), runner).discover(
            _request()
        )
    )

    assert len(output.candidates) == 1
    assert len(runner.calls) == 1
    assert len(provider.calls) == 1


def test_cancellation_propagates_without_provider_fallback() -> None:
    provider = _FakeProvider(_envelope())

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            _model_executor(
                provider,
                _FakeMenuReader(),
                _RegistryRunner("cancel"),
            ).discover(_request())
        )

    assert provider.calls == []


def test_service_logs_only_safe_summary(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.discovery",
    )
    query = "phở riêng tư"
    request = _request(query=query)

    asyncio.run(
        DiscoveryService(
            _FakeProvider(_envelope()),
            _FakeMenuReader(),
        ).discover(request)
    )

    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "operation=discover path=deterministic city=hcmc candidates=1" in logs
    for private in (
        query,
        "10.7799",
        "106.7",
        "hcmc-poi-a",
        "Nguồn chính thức",
        "https://",
    ):
        assert private not in logs


def test_private_tool_models_are_strict_frozen_and_have_no_escape_hatch() -> None:
    model_types = {
        model
        for model in (
            ToolCoordinates,
            ToolSource,
            PoiToolCandidate,
            PoiToolResult,
            MenuItemResult,
            MenuResultEnvelope,
            DiscoveryRegistrySnapshot,
        )
        if issubclass(model, PrivateToolModel)
    }
    forbidden = {"raw", "payload", "metadata", "any"}

    for model_type in model_types:
        assert model_type.model_config["extra"] == "forbid"
        assert model_type.model_config["frozen"] is True
        assert model_type.model_config["strict"] is True
        assert forbidden.isdisjoint(model_type.model_fields)
        assert "additionalProperties" in json.dumps(
            model_type.model_json_schema()
        )

    with pytest.raises(ValidationError):
        MenuResultEnvelope.model_validate(
            {"items": [], "raw": {"escape": True}}
        )


def test_static_instructions_lock_no_prose_invention_order_and_origin() -> None:
    normalized = " ".join(DISCOVERY_INSTRUCTIONS.casefold().split())
    for required in (
        "only the discovery agent",
        "return only the discoveryoutput",
        "never write final user-facing travel prose",
        "always call normalized_poi_search exactly once",
        "normalized_menu_lookup at most once",
        "preserve the exact candidate order",
        "never invent",
        "missing fields must remain missing",
        "never expose the request origin",
        "chain of thought",
        "no final prose",
    ):
        assert required in normalized


@pytest.mark.parametrize(
    ("api_key", "model"),
    [
        (None, None),
        ("", "model"),
        ("key", ""),
        ("  ", "model"),
        ("key", "  "),
    ],
)
def test_missing_model_configuration_selects_deterministic(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    model: str | None,
) -> None:
    if api_key is None:
        monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_API_KEY_ENV, api_key)
    if model is None:
        monkeypatch.delenv(OPENAI_DISCOVERY_MODEL_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_DISCOVERY_MODEL_ENV, model)
    provider = _FakeProvider(_envelope())

    output = asyncio.run(
        DiscoveryService(provider, _FakeMenuReader()).discover(_request())
    )

    assert len(output.candidates) == 1
    assert len(provider.calls) == 1


def test_package_import_needs_no_environment_or_network() -> None:
    script = """
import socket
def blocked(*args, **kwargs):
    raise AssertionError("network")
socket.create_connection = blocked
socket.socket.connect = blocked
import app.agents.discovery
print("ok")
"""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            OPENAI_API_KEY_ENV,
            OPENAI_DISCOVERY_MODEL_ENV,
            "DATABASE_URL",
            "FIREBASE_PROJECT_ID",
        }
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_discovery_output_has_no_origin_or_final_prose_field() -> None:
    fields = set(DiscoveryOutput.model_fields)
    assert "origin" not in fields
    assert "final_text" not in fields
    assert "prose" not in fields
