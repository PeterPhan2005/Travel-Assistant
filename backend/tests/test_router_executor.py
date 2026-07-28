"""SDK adapter, service fallback, import, and privacy tests for T041."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from agents import Agent, RunConfig

from app.agents.contracts import (
    IntentKind,
    RouterEntities,
    RouterOutput,
    RouterRequest,
    SpecialistKind,
    SupportedCity,
)
from app.agents.router import OpenAIRouterExecutor, RouterService
from app.agents.router.executor import (
    OPENAI_API_KEY_ENV,
    OPENAI_ROUTER_MODEL_ENV,
    ROUTER_MAX_TURNS,
)
from app.agents.router.instructions import ROUTER_INSTRUCTIONS
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.preferences.contracts import PreferenceDocument
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def _request(query: str = "Tìm địa điểm gần đây") -> RouterRequest:
    return RouterRequest(
        user_query=query,
        locale="vi-VN",
        city=SupportedCity.HCMC,
        preferences=PreferenceDocument(
            schema_version=1,
            preferences={"pace": "chậm"},
        ),
    )


def _model_output() -> RouterOutput:
    return RouterOutput(
        primary_intent=IntentKind.NEARBY_DISCOVERY,
        entities=RouterEntities(city=SupportedCity.HCMC),
        specialist_plan=(SpecialistKind.DISCOVERY,),
        discovery_required=True,
        clarification_reason=None,
    )


@dataclass
class _FakeRunResult:
    final_output: object


class _RecordingRunner:
    def __init__(
        self,
        result: _FakeRunResult | Exception | BaseException,
    ) -> None:
        self.result = result
        self.calls: list[
            tuple[Agent[None], str, int, RunConfig]
        ] = []

    async def run(
        self,
        starting_agent: Agent[None],
        model_input: str,
        *,
        max_turns: int,
        run_config: RunConfig,
    ) -> _FakeRunResult:
        self.calls.append(
            (starting_agent, model_input, max_turns, run_config)
        )
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _executor(
    runner: _RecordingRunner,
    *,
    api_key: str = "private-test-key",
    model: str = "explicit-test-model",
) -> OpenAIRouterExecutor:
    return OpenAIRouterExecutor(
        api_key=api_key,
        model=model,
        runner=runner,
    )


def test_sdk_agent_and_run_configuration_are_locked_down() -> None:
    runner = _RecordingRunner(_FakeRunResult(_model_output()))
    output = asyncio.run(_executor(runner).route(_request()))

    assert output == _model_output()
    assert len(runner.calls) == 1
    agent, _, max_turns, run_config = runner.calls[0]
    assert agent.name == "travel_intent_router"
    assert agent.output_type is RouterOutput
    assert agent.tools == []
    assert agent.handoffs == []
    assert agent.mcp_servers == []
    assert agent.model == "explicit-test-model"
    assert agent.model_settings.tool_choice == "none"
    assert agent.model_settings.parallel_tool_calls is False
    assert agent.model_settings.temperature is None
    assert agent.model_settings.reasoning is None
    assert agent.model_settings.retry is not None
    assert agent.model_settings.retry.max_retries == 0
    assert max_turns == ROUTER_MAX_TURNS == 1
    assert run_config.tracing_disabled is True
    assert run_config.trace_include_sensitive_data is False
    assert run_config.trace_id is None
    assert run_config.group_id is None
    assert run_config.trace_metadata is None
    assert run_config.session_settings is None


def test_model_path_receives_only_compact_serialized_router_request() -> None:
    request = _request("Tìm phở gần đây ở Hồ Chí Minh")
    runner = _RecordingRunner(_FakeRunResult(_model_output()))

    asyncio.run(_executor(runner).route(request))

    _, model_input, _, _ = runner.calls[0]
    assert json.loads(model_input) == request.model_dump(mode="json")
    assert set(json.loads(model_input)) == set(RouterRequest.model_fields)
    assert "Hồ Chí Minh" in model_input
    assert " " not in model_input.split(":", maxsplit=1)[0]
    for forbidden in (
        "uid",
        "email",
        "firebase_claim",
        "token",
        "latitude",
        "longitude",
        "transcript",
        "database",
        "provider",
    ):
        assert forbidden not in json.loads(model_input)


def test_default_sdk_runner_supplies_no_session_or_response_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_run(
        starting_agent: Agent[None],
        model_input: str,
        **kwargs: object,
    ) -> _FakeRunResult:
        captured["agent"] = starting_agent
        captured["input"] = model_input
        captured["kwargs"] = kwargs
        return _FakeRunResult(_model_output())

    monkeypatch.setattr(
        "app.agents.router.executor.Runner.run",
        fake_run,
    )

    output = asyncio.run(
        OpenAIRouterExecutor(
            api_key="private-test-key",
            model="explicit-test-model",
        ).route(_request())
    )

    assert output == _model_output()
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert set(kwargs) == {"max_turns", "run_config"}
    for forbidden in (
        "session",
        "conversation_id",
        "previous_response_id",
        "auto_previous_response_id",
        "context",
        "hooks",
    ):
        assert forbidden not in kwargs


def test_static_instructions_forbid_answers_facts_reasoning_and_invention() -> None:
    normalized = " ".join(ROUTER_INSTRUCTIONS.casefold().split())

    for required in (
        "vietnamese-first travel assistant",
        "return only the routeroutput structured schema",
        "never answer the travel question",
        "state destination facts",
        "expose reasoning",
        "never invent a city, poi id, category, constraint, or preference",
        "general travel help schedules no specialist",
        "unsupported or non-travel input",
        "do not include tools",
    ):
        assert required in normalized


def test_valid_structured_model_output_is_revalidated_and_returned() -> None:
    expected = _model_output()
    runner = _RecordingRunner(_FakeRunResult(expected))
    service = RouterService(
        executor_factory=lambda: _executor(runner)
    )

    actual = asyncio.run(service.route(_request()))

    assert actual == expected
    assert actual is not expected
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    "unexpected_output",
    [
        "nearby_discovery",
        {
            "primary_intent": "nearby_discovery",
            "specialist_plan": ["discovery"],
        },
        42,
    ],
)
def test_plain_text_and_unexpected_sdk_outputs_fall_back(
    unexpected_output: object,
) -> None:
    runner = _RecordingRunner(_FakeRunResult(unexpected_output))
    service = RouterService(
        executor_factory=lambda: _executor(runner)
    )

    output = asyncio.run(service.route(_request()))

    assert output.primary_intent is IntentKind.NEARBY_DISCOVERY
    assert output == asyncio.run(
        RouterService(executor_factory=lambda: None).route(_request())
    )
    assert len(runner.calls) == 1


def test_contract_invalid_model_instance_falls_back() -> None:
    invalid = _model_output().model_copy(
        update={
            "specialist_plan": (),
            "discovery_required": False,
        }
    )
    runner = _RecordingRunner(_FakeRunResult(invalid))
    service = RouterService(
        executor_factory=lambda: _executor(runner)
    )

    output = asyncio.run(service.route(_request()))

    assert output.specialist_plan == (SpecialistKind.DISCOVERY,)
    assert output.discovery_required is True
    assert len(runner.calls) == 1


def test_ordinary_sdk_exception_falls_back_without_retry_or_leak(
    caplog: pytest.LogCaptureFixture,
) -> None:
    query = "private query tìm nơi gần đây"
    private_error = "raw private model response and credential"
    runner = _RecordingRunner(RuntimeError(private_error))
    service = RouterService(
        executor_factory=lambda: _executor(
            runner,
            api_key="private-api-key",
            model="private-model-name",
        )
    )
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.router",
    )

    output = asyncio.run(service.route(_request(query)))

    assert output.primary_intent is IntentKind.NEARBY_DISCOVERY
    assert len(runner.calls) == 1
    combined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "operation=route path=fallback reason=model_failure" in combined_logs
    for private_value in (
        query,
        "chậm",
        private_error,
        "private-api-key",
        "private-model-name",
        "RuntimeError",
    ):
        assert private_value not in combined_logs


def test_cancellation_propagates_and_does_not_trigger_fallback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner = _RecordingRunner(asyncio.CancelledError())
    service = RouterService(
        executor_factory=lambda: _executor(runner)
    )
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.router",
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(service.route(_request()))

    assert len(runner.calls) == 1
    assert not caplog.records


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
def test_missing_or_blank_model_configuration_selects_fallback(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    model: str | None,
) -> None:
    if api_key is None:
        monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_API_KEY_ENV, api_key)
    if model is None:
        monkeypatch.delenv(OPENAI_ROUTER_MODEL_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_ROUTER_MODEL_ENV, model)

    output = asyncio.run(RouterService().route(_request()))

    assert output.primary_intent is IntentKind.NEARBY_DISCOVERY


def test_configuration_is_read_lazily_at_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    monkeypatch.delenv(OPENAI_ROUTER_MODEL_ENV, raising=False)
    service = RouterService()
    monkeypatch.setenv(OPENAI_API_KEY_ENV, "later-key")
    monkeypatch.setenv(OPENAI_ROUTER_MODEL_ENV, "later-model")
    created = OpenAIRouterExecutor.from_environment()

    assert created is not None
    monkeypatch.delenv(OPENAI_API_KEY_ENV)
    monkeypatch.delenv(OPENAI_ROUTER_MODEL_ENV)
    output = asyncio.run(service.route(_request()))
    assert output.primary_intent is IntentKind.NEARBY_DISCOVERY


def test_package_import_requires_no_environment_and_performs_no_network() -> None:
    code = """\
import socket
def blocked(*args, **kwargs):
    raise AssertionError("network attempted during import")
socket.socket.connect = blocked
socket.create_connection = blocked
import app.agents.router
"""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            OPENAI_API_KEY_ENV,
            OPENAI_ROUTER_MODEL_ENV,
            "DATABASE_URL",
            "FIREBASE_PROJECT_ID",
        }
    }

    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_runtime_dependency_is_exactly_pinned() -> None:
    requirements = (BACKEND / "requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines()

    assert requirements.count("openai-agents==0.18.3") == 1
    assert not any(
        line.startswith("openai-agents")
        and line != "openai-agents==0.18.3"
        for line in requirements
    )


def test_no_agent_route_or_global_openai_settings_were_added() -> None:
    settings = Settings(
        database_url=SecretStr(
            "postgresql+asyncpg://unused:never-connect@"
            "database.invalid:9999/unused"
        ),
        firebase_project_id="travel-assistant-test",
        application_environment=ApplicationEnvironment.TEST,
    )
    paths = set(create_app(settings).openapi()["paths"])

    assert paths == {
        "/health",
        "/auth/me",
        "/preferences",
        "/pois/nearby",
    }
    assert OPENAI_API_KEY_ENV.casefold() not in Settings.model_fields
    assert OPENAI_ROUTER_MODEL_ENV.casefold() not in Settings.model_fields


def test_router_models_have_no_sensitive_or_escape_hatch_fields() -> None:
    forbidden = {
        "uid",
        "email",
        "token",
        "password",
        "reasoning",
        "raw",
        "payload",
        "metadata",
        "session",
        "trace",
        "usage",
    }

    for model in (RouterRequest, RouterEntities, RouterOutput):
        assert forbidden.isdisjoint(model.model_fields)


def test_router_package_does_not_configure_verbose_sdk_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def record_call() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(
        "agents.enable_verbose_stdout_logging",
        record_call,
    )
    runner = _RecordingRunner(_FakeRunResult(_model_output()))

    asyncio.run(_executor(runner).route(_request()))

    assert called is False
