"""Deterministic planning, SDK isolation, closure, and privacy tests for T045."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path

import pytest
from agents import Agent, RunConfig
from pydantic import HttpUrl, SecretStr, ValidationError

from app.agents.contracts import (
    AgentKind,
    AgentWarning,
    DiscoveryCandidate,
    DiscoveryOrigin,
    EvidenceBundle,
    FactKind,
    FactualClaim,
    FailureCode,
    ItineraryConstraints,
    ItineraryOutput,
    ItineraryRequest,
    SourceRecord,
    SourceType,
    SupportedCity,
)
from app.agents.itinerary import (
    APPROVED_ASSUMPTIONS,
    ItineraryExecutionError,
    ItineraryFailureReason,
    ItineraryService,
    OpenAIItineraryExecutor,
    plan_itinerary,
    select_candidates,
    validate_itinerary_output,
)
from app.agents.itinerary.executor import (
    ITINERARY_MAX_TURNS,
    OPENAI_API_KEY_ENV,
    OPENAI_ITINERARY_MODEL_ENV,
    serialize_itinerary_request,
)
from app.agents.itinerary.instructions import ITINERARY_INSTRUCTIONS
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.providers.poi.models import (
    Coordinates,
    PoiProviderKind,
    SourceReference,
)

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
NOW = datetime(2026, 7, 28, 1, 2, tzinfo=timezone.utc)


def _candidate(
    provider_id: str,
    *,
    name: str,
    category: str,
    distance: float,
    city: SupportedCity = SupportedCity.HCMC,
) -> DiscoveryCandidate:
    source_id = f"candidate-source-{provider_id}"
    return DiscoveryCandidate(
        id=f"curated:{provider_id}",
        provider=PoiProviderKind.CURATED,
        provider_id=provider_id,
        canonical_name=name,
        city=city,
        category=category,
        address=f"Địa chỉ riêng {provider_id}",
        coordinates=Coordinates(latitude=10.77, longitude=106.69),
        distance_metres=distance,
        rating=None,
        rating_count=None,
        price_level=None,
        opening_hours_summary=None,
        sources=(
            SourceReference(
                source_id=source_id,
                source_type="official_institution",
                label=f"Nguồn riêng {provider_id}",
                publisher="Đơn vị riêng",
                url=HttpUrl(f"https://example.test/{provider_id}"),
                published_at=None,
                retrieved_at=NOW,
            ),
        ),
        retrieved_at=NOW,
        is_curated=True,
        is_externally_supplied=False,
    )


CANDIDATES = (
    _candidate(
        "poi-z",
        name="Điểm gần nhất",
        category="food",
        distance=100.0,
    ),
    _candidate(
        "poi-a",
        name="Bảo tàng bắt buộc",
        category="museum",
        distance=200.0,
    ),
    _candidate(
        "poi-m",
        name="Bảo tàng tiếp theo",
        category="museum",
        distance=300.0,
    ),
    _candidate(
        "poi-b",
        name="Công viên cuối",
        category="park",
        distance=400.0,
    ),
)


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
    poi_id: str,
    source_ids: tuple[str, ...],
) -> FactualClaim:
    return FactualClaim(
        claim_id=claim_id,
        evidence_id=f"evidence-{claim_id}",
        fact_kind=FactKind.HISTORY,
        statement=f"Thông tin đã duyệt cho {claim_id}.",
        supporting_source_ids=source_ids,
        poi_id=poi_id,
        freshness_at=NOW,
        price=None,
    )


def _request(
    *,
    candidates: tuple[DiscoveryCandidate, ...] = CANDIDATES,
    maximum_stops: int = 3,
    required: tuple[str, ...] = ("curated:poi-a",),
    excluded: tuple[str, ...] = (),
    preferred: tuple[str, ...] = ("museum",),
    notes: tuple[str, ...] = ("Giữ nhịp độ ổn định",),
    start: time = time(9, 0),
    end: time = time(17, 1),
    evidence: EvidenceBundle | None = None,
    start_origin: DiscoveryOrigin | None = None,
) -> ItineraryRequest:
    return ItineraryRequest(
        city=SupportedCity.HCMC,
        local_date=date(2026, 8, 1),
        timezone="Asia/Ho_Chi_Minh",
        start_local_time=start,
        end_local_time=end,
        candidates=candidates,
        evidence=evidence or EvidenceBundle(),
        constraints=ItineraryConstraints(
            maximum_stops=maximum_stops,
            required_poi_ids=required,
            excluded_poi_ids=excluded,
            preferred_categories=preferred,
            notes=notes,
        ),
        start_origin=start_origin,
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


class _FakeExecutor:
    def __init__(self, result: object | BaseException) -> None:
        self.result = result
        self.calls = 0

    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        del request
        self.calls += 1
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result  # type: ignore[return-value]


def _executor(
    runner: _RecordingRunner,
    *,
    api_key: str = "private-test-key",
    model: str = "private-test-model",
) -> OpenAIItineraryExecutor:
    return OpenAIItineraryExecutor(
        api_key=api_key,
        model=model,
        runner=runner,
    )


def _warning() -> AgentWarning:
    return AgentWarning(
        stage=AgentKind.ITINERARY,
        code=FailureCode.PARTIAL_RESULT,
        message="Một phần lịch trình chưa được xác nhận.",
        retryable=False,
    )


def test_distance_ranked_nonlexicographic_candidates_are_accepted() -> None:
    request = _request()

    assert tuple(candidate.id for candidate in request.candidates) == (
        "curated:poi-z",
        "curated:poi-a",
        "curated:poi-m",
        "curated:poi-b",
    )


def test_duplicate_candidate_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        _request(
            candidates=(CANDIDATES[0], CANDIDATES[0]),
            required=(),
        )


def test_candidate_city_and_constraint_closure_remain_strict() -> None:
    bangkok = _candidate(
        "bkk-poi",
        name="Điểm Bangkok",
        category="temple",
        distance=10.0,
        city=SupportedCity.BANGKOK,
    )
    with pytest.raises(ValidationError, match="city"):
        _request(candidates=(bangkok,), required=())
    with pytest.raises(ValidationError, match="unknown candidate"):
        _request(required=("curated:poi-unknown",))
    with pytest.raises(ValidationError, match="unknown candidate"):
        _request(excluded=("curated:poi-unknown",))


def test_public_schema_shape_remains_compatible() -> None:
    request_fields = set(
        ItineraryRequest.model_json_schema()["properties"]
    )
    output_fields = set(ItineraryOutput.model_json_schema()["properties"])

    assert request_fields == {
        "city",
        "local_date",
        "timezone",
        "start_local_time",
        "end_local_time",
        "candidates",
        "evidence",
        "constraints",
        "start_origin",
    }
    assert output_fields == {
        "local_date",
        "timezone",
        "start_local_time",
        "end_local_time",
        "items",
        "assumptions",
        "warnings",
        "draft_only",
    }


def test_candidate_selection_required_preferred_remaining_and_input_order() -> None:
    selected = select_candidates(_request())

    assert tuple(candidate.id for candidate in selected) == (
        "curated:poi-z",
        "curated:poi-a",
        "curated:poi-m",
    )


def test_candidate_selection_excludes_and_enforces_maximum() -> None:
    request = _request(
        maximum_stops=2,
        required=("curated:poi-a",),
        excluded=("curated:poi-m",),
    )

    selected = select_candidates(request)

    assert tuple(candidate.id for candidate in selected) == (
        "curated:poi-z",
        "curated:poi-a",
    )


def test_planner_allocates_all_minutes_with_earlier_remainder() -> None:
    output = plan_itinerary(_request())

    assert tuple(
        (
            item.item_id,
            item.poi_id,
            item.start_local_time,
            item.end_local_time,
        )
        for item in output.items
    ) == (
        (
            "itinerary-item-001",
            "curated:poi-z",
            time(9, 0),
            time(11, 41),
        ),
        (
            "itinerary-item-002",
            "curated:poi-a",
            time(11, 41),
            time(14, 21),
        ),
        (
            "itinerary-item-003",
            "curated:poi-m",
            time(14, 21),
            time(17, 1),
        ),
    )
    assert output.items[-1].end_local_time == output.end_local_time


def test_planner_identity_assumptions_and_evidence_are_exact() -> None:
    request = _request()
    output = plan_itinerary(request)

    assert output.local_date == request.local_date
    assert output.timezone == request.timezone
    assert output.start_local_time == request.start_local_time
    assert output.end_local_time == request.end_local_time
    assert output.assumptions == APPROVED_ASSUMPTIONS
    assert output.warnings == ()
    assert output.draft_only is True
    for item in output.items:
        candidate = next(
            candidate
            for candidate in request.candidates
            if candidate.id == item.poi_id
        )
        assert item.title == candidate.canonical_name
        assert item.supporting_claim_ids == ()
        assert item.supporting_source_ids == ()


def test_planner_is_byte_deterministic_and_does_not_mutate_request() -> None:
    request = _request()
    before = request.model_dump_json()

    first = plan_itinerary(request)
    second = plan_itinerary(request)

    assert first.model_dump_json() == second.model_dump_json()
    assert request.model_dump_json() == before


def test_optional_selection_is_limited_by_positive_minute_capacity() -> None:
    request = _request(
        maximum_stops=3,
        required=(),
        start=time(9, 0),
        end=time(9, 1),
    )

    output = plan_itinerary(request)

    assert len(output.items) == 1
    assert output.items[0].start_local_time == time(9, 0)
    assert output.items[0].end_local_time == time(9, 1)


def test_no_usable_candidate_raises_sanitized_typed_error() -> None:
    request = _request(
        maximum_stops=4,
        required=(),
        excluded=tuple(sorted(candidate.id for candidate in CANDIDATES)),
    )

    with pytest.raises(ItineraryExecutionError) as captured:
        plan_itinerary(request)

    assert captured.value.reason is (
        ItineraryFailureReason.NO_USABLE_CANDIDATES
    )
    assert captured.value.failure.stage is AgentKind.ITINERARY
    assert captured.value.failure.code is FailureCode.INVALID_INPUT
    assert str(captured.value) == "no_usable_candidates"
    assert "poi" not in str(captured.value).casefold()


def test_required_stops_that_cannot_fit_raise_sanitized_error() -> None:
    request = _request(
        maximum_stops=2,
        required=("curated:poi-a", "curated:poi-z"),
        start=time(9, 0),
        end=time(9, 1),
    )

    with pytest.raises(ItineraryExecutionError) as captured:
        plan_itinerary(request)

    assert captured.value.reason is (
        ItineraryFailureReason.UNSATISFIABLE_TIME_WINDOW
    )


def test_non_integer_minute_window_fails_closed() -> None:
    request = _request(
        start=time(9, 0, 30),
        end=time(10, 0, 30),
    )

    with pytest.raises(ItineraryExecutionError) as captured:
        plan_itinerary(request)

    assert captured.value.reason is (
        ItineraryFailureReason.UNSATISFIABLE_TIME_WINDOW
    )


def test_valid_item_specific_evidence_is_accepted() -> None:
    evidence = EvidenceBundle(
        sources=(_source("source-a"), _source("source-b")),
        claims=(
            _claim(
                "claim-a",
                poi_id="curated:poi-z",
                source_ids=("source-a", "source-b"),
            ),
        ),
    )
    request = _request(evidence=evidence)
    output = plan_itinerary(request)
    first = output.items[0].model_copy(
        update={
            "supporting_claim_ids": ("claim-a",),
            "supporting_source_ids": ("source-a", "source-b"),
        }
    )
    candidate = output.model_copy(
        update={"items": (first, *output.items[1:])}
    )

    assert validate_itinerary_output(candidate, request) == candidate


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("local_date", date(2026, 8, 2)),
        ("timezone", "Asia/Bangkok"),
        ("start_local_time", time(8, 59)),
        ("end_local_time", time(17, 2)),
    ],
)
def test_changed_request_window_is_rejected(
    field: str,
    value: object,
) -> None:
    request = _request()
    output = plan_itinerary(request).model_copy(update={field: value})

    with pytest.raises(ValueError):
        validate_itinerary_output(output, request)


def test_overlap_and_out_of_window_are_rejected() -> None:
    request = _request()
    output = plan_itinerary(request)
    overlapping_item = output.items[1].model_copy(
        update={"start_local_time": time(11, 40)}
    )
    overlapping = output.model_copy(
        update={
            "items": (
                output.items[0],
                overlapping_item,
                output.items[2],
            )
        }
    )
    outside_item = output.items[0].model_copy(
        update={"start_local_time": time(8, 59)}
    )
    outside = output.model_copy(
        update={"items": (outside_item, *output.items[1:])}
    )

    with pytest.raises(ValidationError, match="overlap"):
        validate_itinerary_output(overlapping, request)
    with pytest.raises(ValidationError):
        validate_itinerary_output(outside, request)


def test_duplicate_poi_noncanonical_id_and_changed_title_are_rejected() -> None:
    request = _request()
    output = plan_itinerary(request)
    duplicate = output.items[1].model_copy(
        update={
            "poi_id": output.items[0].poi_id,
            "title": output.items[0].title,
        }
    )
    duplicate_output = output.model_copy(
        update={"items": (output.items[0], duplicate, output.items[2])}
    )
    wrong_id = output.model_copy(
        update={
            "items": (
                output.items[0].model_copy(update={"item_id": "item-1"}),
                *output.items[1:],
            )
        }
    )
    wrong_title = output.model_copy(
        update={
            "items": (
                output.items[0].model_copy(update={"title": "Tên tự tạo"}),
                *output.items[1:],
            )
        }
    )

    with pytest.raises(ValueError, match="unique"):
        validate_itinerary_output(duplicate_output, request)
    with pytest.raises(ValueError, match="canonical"):
        validate_itinerary_output(wrong_id, request)
    with pytest.raises(ValueError, match="title"):
        validate_itinerary_output(wrong_title, request)


def test_unknown_omitted_excluded_and_too_many_pois_are_rejected() -> None:
    request = _request()
    output = plan_itinerary(request)
    unknown = output.model_copy(
        update={
            "items": (
                output.items[0].model_copy(
                    update={
                        "poi_id": "curated:unknown",
                        "title": "Không rõ",
                    }
                ),
                *output.items[1:],
            )
        }
    )
    omitted_required = output.model_copy(
        update={"items": (output.items[0], output.items[2])}
    )
    excluded_request = _request(
        maximum_stops=3,
        excluded=("curated:poi-z",),
    )
    excluded_output = output
    max_one_request = _request(
        maximum_stops=1,
        required=(),
    )

    with pytest.raises(ValueError, match="unknown"):
        validate_itinerary_output(unknown, request)
    with pytest.raises(ValueError, match="required"):
        validate_itinerary_output(omitted_required, request)
    with pytest.raises(ValueError, match="excluded"):
        validate_itinerary_output(excluded_output, excluded_request)
    with pytest.raises(ValueError, match="maximum"):
        validate_itinerary_output(output, max_one_request)


def test_candidate_order_assumptions_warnings_and_seconds_are_rejected() -> None:
    request = _request()
    output = plan_itinerary(request)
    first = output.items[0]
    second = output.items[1]
    reversed_pois = output.model_copy(
        update={
            "items": (
                first.model_copy(
                    update={
                        "poi_id": second.poi_id,
                        "title": second.title,
                    }
                ),
                second.model_copy(
                    update={
                        "poi_id": first.poi_id,
                        "title": first.title,
                    }
                ),
                output.items[2],
            )
        }
    )
    arbitrary_assumption = output.model_copy(
        update={"assumptions": ("Giờ mở cửa đã được kiểm tra.",)}
    )
    arbitrary_warning = output.model_copy(update={"warnings": (_warning(),)})
    second_boundary = output.model_copy(
        update={
            "items": (
                first.model_copy(
                    update={"start_local_time": time(9, 0, 1)}
                ),
                *output.items[1:],
            )
        }
    )

    with pytest.raises(ValueError, match="input order"):
        validate_itinerary_output(reversed_pois, request)
    with pytest.raises(ValueError, match="assumptions"):
        validate_itinerary_output(arbitrary_assumption, request)
    with pytest.raises(ValueError, match="warnings"):
        validate_itinerary_output(arbitrary_warning, request)
    with pytest.raises(ValueError, match="whole minutes"):
        validate_itinerary_output(second_boundary, request)


def test_unknown_cross_poi_and_inexact_source_union_are_rejected() -> None:
    evidence = EvidenceBundle(
        sources=(_source("source-a"), _source("source-b")),
        claims=(
            _claim(
                "claim-a",
                poi_id="curated:poi-z",
                source_ids=("source-a", "source-b"),
            ),
            _claim(
                "claim-b",
                poi_id="curated:poi-a",
                source_ids=("source-a",),
            ),
        ),
    )
    request = _request(evidence=evidence)
    output = plan_itinerary(request)

    def with_refs(
        claim_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
    ) -> ItineraryOutput:
        first = output.items[0].model_copy(
            update={
                "supporting_claim_ids": claim_ids,
                "supporting_source_ids": source_ids,
            }
        )
        return output.model_copy(
            update={"items": (first, *output.items[1:])}
        )

    with pytest.raises(ValueError, match="unknown claim"):
        validate_itinerary_output(
            with_refs(("claim-unknown",), ("source-a",)),
            request,
        )
    with pytest.raises(ValueError, match="another POI"):
        validate_itinerary_output(
            with_refs(("claim-b",), ("source-a",)),
            request,
        )
    with pytest.raises(ValueError, match="source union"):
        validate_itinerary_output(
            with_refs(("claim-a",), ("source-a",)),
            request,
        )


def test_model_input_is_compact_allowlisted_and_coordinate_free() -> None:
    evidence = EvidenceBundle(
        sources=(_source("source-a"),),
        claims=(
            _claim(
                "claim-a",
                poi_id="curated:poi-z",
                source_ids=("source-a",),
            ),
        ),
    )
    request = _request(
        evidence=evidence,
        start_origin=DiscoveryOrigin(
            latitude=10.123456,
            longitude=106.654321,
        ),
    )

    serialized = serialize_itinerary_request(request)
    payload = json.loads(serialized)

    assert serialized == json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert set(payload) == {
        "approved_assumptions",
        "candidates",
        "city",
        "claims",
        "constraints",
        "end_local_time",
        "local_date",
        "source_ids",
        "start_local_time",
        "timezone",
    }
    assert set(payload["candidates"][0]) == {
        "canonical_name",
        "category",
        "distance_metres",
        "id",
    }
    forbidden = (
        "latitude",
        "longitude",
        "provider_id",
        "address",
        "https://",
        "publisher",
        "retrieved_at",
        "evidence_id",
        "start_origin",
        "database",
        "trip",
        "uid",
        "token",
    )
    assert not any(value in serialized.casefold() for value in forbidden)


def test_sdk_agent_and_run_configuration_are_locked_down() -> None:
    request = _request()
    runner = _RecordingRunner(_FakeRunResult(plan_itinerary(request)))

    output = asyncio.run(_executor(runner).draft(request))

    assert output == plan_itinerary(request)
    assert len(runner.calls) == 1
    agent, _, max_turns, run_config = runner.calls[0]
    assert agent.name == "travel_itinerary"
    assert agent.output_type is ItineraryOutput
    assert agent.tools == []
    assert agent.handoffs == []
    assert agent.mcp_servers == []
    assert agent.model == "private-test-model"
    assert agent.model_settings.tool_choice == "none"
    assert agent.model_settings.parallel_tool_calls is False
    assert agent.model_settings.retry is not None
    assert agent.model_settings.retry.max_retries == 0
    assert max_turns == ITINERARY_MAX_TURNS == 1
    assert run_config.tracing_disabled is True
    assert run_config.trace_include_sensitive_data is False
    assert run_config.trace_id is None
    assert run_config.group_id is None
    assert run_config.trace_metadata is None
    assert run_config.session_settings is None


def test_default_runner_passes_no_session_or_response_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    captured: dict[str, object] = {}

    async def fake_run(
        starting_agent: Agent[None],
        model_input: str,
        **kwargs: object,
    ) -> _FakeRunResult:
        captured["agent"] = starting_agent
        captured["input"] = model_input
        captured["kwargs"] = kwargs
        return _FakeRunResult(plan_itinerary(request))

    monkeypatch.setattr(
        "app.agents.itinerary.executor.Runner.run",
        fake_run,
    )

    output = asyncio.run(
        OpenAIItineraryExecutor(
            api_key="private-test-key",
            model="private-test-model",
        ).draft(request)
    )

    assert output == plan_itinerary(request)
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert set(kwargs) == {"max_turns", "run_config"}


@pytest.mark.parametrize(
    "result",
    [
        _FakeRunResult("plain text"),
        _FakeRunResult(object()),
        RuntimeError("raw private model exception"),
    ],
)
def test_executor_invalid_output_and_failure_fall_back(
    result: _FakeRunResult | BaseException,
) -> None:
    request = _request()
    runner = _RecordingRunner(result)

    output = asyncio.run(_executor(runner).draft(request))

    assert output == plan_itinerary(request)
    assert len(runner.calls) == 1


def test_executor_invalid_structured_output_falls_back() -> None:
    request = _request()
    output = plan_itinerary(request)
    invalid = output.model_copy(
        update={
            "items": (
                output.items[0].model_copy(update={"title": "Tên bịa"}),
                *output.items[1:],
            )
        }
    )
    runner = _RecordingRunner(_FakeRunResult(invalid))

    result = asyncio.run(_executor(runner).draft(request))

    assert result == output
    assert len(runner.calls) == 1


def test_executor_and_service_propagate_cancellation() -> None:
    request = _request()
    runner = _RecordingRunner(asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_executor(runner).draft(request))

    fake = _FakeExecutor(asyncio.CancelledError())
    service = ItineraryService(executor_factory=lambda: fake)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(service.draft(request))
    assert fake.calls == 1


def test_environment_configuration_requires_key_and_explicit_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    monkeypatch.delenv(OPENAI_ITINERARY_MODEL_ENV, raising=False)
    assert OpenAIItineraryExecutor.from_environment() is None

    monkeypatch.setenv(OPENAI_API_KEY_ENV, " key ")
    assert OpenAIItineraryExecutor.from_environment() is None

    monkeypatch.delenv(OPENAI_API_KEY_ENV)
    monkeypatch.setenv(OPENAI_ITINERARY_MODEL_ENV, " model ")
    assert OpenAIItineraryExecutor.from_environment() is None

    monkeypatch.setenv(OPENAI_API_KEY_ENV, " key ")
    configured = OpenAIItineraryExecutor.from_environment()
    assert configured is not None
    assert configured._agent.model == "model"


@pytest.mark.parametrize(
    "api_key,model",
    [
        ("", "model"),
        (" ", "model"),
        ("key", ""),
        ("key", " "),
    ],
)
def test_blank_configuration_is_rejected(
    api_key: str,
    model: str,
) -> None:
    with pytest.raises(ValueError, match="nonblank"):
        OpenAIItineraryExecutor(api_key=api_key, model=model)


def test_service_missing_or_failed_configuration_uses_fallback() -> None:
    request = _request()
    missing = ItineraryService(executor_factory=lambda: None)

    def broken_factory() -> None:
        raise RuntimeError("private configuration failure")

    broken = ItineraryService(executor_factory=broken_factory)

    assert asyncio.run(missing.draft(request)) == plan_itinerary(request)
    assert asyncio.run(broken.draft(request)) == plan_itinerary(request)


def test_service_revalidates_executor_output_and_never_retries() -> None:
    request = _request()
    invalid = _FakeExecutor("raw output")
    service = ItineraryService(executor_factory=lambda: invalid)

    output = asyncio.run(service.draft(request))

    assert output == plan_itinerary(request)
    assert invalid.calls == 1


def test_logs_exclude_private_input_output_and_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = _request(notes=("Ghi chú cực kỳ riêng tư",))
    raw_exception = "raw-secret-exception"
    executor = _FakeExecutor(RuntimeError(raw_exception))
    service = ItineraryService(executor_factory=lambda: executor)

    with caplog.at_level(
        logging.INFO,
        logger="travel_assistant.agents.itinerary",
    ):
        output = asyncio.run(service.draft(request))

    assert output == plan_itinerary(request)
    logs = caplog.text
    assert "operation=draft" in logs
    assert "path=deterministic" in logs
    assert "city=hcmc" not in logs
    assert "items=3" in logs
    forbidden = (
        raw_exception,
        "Ghi chú cực kỳ riêng tư",
        "Điểm gần nhất",
        "curated:poi-z",
        "private-test-key",
        "10.77",
        "106.69",
        "claim",
        "source",
    )
    assert not any(value in logs for value in forbidden)


def test_package_imports_without_external_configuration_or_network() -> None:
    script = """\
import socket
def blocked(*args, **kwargs):
    raise AssertionError("network attempted")
socket.create_connection = blocked
import app.agents.itinerary
assert "app.db.runtime" not in __import__("sys").modules
assert "firebase_admin" not in __import__("sys").modules
print("ok")
"""
    environment = os.environ.copy()
    for name in (
        OPENAI_API_KEY_ENV,
        OPENAI_ITINERARY_MODEL_ENV,
        "DATABASE_URL",
        "FIREBASE_PROJECT_ID",
    ):
        environment.pop(name, None)

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


def test_static_instructions_cover_t045_boundaries() -> None:
    normalized = " ".join(ITINERARY_INSTRUCTIONS.casefold().split())

    for phrase in (
        "itineraryoutput",
        "một ngày",
        "không chồng lấn",
        "maximum_stops",
        "itinerary-item-001",
        "draft_only=true",
        "thời gian di chuyển",
        "giờ mở cửa",
        "không đọc hoặc sửa lịch trình đã lưu",
    ):
        assert phrase in normalized


def test_fastapi_route_set_adds_only_structured_itinerary_generation() -> None:
    settings = Settings(
        database_url=SecretStr(
            "postgresql+asyncpg://unused:unused@invalid/unused"
        ),
        firebase_project_id="itinerary-test",
        application_environment=ApplicationEnvironment.TEST,
    )

    paths = set(create_app(settings).openapi()["paths"])

    assert paths == {
        "/health",
        "/auth/me",
        "/preferences",
        "/pois/nearby",
        "/v1/assistant/query",
        "/v1/itinerary-drafts/generate",
        "/v1/itineraries",
        "/v1/itineraries/{itinerary_id}",
    }
