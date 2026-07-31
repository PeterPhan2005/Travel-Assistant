"""T047 deterministic Response Composer and exact SDK closure tests."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from agents import Agent, RunConfig
from pydantic import HttpUrl, SecretStr, ValidationError

from app.agents.composer import (
    OpenAIResponseComposerExecutor,
    ResponseComposerService,
    build_deterministic_response,
    validate_response_composer_output,
)
from app.agents.composer.executor import (
    COMPOSER_MAX_TURNS,
    OPENAI_API_KEY_ENV,
    OPENAI_COMPOSER_MODEL_ENV,
    serialize_response_composer_request,
)
from app.agents.composer.renderer import SAFE_FALLBACK_TEXT
from app.agents.contracts import (
    AgentKind,
    AgentWarning,
    AnswerStatus,
    CultureGuidanceItem,
    DiscoveryCandidate,
    DiscoveryCompleteness,
    DiscoveryOutput,
    DiscoverySpecialistOutput,
    EvidenceBundle,
    FactKind,
    FactualClaim,
    FailureCode,
    ItineraryItem,
    ItineraryOutput,
    ItinerarySpecialistOutput,
    LocalCultureOutput,
    LocalCultureSpecialistOutput,
    NarrationOutput,
    NarrationSpecialistOutput,
    PoiPresentationItem,
    PriceFact,
    ResponseComposerOutput,
    ResponseComposerRequest,
    SourceRecord,
    SourceType,
    SupportedCity,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.providers.poi.models import (
    Coordinates,
    PoiProviderKind,
    PriceLevel,
    SourceReference,
)

BACKEND = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 28, tzinfo=timezone.utc)
NARRATION_TEXT = " ".join(
    f"Thông tin Việt {index}" for index in range(1, 26)
)


def _source(source_id: str = "source-a") -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_INSTITUTION,
        label="Nhãn nguồn riêng",
        publisher="Đơn vị nguồn riêng",
        url=HttpUrl(f"https://example.com/{source_id}"),
        retrieved_at=NOW,
    )


def _claim(
    claim_id: str,
    fact_kind: FactKind,
    statement: str,
    *,
    poi_id: str | None = "curated:z-near",
    source_id: str = "source-a",
    price: PriceFact | None = None,
) -> FactualClaim:
    return FactualClaim(
        claim_id=claim_id,
        evidence_id=f"evidence:{claim_id}",
        fact_kind=fact_kind,
        statement=statement,
        supporting_source_ids=(source_id,),
        poi_id=poi_id,
        freshness_at=price.source_updated_at if price is not None else NOW,
        price=price,
    )


def _candidate(
    provider_id: str,
    name: str,
    category: str,
    distance: float,
    *,
    address: str | None = None,
    rating: Decimal | None = None,
    rating_count: int | None = None,
    opening_hours: str | None = None,
    price_level: PriceLevel | None = None,
) -> DiscoveryCandidate:
    source = _source()
    return DiscoveryCandidate(
        id=f"curated:{provider_id}",
        provider=PoiProviderKind.CURATED,
        provider_id=provider_id,
        canonical_name=name,
        city=SupportedCity.HCMC,
        category=category,
        address=address,
        coordinates=Coordinates(latitude=10.78, longitude=106.7),
        distance_metres=distance,
        rating=rating,
        rating_count=rating_count,
        price_level=price_level,
        opening_hours_summary=opening_hours,
        sources=(
            SourceReference(
                source_id=source.source_id,
                source_type=source.source_type.value,
                label=source.label,
                publisher=source.publisher,
                url=source.url,
                retrieved_at=source.retrieved_at,
            ),
        ),
        retrieved_at=NOW,
        is_curated=True,
        is_externally_supplied=False,
    )


def _discovery_specialist(
    *,
    claims: tuple[FactualClaim, ...],
    candidates: tuple[DiscoveryCandidate, ...] | None = None,
) -> DiscoverySpecialistOutput:
    selected = candidates or (
        _candidate(
            "z-near",
            "Bưu điện Trung tâm Sài Gòn",
            "landmark",
            80.0,
            address=None,
            rating=None,
            rating_count=None,
            opening_hours=None,
            price_level=PriceLevel.EXPENSIVE,
        ),
        _candidate(
            "a-far",
            "Bảo tàng Thành phố",
            "museum",
            160.0,
            address="Địa chỉ đã duyệt",
            rating=Decimal("4.5"),
            rating_count=25,
            opening_hours="Giờ đã duyệt",
        ),
    )
    return DiscoverySpecialistOutput(
        agent=AgentKind.DISCOVERY,
        output_id="output-discovery",
        output=DiscoveryOutput(
            candidates=selected,
            evidence=EvidenceBundle(sources=(_source(),), claims=claims),
            provider_failures=(),
            completeness=DiscoveryCompleteness.COMPLETE,
            is_truncated=False,
        ),
    )


def _narration_specialist() -> NarrationSpecialistOutput:
    return NarrationSpecialistOutput(
        agent=AgentKind.NARRATION,
        output_id="output-narration",
        output=NarrationOutput(
            status=AnswerStatus.COMPLETE,
            narration_text=NARRATION_TEXT,
            key_points=("Điểm chính có dấu tiếng Việt.",),
            used_source_ids=("source-a",),
            used_claim_ids=("claim-history",),
            limitation_reason=None,
        ),
    )


def _culture_specialist() -> LocalCultureSpecialistOutput:
    return LocalCultureSpecialistOutput(
        agent=AgentKind.LOCAL_CULTURE,
        output_id="output-culture",
        output=LocalCultureOutput(
            status=AnswerStatus.COMPLETE,
            guidance=(
                CultureGuidanceItem(
                    guidance_id="culture-guidance-001",
                    text="Giữ giọng nói vừa phải tại địa điểm.",
                    claim_ids=("claim-culture",),
                    source_ids=("source-a",),
                ),
            ),
            respectful_caution="Hãy quan sát và hỏi một cách lịch sự.",
            limitation_reason=None,
        ),
    )


def _itinerary_specialist() -> ItinerarySpecialistOutput:
    return ItinerarySpecialistOutput(
        agent=AgentKind.ITINERARY,
        output_id="output-itinerary",
        output=ItineraryOutput(
            local_date=date(2026, 8, 1),
            timezone="Asia/Ho_Chi_Minh",
            start_local_time=time(9, 0),
            end_local_time=time(10, 0),
            items=(
                ItineraryItem(
                    item_id="itinerary-item-001",
                    poi_id="curated:z-near",
                    title="Bưu điện Trung tâm Sài Gòn",
                    start_local_time=time(9, 0),
                    end_local_time=time(10, 0),
                    supporting_claim_ids=("claim-itinerary",),
                    supporting_source_ids=("source-a",),
                ),
            ),
            assumptions=(
                "Đây là lịch trình nháp và thời lượng được chia theo khung giờ.",
                "Chưa tính thời gian di chuyển hoặc tình trạng thực tế.",
            ),
            warnings=(),
            draft_only=True,
        ),
    )


def _warning() -> AgentWarning:
    return AgentWarning(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.PARTIAL_RESULT,
        message="Một phần thông tin hiện chưa có.",
        retryable=True,
    )


def _full_request(
    *,
    warnings: tuple[AgentWarning, ...] = (),
    duplicate_claim: bool = False,
) -> ResponseComposerRequest:
    claims = (
        _claim(
            "claim-category",
            FactKind.CATEGORY,
            "Bưu điện có loại landmark.",
        ),
        _claim(
            "claim-culture",
            FactKind.CULTURE,
            "Giữ giọng nói vừa phải tại địa điểm.",
            poi_id=None,
        ),
        _claim(
            "claim-history",
            FactKind.HISTORY,
            "Thông tin lịch sử đã duyệt.",
        ),
        _claim(
            "claim-identity",
            FactKind.IDENTITY,
            "Đây là Bưu điện Trung tâm Sài Gòn.",
        ),
        _claim(
            "claim-itinerary",
            FactKind.ITINERARY_CONSTRAINT,
            "Khung giờ tham quan đã được chọn.",
        ),
        _claim(
            "claim-remaining",
            FactKind.DESCRIPTION,
            (
                "Giữ giọng nói vừa phải tại địa điểm."
                if duplicate_claim
                else "Thông tin bổ sung đã duyệt."
            ),
        ),
    )
    discovery_claims = tuple(
        claim
        for claim in claims
        if claim.claim_id in {"claim-category", "claim-identity"}
    )
    return ResponseComposerRequest(
        user_query="  Giới thiệu   địa điểm  ",
        locale="vi-VN",
        evidence=EvidenceBundle(sources=(_source(),), claims=claims),
        approved_claim_ids=tuple(claim.claim_id for claim in claims),
        approved_specialist_outputs=(
            _culture_specialist(),
            _discovery_specialist(claims=discovery_claims),
            _itinerary_specialist(),
            _narration_specialist(),
        ),
        warnings=warnings,
    )


@dataclass
class _FakeRunResult:
    final_output: object


class _RecordingRunner:
    def __init__(self, result: _FakeRunResult | BaseException) -> None:
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


class _FakeExecutor:
    def __init__(self, result: object | BaseException) -> None:
        self.result = result
        self.calls = 0

    async def compose(
        self,
        request: ResponseComposerRequest,
    ) -> ResponseComposerOutput:
        del request
        self.calls += 1
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result  # type: ignore[return-value]


def _executor(
    runner: _RecordingRunner,
) -> OpenAIResponseComposerExecutor:
    return OpenAIResponseComposerExecutor(
        api_key="private-test-key",
        model="private-test-model",
        runner=runner,
    )


def test_empty_approved_content_returns_fixed_evidence_free_fallback() -> None:
    warning = _warning()
    request = ResponseComposerRequest(
        user_query="Hỗ trợ tôi",
        locale="vi-VN",
        evidence=EvidenceBundle(),
        approved_claim_ids=(),
        approved_specialist_outputs=(),
        warnings=(warning,),
    )

    output = build_deterministic_response(request)

    assert output.final_text == SAFE_FALLBACK_TEXT
    assert output.poi_items == ()
    assert output.warnings == (warning,)
    assert output.used_claim_ids == ()
    assert output.used_source_ids == ()


def test_renderer_is_byte_deterministic_and_uses_content_priority() -> None:
    request = _full_request(warnings=(_warning(),))

    first = build_deterministic_response(request)
    second = build_deterministic_response(request)

    assert first.model_dump_json() == second.model_dump_json()
    assert first.warnings == request.warnings
    assert first.final_text.index("Phần thuyết minh:") < first.final_text.index(
        "Thông tin văn hóa địa phương:"
    )
    assert first.final_text.index(
        "Thông tin văn hóa địa phương:"
    ) < first.final_text.index("Lịch trình nháp:")
    assert first.final_text.index("Lịch trình nháp:") < first.final_text.index(
        "Các địa điểm:"
    )
    for exact in (
        NARRATION_TEXT,
        "Điểm chính có dấu tiếng Việt.",
        "Giữ giọng nói vừa phải tại địa điểm.",
        "09:00–10:00: Bưu điện Trung tâm Sài Gòn",
        "Đây là lịch trình nháp và thời lượng được chia theo khung giờ.",
        "Thông tin bổ sung đã duyệt.",
    ):
        assert exact in first.final_text
    assert first.used_claim_ids == request.approved_claim_ids
    assert first.used_source_ids == ("source-a",)
    assert "best" not in first.final_text.casefold()
    assert "must visit" not in first.final_text.casefold()


def test_normalized_duplicate_content_is_rendered_once() -> None:
    output = build_deterministic_response(
        _full_request(duplicate_claim=True)
    )

    assert output.final_text.count(
        "Giữ giọng nói vừa phải tại địa điểm."
    ) == 1
    assert "claim-remaining" in output.used_claim_ids


def test_discovery_preserves_nonlexicographic_distance_order_and_omission() -> None:
    request = _full_request()

    output = build_deterministic_response(request)

    assert tuple(item.poi_id for item in output.poi_items) == (
        "curated:z-near",
        "curated:a-far",
    )
    first, second = output.poi_items
    assert first.distance_metres == 80.0
    assert first.address is None
    assert first.rating is None
    assert first.rating_count is None
    assert first.opening_hours_summary is None
    assert first.price is None
    assert second.address == "Địa chỉ đã duyệt"
    assert second.rating == Decimal("4.5")
    assert second.rating_count == 25
    assert second.opening_hours_summary == "Giờ đã duyệt"
    serialized = first.model_dump(mode="json", exclude_none=True)
    for missing in (
        "address",
        "rating",
        "rating_count",
        "price",
        "opening_hours_summary",
    ):
        assert missing not in serialized
    assert "coordinates" not in output.model_dump_json()
    assert "provider_id" not in output.model_dump_json()


def test_duplicate_presented_poi_is_rejected_but_input_order_is_not_sorted() -> None:
    first = PoiPresentationItem(
        poi_id="curated:z-near",
        canonical_name="Gần",
        category="landmark",
    )
    second = PoiPresentationItem(
        poi_id="curated:a-far",
        canonical_name="Xa",
        category="museum",
    )
    output = ResponseComposerOutput(
        final_text="Danh sách địa điểm.",
        poi_items=(first, second),
    )

    assert tuple(item.poi_id for item in output.poi_items) == (
        "curated:z-near",
        "curated:a-far",
    )
    with pytest.raises(ValidationError):
        ResponseComposerOutput(
            final_text="Danh sách địa điểm.",
            poi_items=(first, first),
        )


def test_price_requires_exactly_one_approved_price_for_same_poi() -> None:
    price_a = _claim(
        "claim-price-a",
        FactKind.PRICE,
        "Một món có giá 125000 VND.",
        price=PriceFact(
            price_minor_units=125_000,
            currency="VND",
            source_updated_at=NOW,
        ),
    )
    candidate = _candidate(
        "z-near",
        "Bưu điện Trung tâm Sài Gòn",
        "landmark",
        80.0,
        price_level=PriceLevel.VERY_EXPENSIVE,
    )
    request = ResponseComposerRequest(
        user_query="Giá",
        locale="vi-VN",
        evidence=EvidenceBundle(
            sources=(_source(),),
            claims=(price_a,),
        ),
        approved_claim_ids=("claim-price-a",),
        approved_specialist_outputs=(
            _discovery_specialist(claims=(), candidates=(candidate,)),
        ),
    )

    exact = build_deterministic_response(request)

    assert exact.poi_items[0].price == price_a.price
    assert exact.used_claim_ids == ("claim-price-a",)
    assert exact.poi_items[0].price is not None
    ambiguous_claim = _claim(
        "claim-price-b",
        FactKind.PRICE,
        "Một món khác có giá 150000 VND.",
        price=PriceFact(
            price_minor_units=150_000,
            currency="VND",
            source_updated_at=NOW,
        ),
    )
    ambiguous = request.model_copy(
        update={
            "evidence": EvidenceBundle(
                sources=(_source(),),
                claims=(price_a, ambiguous_claim),
            ),
            "approved_claim_ids": ("claim-price-a", "claim-price-b"),
        }
    )
    none_for_multiple = build_deterministic_response(
        ResponseComposerRequest.model_validate(
            ambiguous.model_dump(mode="python")
        )
    )
    assert none_for_multiple.poi_items[0].price is None


def test_price_for_another_poi_and_price_level_are_not_mapped() -> None:
    other_price = _claim(
        "claim-price-other",
        FactKind.PRICE,
        "Một món ở nơi khác có giá 100 VND.",
        poi_id="curated:other",
        price=PriceFact(
            price_minor_units=100,
            currency="VND",
            source_updated_at=NOW,
        ),
    )
    request = ResponseComposerRequest(
        user_query="Giá",
        locale="vi-VN",
        evidence=EvidenceBundle(
            sources=(_source(),),
            claims=(other_price,),
        ),
        approved_claim_ids=("claim-price-other",),
        approved_specialist_outputs=(
            _discovery_specialist(claims=()),
        ),
    )

    output = build_deterministic_response(request)

    assert all(item.price is None for item in output.poi_items)


def test_distance_only_discovery_creates_no_synthetic_reference() -> None:
    request = ResponseComposerRequest(
        user_query="Địa điểm gần đây",
        locale="vi-VN",
        evidence=EvidenceBundle(),
        approved_claim_ids=(),
        approved_specialist_outputs=(
            _discovery_specialist(
                claims=(),
                candidates=(
                    _candidate(
                        "z-near",
                        "Địa điểm có khoảng cách",
                        "landmark",
                        80.0,
                    ),
                ),
            ),
        ),
    )

    output = build_deterministic_response(request)

    assert output.poi_items[0].distance_metres == 80.0
    assert output.used_claim_ids == ()
    assert output.used_source_ids == ()


def test_exact_warning_and_reference_closure_rejects_every_change() -> None:
    request = _full_request(warnings=(_warning(),))
    deterministic = build_deterministic_response(request)
    changed_warning = deterministic.model_copy(update={"warnings": ()})
    extra_source = deterministic.model_copy(
        update={"used_source_ids": ("source-a", "source-extra")}
    )
    altered_text = deterministic.model_copy(
        update={"final_text": deterministic.final_text + " Một fact mới."}
    )

    for candidate in (changed_warning, extra_source, altered_text):
        with pytest.raises((TypeError, ValueError)):
            validate_response_composer_output(
                candidate,
                request,
                deterministic,
            )


def test_serialization_is_compact_unicode_and_private_data_free() -> None:
    request = _full_request(warnings=(_warning(),))

    serialized = serialize_response_composer_request(request)
    payload = json.loads(serialized)

    assert serialized == json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert payload["user_query"] == "Giới thiệu địa điểm"
    assert "Điểm chính có dấu tiếng Việt." in serialized
    for private in (
        "latitude",
        "longitude",
        "coordinates",
        "provider_id",
        "price_level",
        "evidence_id",
        "Nhãn nguồn riêng",
        "Đơn vị nguồn riêng",
        "https://",
        "DATABASE_URL",
        "FIREBASE",
        "private-test-key",
        "private-test-model",
    ):
        assert private not in serialized


def test_sdk_agent_and_run_configuration_are_locked_down() -> None:
    request = _full_request()
    expected = build_deterministic_response(request)
    runner = _RecordingRunner(_FakeRunResult(expected))

    output = asyncio.run(_executor(runner).compose(request))

    assert output == expected
    assert len(runner.calls) == 1
    agent, _, max_turns, run_config = runner.calls[0]
    assert agent.name == "travel_response_composer"
    assert agent.output_type is ResponseComposerOutput
    assert agent.tools == []
    assert agent.handoffs == []
    assert agent.mcp_servers == []
    assert agent.model == "private-test-model"
    assert agent.model_settings.tool_choice == "none"
    assert agent.model_settings.parallel_tool_calls is False
    assert agent.model_settings.retry is not None
    assert agent.model_settings.retry.max_retries == 0
    assert max_turns == COMPOSER_MAX_TURNS == 1
    assert run_config.tracing_disabled is True
    assert run_config.trace_include_sensitive_data is False
    assert run_config.session_settings is None


@pytest.mark.parametrize(
    "result",
    [
        "plain text",
        {"final_text": "arbitrary"},
        RuntimeError("raw model response"),
    ],
)
def test_wrong_output_and_sdk_failure_fall_back_without_retry(
    result: object,
) -> None:
    request = _full_request()
    runner_result = (
        result
        if isinstance(result, BaseException)
        else _FakeRunResult(result)
    )
    runner = _RecordingRunner(runner_result)

    output = asyncio.run(_executor(runner).compose(request))

    assert output == build_deterministic_response(request)
    assert len(runner.calls) == 1


def test_model_cannot_change_text_poi_order_or_warning() -> None:
    request = _full_request(warnings=(_warning(),))
    deterministic = build_deterministic_response(request)
    candidates = (
        deterministic.model_copy(
            update={"final_text": deterministic.final_text + " Fact mới."}
        ),
        deterministic.model_copy(
            update={"poi_items": tuple(reversed(deterministic.poi_items))}
        ),
        deterministic.model_copy(
            update={
                "poi_items": (
                    deterministic.poi_items[0].model_copy(
                        update={"distance_metres": 999.0}
                    ),
                    *deterministic.poi_items[1:],
                )
            }
        ),
        deterministic.model_copy(update={"warnings": ()}),
        deterministic.model_copy(
            update={"warnings": (*deterministic.warnings, _warning())}
        ),
    )

    for candidate in candidates:
        runner = _RecordingRunner(_FakeRunResult(candidate))
        output = asyncio.run(_executor(runner).compose(request))
        assert output == deterministic
        assert len(runner.calls) == 1


def test_service_failure_is_sanitized_and_does_not_retry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = _full_request()
    private_error = "raw private response claim-history source-a"
    executor = _FakeExecutor(RuntimeError(private_error))
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.composer",
    )

    output = asyncio.run(
        ResponseComposerService(
            executor_factory=lambda: executor
        ).compose(request)
    )

    assert output == build_deterministic_response(request)
    assert executor.calls == 1
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "operation=compose path=deterministic" in logs
    for private in (
        private_error,
        request.user_query,
        output.final_text,
        "claim-history",
        "source-a",
        "curated:z-near",
        "private-test-key",
        "private-test-model",
        "Bưu điện",
    ):
        assert private not in logs


def test_cancellation_propagates_without_fallback_or_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner = _RecordingRunner(asyncio.CancelledError())
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.composer",
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            ResponseComposerService(
                executor_factory=lambda: _executor(runner)
            ).compose(_full_request())
        )

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
def test_missing_or_blank_configuration_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    model: str | None,
) -> None:
    if api_key is None:
        monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_API_KEY_ENV, api_key)
    if model is None:
        monkeypatch.delenv(OPENAI_COMPOSER_MODEL_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_COMPOSER_MODEL_ENV, model)

    output = asyncio.run(ResponseComposerService().compose(_full_request()))

    assert output == build_deterministic_response(_full_request())


def test_environment_free_import_has_no_network_or_external_initialization() -> None:
    script = """
import socket

def blocked(*args, **kwargs):
    raise AssertionError("network access attempted")

socket.create_connection = blocked
socket.socket.connect = blocked
import app.agents.composer
from app.agents.contracts import ResponseComposerRequest, ResponseComposerOutput
ResponseComposerRequest.model_json_schema()
ResponseComposerOutput.model_json_schema()
print("ok")
"""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            OPENAI_API_KEY_ENV,
            OPENAI_COMPOSER_MODEL_ENV,
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


def test_dependencies_routes_settings_and_scope_remain_unchanged() -> None:
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
    }
    assert OPENAI_API_KEY_ENV.casefold() not in Settings.model_fields
    assert OPENAI_COMPOSER_MODEL_ENV.casefold() not in Settings.model_fields

    package = BACKEND / "app" / "agents" / "composer"
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
        "groundingreviewoutput",
        "groundingreviewrequest",
    ):
        assert forbidden not in combined
