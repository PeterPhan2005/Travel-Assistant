"""Source closure, SDK isolation, fallback, and privacy tests for T043."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest
from agents import Agent, RunConfig
from pydantic import HttpUrl, SecretStr, ValidationError

from app.agents.contracts import (
    AnswerStatus,
    EvidenceBundle,
    FactKind,
    FactualClaim,
    NarrationOutput,
    NarrationRequest,
    NarrationWordRange,
    PoiIdentity,
    SourceRecord,
    SourceType,
    SupportedCity,
)
from app.agents.narration import (
    NarrationLimitationReason,
    NarrationService,
    OpenAINarrationExecutor,
    build_limited_narration,
)
from app.agents.narration.executor import (
    NARRATION_MAX_TURNS,
    OPENAI_API_KEY_ENV,
    OPENAI_NARRATION_MODEL_ENV,
    serialize_narration_request,
)
from app.agents.narration.instructions import NARRATION_INSTRUCTIONS
from app.agents.narration.validation import validate_narration_output
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
NOW = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)


def _source(source_id: str) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_INSTITUTION,
        label=f"Nhãn nguồn riêng {source_id}",
        publisher="Đơn vị quản lý riêng",
        url=HttpUrl(f"https://example.test/{source_id}"),
        published_at=None,
        retrieved_at=NOW,
    )


def _claim(
    claim_id: str,
    *,
    source_ids: tuple[str, ...],
    poi_id: str | None = "curated:hcmc-poi-a",
    statement: str | None = None,
) -> FactualClaim:
    return FactualClaim(
        claim_id=claim_id,
        evidence_id=f"evidence-{claim_id}",
        fact_kind=FactKind.HISTORY,
        statement=statement or f"Sự kiện được xác nhận cho {claim_id}.",
        supporting_source_ids=source_ids,
        poi_id=poi_id,
        freshness_at=NOW,
        price=None,
    )


def _request(
    *,
    sources: tuple[SourceRecord, ...] | None = None,
    claims: tuple[FactualClaim, ...] | None = None,
    minimum_words: int = 100,
    maximum_words: int = 200,
) -> NarrationRequest:
    resolved_sources = (
        sources
        if sources is not None
        else (_source("source-a"), _source("source-b"))
    )
    resolved_claims = (
        claims
        if claims is not None
        else (
            _claim("claim-a", source_ids=("source-a",)),
            _claim(
                "claim-b",
                source_ids=("source-a", "source-b"),
                statement="Địa điểm có hai nguồn cùng xác nhận.",
            ),
        )
    )
    return NarrationRequest(
        poi=PoiIdentity(
            poi_id="curated:hcmc-poi-a",
            canonical_name="Điểm đến Việt Nam riêng",
            city=SupportedCity.HCMC,
            category="museum",
        ),
        evidence=EvidenceBundle(
            sources=resolved_sources,
            claims=resolved_claims,
        ),
        locale="vi-VN",
        word_range=NarrationWordRange(
            minimum_words=minimum_words,
            maximum_words=maximum_words,
        ),
    )


def _words(count: int, *, first: str = "Việt") -> str:
    return " ".join([first, *(f"từ{index}" for index in range(count - 1))])


def _complete_output(
    count: int = 100,
    *,
    used_claim_ids: tuple[str, ...] = ("claim-a",),
    used_source_ids: tuple[str, ...] = ("source-a",),
    key_points: tuple[str, ...] = ("Lịch sử được xác nhận",),
) -> NarrationOutput:
    return NarrationOutput(
        status=AnswerStatus.COMPLETE,
        narration_text=_words(count),
        key_points=key_points,
        used_source_ids=used_source_ids,
        used_claim_ids=used_claim_ids,
        limitation_reason=None,
    )


def _limited_output() -> NarrationOutput:
    return NarrationOutput(
        status=AnswerStatus.LIMITED,
        narration_text=None,
        key_points=(),
        used_source_ids=(),
        used_claim_ids=(),
        limitation_reason="Chưa có đủ nội dung được xác nhận.",
    )


@dataclass
class _FakeRunResult:
    final_output: object


class _RecordingRunner:
    def __init__(
        self,
        result: _FakeRunResult | BaseException,
    ) -> None:
        self.result = result
        self.calls: list[tuple[Agent[None], str, int, RunConfig]] = []

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
    model: str = "private-test-model",
) -> OpenAINarrationExecutor:
    return OpenAINarrationExecutor(
        api_key=api_key,
        model=model,
        runner=runner,
    )


def _service(runner: _RecordingRunner) -> NarrationService:
    return NarrationService(executor_factory=lambda: _executor(runner))


def test_sdk_agent_and_run_configuration_are_locked_down() -> None:
    runner = _RecordingRunner(_FakeRunResult(_complete_output()))

    output = asyncio.run(_executor(runner).narrate(_request()))

    assert output.status is AnswerStatus.COMPLETE
    assert len(runner.calls) == 1
    agent, _, max_turns, run_config = runner.calls[0]
    assert agent.name == "travel_narration"
    assert agent.output_type is NarrationOutput
    assert agent.tools == []
    assert agent.handoffs == []
    assert agent.mcp_servers == []
    assert agent.model == "private-test-model"
    assert agent.model_settings.tool_choice == "none"
    assert agent.model_settings.parallel_tool_calls is False
    assert agent.model_settings.temperature is None
    assert agent.model_settings.reasoning is None
    assert agent.model_settings.retry is not None
    assert agent.model_settings.retry.max_retries == 0
    assert max_turns == NARRATION_MAX_TURNS == 1
    assert run_config.tracing_disabled is True
    assert run_config.trace_include_sensitive_data is False
    assert run_config.trace_id is None
    assert run_config.group_id is None
    assert run_config.trace_metadata is None
    assert run_config.session_settings is None


def test_default_runner_passes_no_session_or_response_state(
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
        return _FakeRunResult(_complete_output())

    monkeypatch.setattr(
        "app.agents.narration.executor.Runner.run",
        fake_run,
    )

    output = asyncio.run(
        OpenAINarrationExecutor(
            api_key="private-test-key",
            model="private-test-model",
        ).narrate(_request())
    )

    assert output.status is AnswerStatus.COMPLETE
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


def test_serialization_is_compact_unicode_and_approved_only() -> None:
    request = _request(
        claims=(
            _claim(
                "claim-a",
                source_ids=("source-a",),
                statement="Lịch sử tiếng Việt được xác nhận.",
            ),
            _claim(
                "claim-unscoped",
                source_ids=("source-b",),
                poi_id=None,
                statement="Không được gửi vì chưa gắn POI.",
            ),
        )
    )

    serialized = serialize_narration_request(request)
    parsed = json.loads(serialized)

    assert set(parsed) == {
        "claims",
        "locale",
        "poi",
        "source_ids",
        "word_range",
    }
    assert parsed["source_ids"] == ["source-a"]
    assert [claim["claim_id"] for claim in parsed["claims"]] == ["claim-a"]
    assert "Lịch sử tiếng Việt" in serialized
    assert "claim-unscoped" not in serialized
    assert "Không được gửi" not in serialized
    for forbidden in (
        "https://",
        "Nhãn nguồn riêng",
        "Đơn vị quản lý riêng",
        "uid",
        "email",
        "token",
        "latitude",
        "longitude",
        "database",
        "provider",
        "query",
        "transcript",
    ):
        assert forbidden not in serialized
    assert serialized == json.dumps(
        parsed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def test_no_claims_sources_only_or_unscoped_claims_return_limited_without_factory() -> None:
    requests = (
        _request(sources=(), claims=()),
        _request(sources=(_source("source-a"),), claims=()),
        _request(
            sources=(_source("source-a"),),
            claims=(
                _claim(
                    "claim-unscoped",
                    source_ids=("source-a",),
                    poi_id=None,
                ),
            ),
        ),
    )
    calls = 0

    def forbidden_factory() -> OpenAINarrationExecutor:
        nonlocal calls
        calls += 1
        raise AssertionError("executor factory must not be called")

    service = NarrationService(executor_factory=forbidden_factory)
    outputs = [
        asyncio.run(service.narrate(request))
        for request in requests
    ]

    assert calls == 0
    assert all(output.status is AnswerStatus.LIMITED for output in outputs)
    assert all(output.narration_text is None for output in outputs)
    assert all(output.key_points == () for output in outputs)
    assert all(output.used_claim_ids == () for output in outputs)
    assert all(output.used_source_ids == () for output in outputs)


def test_request_rejects_claim_for_another_poi() -> None:
    with pytest.raises(ValidationError):
        _request(
            sources=(_source("source-a"),),
            claims=(
                _claim(
                    "claim-other",
                    source_ids=("source-a",),
                    poi_id="curated:hcmc-poi-other",
                ),
            ),
        )


@pytest.mark.parametrize("count", [100, 200])
def test_exact_product_word_boundaries_pass(count: int) -> None:
    runner = _RecordingRunner(_FakeRunResult(_complete_output(count)))

    output = asyncio.run(_service(runner).narrate(_request()))

    assert output.status is AnswerStatus.COMPLETE
    assert output.narration_text is not None
    assert len(output.narration_text.split()) == count
    assert "Việt" in output.narration_text
    assert len(runner.calls) == 1


@pytest.mark.parametrize("count", [99, 201])
def test_invalid_product_word_counts_fall_back(count: int) -> None:
    invalid = _complete_output().model_copy(
        update={"narration_text": _words(count)}
    )
    runner = _RecordingRunner(_FakeRunResult(invalid))

    output = asyncio.run(_service(runner).narrate(_request()))

    assert output.status is AnswerStatus.LIMITED
    assert output.narration_text is None
    assert len(runner.calls) == 1


def test_narrower_requested_word_range_is_enforced() -> None:
    request = _request(minimum_words=120, maximum_words=130)
    accepted = _RecordingRunner(_FakeRunResult(_complete_output(120)))
    rejected = _RecordingRunner(_FakeRunResult(_complete_output(100)))

    assert (
        asyncio.run(_service(accepted).narrate(request)).status
        is AnswerStatus.COMPLETE
    )
    assert (
        asyncio.run(_service(rejected).narrate(request)).status
        is AnswerStatus.LIMITED
    )


def test_exact_source_union_is_required() -> None:
    request = _request()
    missing_source = _complete_output(
        used_claim_ids=("claim-b",),
        used_source_ids=("source-a",),
    )
    exact = _complete_output(
        used_claim_ids=("claim-b",),
        used_source_ids=("source-a", "source-b"),
    )

    with pytest.raises(ValueError):
        validate_narration_output(missing_source, request)
    assert validate_narration_output(exact, request) == exact


@pytest.mark.parametrize(
    ("claim_ids", "source_ids"),
    [
        (("claim-unknown",), ("source-a",)),
        (("claim-a",), ("source-unknown",)),
        (("claim-a",), ("source-a", "source-b")),
    ],
)
def test_unknown_or_unrelated_references_fall_back(
    claim_ids: tuple[str, ...],
    source_ids: tuple[str, ...],
) -> None:
    invalid = _complete_output().model_copy(
        update={
            "used_claim_ids": claim_ids,
            "used_source_ids": source_ids,
        }
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).narrate(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.used_claim_ids == ()
    assert output.used_source_ids == ()


def test_key_points_must_be_unique_after_unicode_whitespace_casefolding() -> None:
    invalid = _complete_output().model_copy(
        update={
            "key_points": (
                "Lịch sử  được xác nhận",
                "LỊCH SỬ ĐƯỢC XÁC NHẬN",
            )
        }
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).narrate(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED


@pytest.mark.parametrize(
    "invalid_text",
    [
        "<p>Nội dung</p>",
        "# Tiêu đề",
        "- Gạch đầu dòng",
        "```python\nprint('x')\n```",
        "| Cột A | Cột B |",
        "Xem [nguồn](https://example.test)",
        "&lt;p&gt;Nội dung&lt;/p&gt;",
        "Nội dung nhắc đến prompt nội bộ.",
        "Nội dung nhắc đến SDK nội bộ.",
        "Nội dung nhắc đến model output.",
    ],
)
def test_html_markdown_and_internal_terms_fall_back(
    invalid_text: str,
) -> None:
    invalid = _complete_output().model_copy(
        update={
            "narration_text": " ".join(
                [invalid_text, *(_words(100).split()[1:])]
            )
        }
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).narrate(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.narration_text is None


def test_valid_structured_limited_output_passes_without_fabrication() -> None:
    expected = _limited_output()
    runner = _RecordingRunner(_FakeRunResult(expected))

    output = asyncio.run(_service(runner).narrate(_request()))

    assert output == expected
    assert output is not expected
    assert output.narration_text is None
    assert output.key_points == ()
    assert output.used_claim_ids == ()
    assert output.used_source_ids == ()


@pytest.mark.parametrize("unexpected", ["plain text", {"status": "complete"}, 7])
def test_plain_text_and_unexpected_outputs_fall_back(unexpected: object) -> None:
    runner = _RecordingRunner(_FakeRunResult(unexpected))

    output = asyncio.run(_service(runner).narrate(_request()))

    assert output.status is AnswerStatus.LIMITED
    assert output.narration_text is None
    assert len(runner.calls) == 1


def test_sdk_failure_is_deterministic_limited_without_retry() -> None:
    runner = _RecordingRunner(RuntimeError("raw private response"))
    executor = _executor(runner)
    request = _request()

    first = asyncio.run(executor.narrate(request))
    second_runner = _RecordingRunner(RuntimeError("different raw response"))
    second = asyncio.run(_executor(second_runner).narrate(request))

    assert first.status is AnswerStatus.LIMITED
    assert first.model_dump_json() == second.model_dump_json()
    assert len(runner.calls) == 1
    assert len(second_runner.calls) == 1


def test_cancellation_propagates_without_fallback_or_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner = _RecordingRunner(asyncio.CancelledError())
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.narration",
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_service(runner).narrate(_request()))

    assert len(runner.calls) == 1
    assert not caplog.records


def test_pure_fallback_is_byte_deterministic_and_content_free() -> None:
    request = _request()
    outputs = [
        build_limited_narration(
            request,
            NarrationLimitationReason.INSUFFICIENT_EVIDENCE,
        )
        for _ in range(2)
    ]

    assert outputs[0].model_dump_json() == outputs[1].model_dump_json()
    assert outputs[0].status is AnswerStatus.LIMITED
    assert outputs[0].narration_text is None
    assert outputs[0].key_points == ()
    assert outputs[0].used_claim_ids == ()
    assert outputs[0].used_source_ids == ()
    reason = outputs[0].limitation_reason
    assert reason is not None
    assert "api" not in reason.casefold()
    assert "model" not in reason.casefold()


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
def test_missing_or_blank_configuration_returns_limited(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    model: str | None,
) -> None:
    if api_key is None:
        monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_API_KEY_ENV, api_key)
    if model is None:
        monkeypatch.delenv(OPENAI_NARRATION_MODEL_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_NARRATION_MODEL_ENV, model)

    output = asyncio.run(NarrationService().narrate(_request()))

    assert output.status is AnswerStatus.LIMITED
    assert output.narration_text is None


def test_configuration_is_read_lazily(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    monkeypatch.delenv(OPENAI_NARRATION_MODEL_ENV, raising=False)
    service = NarrationService()
    monkeypatch.setenv(OPENAI_API_KEY_ENV, "later-key")
    monkeypatch.setenv(OPENAI_NARRATION_MODEL_ENV, "later-model")
    assert OpenAINarrationExecutor.from_environment() is not None
    monkeypatch.delenv(OPENAI_API_KEY_ENV)
    monkeypatch.delenv(OPENAI_NARRATION_MODEL_ENV)

    output = asyncio.run(service.narrate(_request()))

    assert output.status is AnswerStatus.LIMITED


def test_safe_logs_exclude_evidence_content_ids_and_configuration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_error = "raw private exception response"
    runner = _RecordingRunner(RuntimeError(private_error))
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.narration",
    )

    output = asyncio.run(
        NarrationService(
            executor_factory=lambda: _executor(
                runner,
                api_key="private-key",
                model="private-model",
            )
        ).narrate(_request())
    )

    assert output.status is AnswerStatus.LIMITED
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "operation=narrate path=model status=limited" in logs
    for private in (
        private_error,
        "private-key",
        "private-model",
        "curated:hcmc-poi-a",
        "Điểm đến Việt Nam riêng",
        "claim-a",
        "source-a",
        "Sự kiện được xác nhận",
        "Nhãn nguồn riêng",
        "https://",
    ):
        assert private not in logs


def test_static_instructions_lock_grounding_plain_text_and_limited_shape() -> None:
    normalized = " ".join(NARRATION_INSTRUCTIONS.casefold().split())
    for required in (
        "only the narration agent",
        "vietnamese-first travel assistant",
        "return only the narrationoutput",
        "never perform discovery",
        "only factual claims explicitly supplied",
        "never add a fact from general knowledge",
        "never invent dates",
        "100 to 200 words inclusive",
        "unique concise key_points",
        "exactly the supporting source ids",
        "status=limited with no narration_text",
        "do not use html or markdown",
        "chain of thought",
        "response-composer content",
    ):
        assert required in normalized


def test_package_import_needs_no_environment_or_network() -> None:
    script = """
import socket
def blocked(*args, **kwargs):
    raise AssertionError("network")
socket.create_connection = blocked
socket.socket.connect = blocked
import app.agents.narration
print("ok")
"""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            OPENAI_API_KEY_ENV,
            OPENAI_NARRATION_MODEL_ENV,
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


def test_dependency_route_settings_and_public_shape_are_unchanged() -> None:
    requirements = (BACKEND / "requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    assert requirements.count("openai-agents==0.18.3") == 1

    settings = Settings(
        database_url=SecretStr(
            "postgresql+asyncpg://unused:never-connect@"
            "database.invalid:9999/unused"
        ),
        firebase_project_id="travel-assistant-test",
        application_environment=ApplicationEnvironment.TEST,
    )
    assert set(create_app(settings).openapi()["paths"]) == {
        "/health",
        "/auth/me",
            "/preferences",
            "/pois/nearby",
            "/v1/assistant/query",
            "/v1/itinerary-drafts/generate",
            "/v1/itineraries",
            "/v1/itineraries/{itinerary_id}",
        }
    assert OPENAI_API_KEY_ENV.casefold() not in Settings.model_fields
    assert OPENAI_NARRATION_MODEL_ENV.casefold() not in Settings.model_fields
    assert "final_text" not in NarrationOutput.model_fields
    assert "warnings" not in NarrationOutput.model_fields
    assert "usage" not in NarrationOutput.model_fields
    assert "trace" not in NarrationOutput.model_fields


def test_package_has_no_provider_database_route_or_tool_dependency() -> None:
    package = BACKEND / "app" / "agents" / "narration"
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(package.glob("*.py"))
    ).casefold()

    for forbidden in (
        "fastapi",
        "firebase",
        "sqlalchemy",
        "function_tool",
        "hosted_tool",
        "mcp_server(",
        "handoff(",
        "database_url",
    ):
        assert forbidden not in combined


def test_narration_package_does_not_enable_verbose_sdk_logging(
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
    runner = _RecordingRunner(_FakeRunResult(_complete_output()))

    asyncio.run(_executor(runner).narrate(_request()))

    assert called is False
