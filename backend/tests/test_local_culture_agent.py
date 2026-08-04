"""Evidence closure, safety, SDK isolation, and privacy tests for T044."""

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
    CultureGuidanceItem,
    EvidenceBundle,
    FactKind,
    FactualClaim,
    LocalCultureOutput,
    LocalCultureRequest,
    SourceRecord,
    SourceType,
    SupportedCity,
)
from app.agents.local_culture import (
    FIXED_RESPECTFUL_CAUTION,
    LocalCultureLimitationReason,
    LocalCultureService,
    OpenAILocalCultureExecutor,
    build_limited_local_culture,
)
from app.agents.local_culture.executor import (
    LOCAL_CULTURE_MAX_TURNS,
    OPENAI_API_KEY_ENV,
    OPENAI_LOCAL_CULTURE_MODEL_ENV,
    serialize_local_culture_request,
)
from app.agents.local_culture.instructions import (
    LOCAL_CULTURE_INSTRUCTIONS,
)
from app.agents.local_culture.validation import (
    UnsafeLocalCultureOutputError,
    validate_local_culture_output,
)
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
    fact_kind: FactKind = FactKind.CULTURE,
    statement: str | None = None,
) -> FactualClaim:
    return FactualClaim(
        claim_id=claim_id,
        evidence_id=f"evidence-{claim_id}",
        fact_kind=fact_kind,
        statement=statement
        or "Trong nghi thức tại địa điểm này, khách được đề nghị nói nhỏ.",
        supporting_source_ids=source_ids,
        poi_id=None,
        freshness_at=NOW,
        price=None,
    )


def _request(
    *,
    sources: tuple[SourceRecord, ...] | None = None,
    claims: tuple[FactualClaim, ...] | None = None,
    topic: str = "Ứng xử tại địa điểm",
) -> LocalCultureRequest:
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
                fact_kind=FactKind.ETIQUETTE,
                statement=(
                    "Hướng dẫn tại địa điểm đề nghị khách xin phép "
                    "trước khi chụp ảnh."
                ),
            ),
        )
    )
    return LocalCultureRequest(
        city=SupportedCity.HCMC,
        topic=topic,
        locale="vi-VN",
        evidence=EvidenceBundle(
            sources=resolved_sources,
            claims=resolved_claims,
        ),
    )


def _guidance(
    guidance_id: str = "culture-guidance-001",
    *,
    text: str = (
        "Trong nghi thức được nêu tại địa điểm này, bạn nên nói nhỏ."
    ),
    claim_ids: tuple[str, ...] = ("claim-a",),
    source_ids: tuple[str, ...] = ("source-a",),
) -> CultureGuidanceItem:
    return CultureGuidanceItem(
        guidance_id=guidance_id,
        text=text,
        claim_ids=claim_ids,
        source_ids=source_ids,
    )


def _complete_output(
    *,
    guidance: tuple[CultureGuidanceItem, ...] | None = None,
    respectful_caution: str | None = None,
) -> LocalCultureOutput:
    return LocalCultureOutput(
        status=AnswerStatus.COMPLETE,
        guidance=guidance if guidance is not None else (_guidance(),),
        respectful_caution=respectful_caution,
        limitation_reason=None,
    )


def _limited_output() -> LocalCultureOutput:
    return LocalCultureOutput(
        status=AnswerStatus.LIMITED,
        guidance=(),
        respectful_caution=None,
        limitation_reason="Chưa có đủ nội dung văn hóa được xác nhận.",
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
) -> OpenAILocalCultureExecutor:
    return OpenAILocalCultureExecutor(
        api_key=api_key,
        model=model,
        runner=runner,
    )


def _service(runner: _RecordingRunner) -> LocalCultureService:
    return LocalCultureService(executor_factory=lambda: _executor(runner))


def test_sdk_agent_and_run_configuration_are_locked_down() -> None:
    runner = _RecordingRunner(_FakeRunResult(_complete_output()))

    output = asyncio.run(_executor(runner).advise(_request()))

    assert output.status is AnswerStatus.COMPLETE
    assert len(runner.calls) == 1
    agent, _, max_turns, run_config = runner.calls[0]
    assert agent.name == "travel_local_culture"
    assert agent.output_type is LocalCultureOutput
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
    assert max_turns == LOCAL_CULTURE_MAX_TURNS == 1
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
        "app.agents.local_culture.executor.Runner.run",
        fake_run,
    )

    output = asyncio.run(
        OpenAILocalCultureExecutor(
            api_key="private-test-key",
            model="private-test-model",
        ).advise(_request())
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
        topic="Nói nhỏ bằng tiếng Việt",
        claims=(
            _claim(
                "claim-a",
                source_ids=("source-a",),
                statement="Khách được đề nghị nói nhỏ bằng tiếng Việt.",
            ),
        ),
    )

    serialized = serialize_local_culture_request(request)
    parsed = json.loads(serialized)

    assert set(parsed) == {
        "city",
        "claims",
        "locale",
        "source_ids",
        "topic",
    }
    assert parsed["source_ids"] == ["source-a"]
    assert parsed["claims"] == [
        {
            "claim_id": "claim-a",
            "fact_kind": "culture",
            "statement": "Khách được đề nghị nói nhỏ bằng tiếng Việt.",
            "supporting_source_ids": ["source-a"],
        }
    ]
    assert "tiếng Việt" in serialized
    for forbidden in (
        "https://",
        "Nhãn nguồn riêng",
        "Đơn vị quản lý riêng",
        "evidence_id",
        "freshness_at",
        "poi_id",
        "uid",
        "email",
        "token",
        "latitude",
        "longitude",
        "database",
        "provider",
        "transcript",
    ):
        assert forbidden not in serialized
    assert serialized == json.dumps(
        parsed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def test_unsafe_input_claim_is_not_serialized_or_used() -> None:
    request = _request(
        sources=(_source("source-a"),),
        claims=(
            _claim(
                "claim-unsafe",
                source_ids=("source-a",),
                statement="Người Việt luôn thân thiện.",
            ),
        ),
    )
    calls = 0

    def forbidden_factory() -> OpenAILocalCultureExecutor:
        nonlocal calls
        calls += 1
        raise AssertionError("executor factory must not be called")

    serialized = serialize_local_culture_request(request)
    output = asyncio.run(
        LocalCultureService(
            executor_factory=forbidden_factory
        ).advise(request)
    )

    assert json.loads(serialized)["claims"] == []
    assert "Người Việt luôn" not in serialized
    assert calls == 0
    assert output.status is AnswerStatus.LIMITED


def test_empty_or_source_only_evidence_returns_limited_without_factory() -> None:
    requests = (
        _request(sources=(), claims=()),
        _request(sources=(_source("source-a"),), claims=()),
    )
    calls = 0

    def forbidden_factory() -> OpenAILocalCultureExecutor:
        nonlocal calls
        calls += 1
        raise AssertionError("executor factory must not be called")

    service = LocalCultureService(executor_factory=forbidden_factory)
    outputs = [
        asyncio.run(service.advise(request))
        for request in requests
    ]

    assert calls == 0
    assert all(output.status is AnswerStatus.LIMITED for output in outputs)
    assert all(output.guidance == () for output in outputs)
    assert all(output.respectful_caution is None for output in outputs)


def test_request_contract_rejects_non_culture_claim() -> None:
    with pytest.raises(ValidationError):
        _request(
            sources=(_source("source-a"),),
            claims=(
                _claim(
                    "claim-history",
                    source_ids=("source-a",),
                    fact_kind=FactKind.HISTORY,
                ),
            ),
        )


def test_one_valid_evidence_linked_guidance_item_passes() -> None:
    expected = _complete_output()
    runner = _RecordingRunner(_FakeRunResult(expected))

    output = asyncio.run(_service(runner).advise(_request()))

    assert output == expected
    assert output is not expected
    assert output.guidance[0].claim_ids == ("claim-a",)
    assert output.guidance[0].source_ids == ("source-a",)


def test_multiple_sequential_guidance_ids_pass() -> None:
    expected = _complete_output(
        guidance=(
            _guidance(),
            _guidance(
                "culture-guidance-002",
                text=(
                    "Theo hướng dẫn tại địa điểm, bạn nên xin phép "
                    "trước khi chụp ảnh."
                ),
                claim_ids=("claim-b",),
                source_ids=("source-a", "source-b"),
            ),
        )
    )

    assert validate_local_culture_output(expected, _request()) == expected


@pytest.mark.parametrize(
    "guidance_id",
    [
        "guidance-001",
        "culture-guidance-000",
        "culture-guidance-002",
        "culture-guidance-a",
    ],
)
def test_noncanonical_or_nonsequential_guidance_id_falls_back(
    guidance_id: str,
) -> None:
    invalid = _complete_output(
        guidance=(_guidance(guidance_id),)
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()


def test_duplicate_guidance_id_falls_back() -> None:
    valid = _complete_output()
    invalid = valid.model_copy(
        update={"guidance": (valid.guidance[0], valid.guidance[0])}
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED


@pytest.mark.parametrize(
    ("claim_ids", "source_ids"),
    [
        (("claim-unknown",), ("source-a",)),
        (("claim-a",), ("source-unknown",)),
        (("claim-a",), ("source-a", "source-b")),
        (("claim-b",), ("source-a",)),
    ],
)
def test_unknown_unrelated_or_inexact_references_fall_back(
    claim_ids: tuple[str, ...],
    source_ids: tuple[str, ...],
) -> None:
    invalid = _complete_output(
        guidance=(
            _guidance(
                claim_ids=claim_ids,
                source_ids=source_ids,
            ),
        )
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()


def test_exact_source_union_for_multiple_claims_is_required() -> None:
    exact = _complete_output(
        guidance=(
            _guidance(
                text=(
                    "Tại địa điểm này, bạn nên nói nhỏ và xin phép "
                    "trước khi chụp ảnh."
                ),
                claim_ids=("claim-a", "claim-b"),
                source_ids=("source-a", "source-b"),
            ),
        )
    )
    missing = exact.model_copy(
        update={
            "guidance": (
                exact.guidance[0].model_copy(
                    update={"source_ids": ("source-a",)}
                ),
            )
        }
    )

    assert validate_local_culture_output(exact, _request()) == exact
    with pytest.raises(ValueError):
        validate_local_culture_output(missing, _request())


def test_guidance_must_be_unique_after_unicode_whitespace_casefolding() -> None:
    invalid = _complete_output(
        guidance=(
            _guidance(
                text="Tại đây, khách nên nói nhỏ.",
            ),
            _guidance(
                "culture-guidance-002",
                text="TẠI ĐÂY,  KHÁCH NÊN NÓI NHỎ.",
            ),
        )
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
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
    valid = _complete_output()
    invalid = valid.model_copy(
        update={
            "guidance": (
                valid.guidance[0].model_copy(
                    update={"text": invalid_text}
                ),
            )
        }
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "Người Việt luôn hành xử như vậy.",
        "Người Thái luôn hành xử như vậy.",
        "Tất cả người dân đều làm như vậy.",
        "Ai cũng làm như vậy.",
        "All locals always behave this way.",
        "People never refuse this practice.",
        "Người Việt rất thân thiện.",
        "Vietnamese are generally hardworking.",
        "Thai people are naturally kind.",
        "Dân tộc này vốn chăm chỉ.",
        "Người theo đạo Phật vốn hiền lành.",
        "Phụ nữ thường dịu dàng.",
        "Nhóm này vượt trội hơn nhóm khác.",
        "This culture is superior to another.",
        "Phong tục này thật lạc hậu.",
    ],
)
def test_stereotypes_and_generalizations_fail_closed(
    unsafe_text: str,
) -> None:
    invalid = _complete_output(
        guidance=(_guidance(text=unsafe_text),)
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()
    assert "khái quát" in (output.limitation_reason or "")


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "Theo luật, bạn phải xuất trình giấy tờ.",
        "This legal obligation applies to visitors.",
        "Bạn nên uống thuốc điều trị trước khi tham gia.",
        "Ask a doctor for this medical treatment.",
        "Bạn phải che vai khi vào chùa.",
        "Bạn nên che vai khi vào chùa.",
        "Visitors must tip after the visit.",
        "Visitors should tip after the visit.",
        "Bạn không được mặc cả tại đây.",
    ],
)
def test_legal_medical_or_invented_obligations_fail_closed(
    unsafe_text: str,
) -> None:
    invalid = _complete_output(
        guidance=(_guidance(text=unsafe_text),)
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()


@pytest.mark.parametrize(
    "unsupported_text",
    [
        "Trang phục kín đáo được yêu cầu tại đây.",
        "Trang phục kín đáo là quy định tại đây.",
        "Tại đây có quy định về tiền boa.",
        "Việc chụp ảnh cần tuân theo quy định tại đây.",
    ],
)
def test_restricted_topic_without_support_falls_back_privately(
    unsupported_text: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = _request(
        sources=(_source("source-a"),),
        claims=(_claim("claim-a", source_ids=("source-a",)),),
    )
    invalid = _complete_output(
        guidance=(_guidance(text=unsupported_text),)
    )
    runner = _RecordingRunner(_FakeRunResult(invalid))
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.local_culture",
    )

    output = asyncio.run(_service(runner).advise(request))

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()
    assert output.respectful_caution is None
    assert output.limitation_reason is not None
    assert unsupported_text not in output.limitation_reason
    for forbidden in (
        "model",
        "openai",
        "exception",
        "prompt",
        "claim-a",
        "source-a",
    ):
        assert forbidden not in output.limitation_reason.casefold()
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "operation=advise path=model status=limited" in logs
    assert unsupported_text not in logs
    assert "claim-a" not in logs
    assert "source-a" not in logs
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    "unsupported_text",
    [
        "Trang phục kín đáo được yêu cầu tại đây.",
        "Trang phục kín đáo là quy định tại đây.",
        "Tại đây có quy định về tiền boa.",
        "Việc chụp ảnh cần tuân theo quy định tại đây.",
    ],
)
def test_validator_rejects_restricted_topic_without_claim_support(
    unsupported_text: str,
) -> None:
    request = _request(
        sources=(_source("source-a"),),
        claims=(_claim("claim-a", source_ids=("source-a",)),),
    )
    invalid = _complete_output(
        guidance=(_guidance(text=unsupported_text),)
    )

    with pytest.raises(UnsafeLocalCultureOutputError):
        validate_local_culture_output(invalid, request)


def test_explicitly_supported_dress_requirement_remains_complete() -> None:
    request = _request(
        sources=(_source("source-a"),),
        claims=(
            _claim(
                "claim-dress",
                source_ids=("source-a",),
                fact_kind=FactKind.ETIQUETTE,
                statement="Hướng dẫn tại địa điểm yêu cầu khách che vai.",
            ),
        ),
    )
    expected = _complete_output(
        guidance=(
            _guidance(
                text=(
                    "Theo hướng dẫn tại địa điểm này, khách được "
                    "yêu cầu che vai."
                ),
                claim_ids=("claim-dress",),
                source_ids=("source-a",),
            ),
        )
    )
    runner = _RecordingRunner(_FakeRunResult(expected))

    assert validate_local_culture_output(expected, request) == expected
    output = asyncio.run(_service(runner).advise(request))
    assert output.status is AnswerStatus.COMPLETE
    assert output.guidance == expected.guidance
    assert output.guidance[0].claim_ids == ("claim-dress",)
    assert output.guidance[0].source_ids == ("source-a",)
    assert len(runner.calls) == 1


def test_explicitly_supported_scoped_photography_guidance_passes() -> None:
    output = _complete_output(
        guidance=(
            _guidance(
                text=(
                    "Theo hướng dẫn tại địa điểm, bạn nên xin phép "
                    "trước khi chụp ảnh."
                ),
                claim_ids=("claim-b",),
                source_ids=("source-a", "source-b"),
            ),
        )
    )

    assert validate_local_culture_output(output, _request()) == output


def test_fixed_respectful_caution_is_accepted() -> None:
    output = _complete_output(
        respectful_caution=FIXED_RESPECTFUL_CAUTION
    )

    assert validate_local_culture_output(output, _request()) == output


def test_arbitrary_respectful_caution_falls_back() -> None:
    invalid = _complete_output(
        respectful_caution="Mọi người tại thành phố này đều mong bạn cúi chào."
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.respectful_caution is None


def test_valid_structured_limited_output_passes_without_fabrication() -> None:
    expected = _limited_output()
    runner = _RecordingRunner(_FakeRunResult(expected))

    output = asyncio.run(_service(runner).advise(_request()))

    assert output == expected
    assert output is not expected
    assert output.guidance == ()
    assert output.respectful_caution is None


def test_stereotype_bearing_limited_reason_falls_back_safely() -> None:
    invalid = _limited_output().model_copy(
        update={"limitation_reason": "Người Việt luôn hành xử như vậy."}
    )

    output = asyncio.run(
        _service(_RecordingRunner(_FakeRunResult(invalid))).advise(
            _request()
        )
    )

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()
    assert output.respectful_caution is None
    assert output.limitation_reason != invalid.limitation_reason


@pytest.mark.parametrize("unexpected", ["plain text", {"status": "complete"}, 7])
def test_plain_text_and_unexpected_outputs_fall_back(
    unexpected: object,
) -> None:
    runner = _RecordingRunner(_FakeRunResult(unexpected))

    output = asyncio.run(_service(runner).advise(_request()))

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()
    assert len(runner.calls) == 1


def test_sdk_failure_is_deterministic_limited_without_retry() -> None:
    request = _request()
    first_runner = _RecordingRunner(
        RuntimeError("raw private response")
    )
    second_runner = _RecordingRunner(
        RuntimeError("different raw response")
    )

    first = asyncio.run(_executor(first_runner).advise(request))
    second = asyncio.run(_executor(second_runner).advise(request))

    assert first.status is AnswerStatus.LIMITED
    assert first.model_dump_json() == second.model_dump_json()
    assert len(first_runner.calls) == 1
    assert len(second_runner.calls) == 1


def test_cancellation_propagates_without_fallback_or_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner = _RecordingRunner(asyncio.CancelledError())
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.local_culture",
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_service(runner).advise(_request()))

    assert len(runner.calls) == 1
    assert not caplog.records


def test_pure_fallback_is_byte_deterministic_and_content_free() -> None:
    request = _request()
    outputs = [
        build_limited_local_culture(
            request,
            LocalCultureLimitationReason.INSUFFICIENT_EVIDENCE,
        )
        for _ in range(2)
    ]

    assert outputs[0].model_dump_json() == outputs[1].model_dump_json()
    assert outputs[0].status is AnswerStatus.LIMITED
    assert outputs[0].guidance == ()
    assert outputs[0].respectful_caution is None
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
        monkeypatch.delenv(
            OPENAI_LOCAL_CULTURE_MODEL_ENV,
            raising=False,
        )
    else:
        monkeypatch.setenv(OPENAI_LOCAL_CULTURE_MODEL_ENV, model)

    output = asyncio.run(LocalCultureService().advise(_request()))

    assert output.status is AnswerStatus.LIMITED
    assert output.guidance == ()
    assert output.respectful_caution is None


def test_configuration_is_read_lazily(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    monkeypatch.delenv(
        OPENAI_LOCAL_CULTURE_MODEL_ENV,
        raising=False,
    )
    service = LocalCultureService()
    monkeypatch.setenv(OPENAI_API_KEY_ENV, "later-key")
    monkeypatch.setenv(
        OPENAI_LOCAL_CULTURE_MODEL_ENV,
        "later-model",
    )
    assert OpenAILocalCultureExecutor.from_environment() is not None
    monkeypatch.delenv(OPENAI_API_KEY_ENV)
    monkeypatch.delenv(OPENAI_LOCAL_CULTURE_MODEL_ENV)

    output = asyncio.run(service.advise(_request()))

    assert output.status is AnswerStatus.LIMITED


def test_safe_logs_exclude_request_evidence_and_configuration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_error = "raw private exception response"
    runner = _RecordingRunner(RuntimeError(private_error))
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.local_culture",
    )

    output = asyncio.run(
        LocalCultureService(
            executor_factory=lambda: _executor(
                runner,
                api_key="private-key",
                model="private-model",
            )
        ).advise(_request(topic="Chủ đề riêng tư"))
    )

    assert output.status is AnswerStatus.LIMITED
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "operation=advise path=model status=limited" in logs
    for private in (
        private_error,
        "private-key",
        "private-model",
        "Chủ đề riêng tư",
        "claim-a",
        "source-a",
        "nghi thức",
        "Nhãn nguồn riêng",
        "https://",
    ):
        assert private not in logs


def test_static_instructions_lock_grounding_and_safety() -> None:
    normalized = " ".join(
        LOCAL_CULTURE_INSTRUCTIONS.casefold().split()
    )
    for required in (
        "only the local culture agent",
        "vietnamese-first travel assistant",
        "return only the localcultureoutput",
        "do not perform discovery",
        "only the supplied culture and etiquette claims",
        "general knowledge are not cultural evidence",
        "never turn a narrow claim into a city-wide",
        "every vietnamese person",
        "never characterize a nationality",
        "never use insults",
        "never invent religious or dress requirements",
        "do not create legal, medical",
        "source_ids equal to exactly the sorted union",
        "culture-guidance-001",
        "use plain text only",
        "status=limited with no guidance",
        "chain of thought",
        "response-composer",
    ):
        assert required in normalized


def test_package_import_needs_no_environment_or_network() -> None:
    script = """
import socket
def blocked(*args, **kwargs):
    raise AssertionError("network")
socket.create_connection = blocked
socket.socket.connect = blocked
import app.agents.local_culture
print("ok")
"""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            OPENAI_API_KEY_ENV,
            OPENAI_LOCAL_CULTURE_MODEL_ENV,
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
    assert (
        OPENAI_LOCAL_CULTURE_MODEL_ENV.casefold()
        not in Settings.model_fields
    )
    for forbidden in (
        "final_text",
        "warnings",
        "usage",
        "trace",
        "response_id",
    ):
        assert forbidden not in LocalCultureOutput.model_fields


def test_package_has_no_provider_database_route_or_tool_dependency() -> None:
    package = BACKEND / "app" / "agents" / "local_culture"
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


def test_local_culture_package_does_not_enable_verbose_sdk_logging(
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

    asyncio.run(_executor(runner).advise(_request()))

    assert called is False


def test_current_curated_packages_have_no_dedicated_culture_claims() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "data" / "curated" / "hcmc" / "package-v1.yaml",
            ROOT / "data" / "curated" / "bangkok" / "package-v1.yaml",
        )
    )

    assert "fact_kind: culture" not in combined
    assert "fact_kind: etiquette" not in combined
    output = asyncio.run(
        LocalCultureService().advise(
            _request(sources=(), claims=())
        )
    )
    assert output.status is AnswerStatus.LIMITED
