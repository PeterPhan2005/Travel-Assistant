"""Deterministic rules, SDK isolation, closure, and privacy tests for T046."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest
from agents import Agent, RunConfig
from pydantic import HttpUrl, SecretStr

from app.agents.contracts import (
    AgentKind,
    AgentWarning,
    AnswerStatus,
    ClaimRejectionReason,
    CultureGuidanceItem,
    DiscoveryCandidate,
    DiscoveryCompleteness,
    DiscoveryOutput,
    DiscoverySpecialistOutput,
    EvidenceBundle,
    FactKind,
    FactualClaim,
    FailureCode,
    FreshnessRequirement,
    GroundingCandidateClaim,
    GroundingCandidateEvidence,
    GroundingCandidatePrice,
    GroundingReviewOutput,
    GroundingReviewRequest,
    GroundingReviewStatus,
    ItineraryItem,
    ItineraryOutput,
    ItinerarySpecialistOutput,
    LocalCultureOutput,
    LocalCultureSpecialistOutput,
    NarrationOutput,
    NarrationSpecialistOutput,
    PriceFact,
    RejectedClaim,
    SourceRecord,
    SourceType,
    SupportedCity,
)
from app.agents.grounding import (
    GroundingReviewerService,
    OpenAIGroundingReviewerExecutor,
    build_deterministic_review,
    validate_grounding_review_output,
)
from app.agents.grounding.executor import (
    GROUNDING_MAX_TURNS,
    OPENAI_API_KEY_ENV,
    OPENAI_GROUNDING_MODEL_ENV,
    serialize_grounding_review_request,
)
from app.agents.grounding.instructions import (
    GROUNDING_REVIEWER_INSTRUCTIONS,
)
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


def _source(
    source_id: str = "source-a",
    *,
    retrieved_at: datetime | None = NOW,
    label: str | None = None,
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_INSTITUTION,
        label=label or f"Nhãn nguồn riêng {source_id}",
        publisher="Đơn vị quản lý riêng",
        url=HttpUrl(f"https://example.test/{source_id}"),
        published_at=None,
        retrieved_at=retrieved_at,
    )


def _claim(
    claim_id: str = "claim-a",
    *,
    source_ids: tuple[str, ...] = ("source-a",),
    fact_kind: FactKind = FactKind.HISTORY,
    poi_id: str | None = "curated:poi-a",
    freshness_at: datetime | None = NOW,
    price: PriceFact | None = None,
) -> FactualClaim:
    return FactualClaim(
        claim_id=claim_id,
        evidence_id=f"evidence-{claim_id}",
        fact_kind=fact_kind,
        statement=f"Thông tin đã xác nhận riêng cho {claim_id}.",
        supporting_source_ids=source_ids,
        poi_id=poi_id,
        freshness_at=freshness_at,
        price=price,
    )


def _price_claim(
    claim_id: str = "claim-price",
    *,
    freshness_at: datetime = NOW,
) -> FactualClaim:
    return _claim(
        claim_id,
        fact_kind=FactKind.PRICE,
        freshness_at=freshness_at,
        price=PriceFact(
            price_minor_units=125_000,
            currency="VND",
            source_updated_at=freshness_at,
        ),
    )


def _candidate_claim(
    claim_id: str = "claim-a",
    *,
    evidence_id: str | None = None,
    source_ids: tuple[str, ...] = ("source-a",),
    fact_kind: FactKind = FactKind.HISTORY,
    poi_id: str | None = "curated:poi-a",
    freshness_at: datetime | None = NOW,
    price: GroundingCandidatePrice | None = None,
    statement: str | None = None,
) -> GroundingCandidateClaim:
    return GroundingCandidateClaim(
        claim_id=claim_id,
        evidence_id=evidence_id or f"evidence-{claim_id}",
        fact_kind=fact_kind,
        statement=statement or f"Thông tin đã xác nhận riêng cho {claim_id}.",
        supporting_source_ids=source_ids,
        poi_id=poi_id,
        freshness_at=freshness_at,
        price=price,
    )


def _candidate_price_claim(
    claim_id: str = "claim-price",
    *,
    freshness_at: datetime | None = NOW,
    source_updated_at: datetime | None = NOW,
) -> GroundingCandidateClaim:
    return _candidate_claim(
        claim_id,
        fact_kind=FactKind.PRICE,
        freshness_at=freshness_at,
        price=GroundingCandidatePrice(
            price_minor_units=125_000,
            currency="VND",
            source_updated_at=source_updated_at,
        ),
    )


def _request(
    *,
    sources: tuple[SourceRecord, ...] = (_source(),),
    claims: tuple[FactualClaim | GroundingCandidateClaim, ...] = (_claim(),),
    specialist_outputs: tuple[
        DiscoverySpecialistOutput
        | NarrationSpecialistOutput
        | LocalCultureSpecialistOutput
        | ItinerarySpecialistOutput,
        ...,
    ] = (),
    freshness_requirements: tuple[FreshnessRequirement, ...] = (),
) -> GroundingReviewRequest:
    candidate_claims = tuple(
        claim
        if isinstance(claim, GroundingCandidateClaim)
        else GroundingCandidateClaim.from_approved(claim)
        for claim in claims
    )
    return GroundingReviewRequest(
        evidence=GroundingCandidateEvidence(
            sources=sources,
            claims=candidate_claims,
        ),
        specialist_outputs=specialist_outputs,
        freshness_requirements=freshness_requirements,
    )


def _candidate() -> DiscoveryCandidate:
    source = _source()
    return DiscoveryCandidate(
        id="curated:poi-a",
        provider=PoiProviderKind.CURATED,
        provider_id="poi-a",
        canonical_name="Điểm đến riêng",
        city=SupportedCity.HCMC,
        category="museum",
        address=None,
        coordinates=Coordinates(latitude=10.77, longitude=106.69),
        distance_metres=100.0,
        rating=None,
        rating_count=None,
        price_level=None,
        opening_hours_summary=None,
        sources=(
            SourceReference(
                source_id=source.source_id,
                source_type=source.source_type.value,
                label=source.label,
                publisher=source.publisher,
                url=source.url,
                published_at=source.published_at,
                retrieved_at=source.retrieved_at,
            ),
        ),
        retrieved_at=NOW,
        is_curated=True,
        is_externally_supplied=False,
    )


def _discovery_specialist(
    evidence: EvidenceBundle | None = None,
) -> DiscoverySpecialistOutput:
    evidence = evidence or EvidenceBundle(
        sources=(_source(),),
        claims=(_claim(),),
    )
    return DiscoverySpecialistOutput(
        agent=AgentKind.DISCOVERY,
        output_id="output-discovery",
        output=DiscoveryOutput(
            candidates=(_candidate(),),
            evidence=evidence,
            provider_failures=(),
            completeness=DiscoveryCompleteness.COMPLETE,
            is_truncated=False,
        ),
    )


def _narration_specialist(
    *,
    claim_ids: tuple[str, ...] = ("claim-a",),
    source_ids: tuple[str, ...] = ("source-a",),
) -> NarrationSpecialistOutput:
    return NarrationSpecialistOutput(
        agent=AgentKind.NARRATION,
        output_id="output-narration",
        output=NarrationOutput(
            status=AnswerStatus.COMPLETE,
            narration_text=" ".join(["Thông tin"] * 100),
            key_points=("Điểm chính đã xác nhận.",),
            used_source_ids=source_ids,
            used_claim_ids=claim_ids,
            limitation_reason=None,
        ),
    )


def _limited_narration() -> NarrationSpecialistOutput:
    return NarrationSpecialistOutput(
        agent=AgentKind.NARRATION,
        output_id="output-narration",
        output=NarrationOutput(
            status=AnswerStatus.LIMITED,
            narration_text=None,
            key_points=(),
            used_source_ids=(),
            used_claim_ids=(),
            limitation_reason="Chưa có đủ bằng chứng phù hợp.",
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
                    text="Hãy giữ giọng nói nhỏ tại địa điểm.",
                    claim_ids=("claim-culture",),
                    source_ids=("source-a",),
                ),
            ),
            respectful_caution=None,
            limitation_reason=None,
        ),
    )


def _limited_culture() -> LocalCultureSpecialistOutput:
    return LocalCultureSpecialistOutput(
        agent=AgentKind.LOCAL_CULTURE,
        output_id="output-culture",
        output=LocalCultureOutput(
            status=AnswerStatus.LIMITED,
            guidance=(),
            respectful_caution=None,
            limitation_reason="Chưa có đủ bằng chứng phù hợp.",
        ),
    )


def _itinerary_specialist(
    *,
    claim_ids: tuple[str, ...] = (),
    source_ids: tuple[str, ...] = (),
    poi_id: str = "curated:poi-a",
) -> ItinerarySpecialistOutput:
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
                    poi_id=poi_id,
                    title="Điểm đến riêng",
                    start_local_time=time(9, 0),
                    end_local_time=time(10, 0),
                    supporting_claim_ids=claim_ids,
                    supporting_source_ids=source_ids,
                ),
            ),
            assumptions=("Đây là lịch trình nháp.",),
            warnings=(),
            draft_only=True,
        ),
    )


def _freshness(
    fact_kind: FactKind = FactKind.HISTORY,
    *,
    maximum_age_seconds: int = 86_400,
) -> FreshnessRequirement:
    return FreshnessRequirement(
        fact_kind=fact_kind,
        as_of=NOW,
        maximum_age_seconds=maximum_age_seconds,
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

    async def review(
        self,
        request: GroundingReviewRequest,
    ) -> GroundingReviewOutput:
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
) -> OpenAIGroundingReviewerExecutor:
    return OpenAIGroundingReviewerExecutor(
        api_key=api_key,
        model=model,
        runner=runner,
    )


def _reason(
    output: GroundingReviewOutput,
    claim_id: str,
) -> ClaimRejectionReason:
    return next(
        rejection.reason
        for rejection in output.rejected_claims
        if rejection.claim_id == claim_id
    )


def test_supported_sourced_claim_is_approved() -> None:
    output = build_deterministic_review(_request())

    assert output.status is GroundingReviewStatus.APPROVED
    assert output.approved_claim_ids == ("claim-a",)
    assert output.rejected_claims == ()


@pytest.mark.parametrize(
    "source_ids",
    [(), ("source-unknown",)],
)
def test_missing_or_unknown_source_is_rejected(
    source_ids: tuple[str, ...],
) -> None:
    request = _request(
        sources=(_source(),),
        claims=(_candidate_claim(source_ids=source_ids),),
    )

    output = build_deterministic_review(request)

    assert _reason(output, "claim-a") is ClaimRejectionReason.MISSING_SOURCE


def test_missing_claim_freshness_is_flagged() -> None:
    request = _request(
        sources=(_source(),),
        claims=(_candidate_price_claim(freshness_at=None),),
    )

    output = build_deterministic_review(request)

    assert _reason(
        output,
        "claim-price",
    ) is ClaimRejectionReason.MISSING_PRICE_TIMESTAMP


def test_missing_price_source_timestamp_is_flagged() -> None:
    request = _request(
        claims=(_candidate_price_claim(source_updated_at=None),),
    )

    output = build_deterministic_review(request)

    assert _reason(
        output,
        "claim-price",
    ) is ClaimRejectionReason.MISSING_PRICE_TIMESTAMP


def test_missing_price_data_is_flagged() -> None:
    claim = _candidate_claim(
        "claim-price",
        fact_kind=FactKind.PRICE,
        price=None,
    )

    output = build_deterministic_review(_request(claims=(claim,)))

    assert _reason(
        output,
        "claim-price",
    ) is ClaimRejectionReason.MISSING_PRICE_TIMESTAMP


def test_valid_price_timestamp_and_integer_currency_are_approved() -> None:
    output = build_deterministic_review(
        _request(claims=(_price_claim(),))
    )

    assert output.approved_claim_ids == ("claim-price",)


def test_price_freshness_mismatch_is_rejected() -> None:
    output = build_deterministic_review(
        _request(
            sources=(_source(),),
            claims=(
                _candidate_price_claim(
                    source_updated_at=NOW - timedelta(hours=1),
                ),
            ),
        )
    )

    assert _reason(
        output,
        "claim-price",
    ) is ClaimRejectionReason.INCONSISTENT_EVIDENCE


def test_nonprice_claim_with_candidate_price_is_inconsistent() -> None:
    claim = _candidate_claim(
        price=GroundingCandidatePrice(
            price_minor_units=125_000,
            currency="VND",
            source_updated_at=NOW,
        )
    )

    output = build_deterministic_review(_request(claims=(claim,)))

    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.INCONSISTENT_EVIDENCE


def test_duplicate_claim_identity_is_reviewed_canonically() -> None:
    duplicate_claim = _candidate_claim()

    output = build_deterministic_review(
        _request(claims=(duplicate_claim, duplicate_claim))
    )

    assert output.reviewed_claim_ids == ("claim-a",)
    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.INCONSISTENT_EVIDENCE


def test_conflicting_claim_identity_is_inconsistent() -> None:
    conflicting_claim = _candidate_claim(
        statement="Thông tin mâu thuẫn nhưng hợp lệ về cấu trúc.",
    )

    output = build_deterministic_review(
        _request(claims=(_candidate_claim(), conflicting_claim))
    )

    assert output.reviewed_claim_ids == ("claim-a",)
    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.INCONSISTENT_EVIDENCE


def test_conflicting_source_identity_is_inconsistent() -> None:
    request = _request(
        sources=(
            _source(),
            _source(label="Nhãn nguồn xung đột hợp lệ."),
        ),
    )

    output = build_deterministic_review(request)

    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.INCONSISTENT_EVIDENCE


def test_duplicate_identical_source_is_representable_and_not_a_conflict() -> None:
    source = _source()

    output = build_deterministic_review(
        _request(sources=(source, source))
    )

    assert output.approved_claim_ids == ("claim-a",)


def test_duplicate_evidence_id_rejects_every_affected_claim() -> None:
    first = _candidate_claim("claim-a", evidence_id="evidence-shared")
    second = _candidate_claim("claim-b", evidence_id="evidence-shared")

    output = build_deterministic_review(
        _request(claims=(first, second))
    )

    assert output.reviewed_claim_ids == ("claim-a", "claim-b")
    assert all(
        _reason(output, claim_id)
        is ClaimRejectionReason.INCONSISTENT_EVIDENCE
        for claim_id in output.reviewed_claim_ids
    )


def test_stale_and_fresh_evidence_use_only_supplied_reference_time() -> None:
    stale = _claim(
        "claim-stale",
        freshness_at=NOW - timedelta(days=2),
    )
    fresh = _claim(
        "claim-fresh",
        freshness_at=NOW - timedelta(hours=1),
    )
    request = _request(
        claims=(fresh, stale),
        freshness_requirements=(_freshness(),),
    )

    first = build_deterministic_review(request)
    second = build_deterministic_review(request)

    assert first.approved_claim_ids == ("claim-fresh",)
    assert _reason(
        first,
        "claim-stale",
    ) is ClaimRejectionReason.STALE_EVIDENCE
    assert first.model_dump_json() == second.model_dump_json()


def test_future_timestamp_is_inconsistent_against_supplied_as_of() -> None:
    request = _request(
        claims=(
            _candidate_claim(
                freshness_at=NOW + timedelta(seconds=1),
            ),
        ),
        freshness_requirements=(_freshness(),),
    )

    output = build_deterministic_review(request)

    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.INCONSISTENT_EVIDENCE


def test_missing_nonprice_freshness_is_unsupported() -> None:
    claim = _claim(freshness_at=None)
    request = _request(
        sources=(_source(retrieved_at=None),),
        claims=(claim,),
        freshness_requirements=(_freshness(),),
    )

    output = build_deterministic_review(request)

    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.UNSUPPORTED_CLAIM


def test_stale_supporting_source_cannot_be_hidden_by_fresh_claim_time() -> None:
    request = _request(
        sources=(
            _source(retrieved_at=NOW - timedelta(days=2)),
        ),
        freshness_requirements=(_freshness(),),
    )

    output = build_deterministic_review(request)

    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.STALE_EVIDENCE


def test_decisions_are_disjoint_complete_sorted_and_byte_deterministic() -> None:
    request = _request(
        sources=(_source(),),
        claims=(
            _claim("claim-a"),
            _candidate_claim("claim-b", source_ids=()),
        ),
    )

    first = build_deterministic_review(request)
    second = build_deterministic_review(request)
    rejected_ids = {
        rejection.claim_id for rejection in first.rejected_claims
    }

    assert not set(first.approved_claim_ids) & rejected_ids
    assert set(first.reviewed_claim_ids) == (
        set(first.approved_claim_ids) | rejected_ids
    )
    assert first.model_dump_json() == second.model_dump_json()


def test_discovery_output_with_exact_evidence_is_approved() -> None:
    evidence = EvidenceBundle(sources=(_source(),), claims=(_claim(),))
    specialist = _discovery_specialist(evidence)
    output = build_deterministic_review(
        _request(
            specialist_outputs=(specialist,),
        )
    )

    assert output.approved_specialist_output_ids == ("output-discovery",)


def test_discovery_without_candidate_provenance_is_not_approved() -> None:
    specialist = _discovery_specialist().model_copy(
        update={
            "output": _discovery_specialist().output.model_copy(
                update={
                    "candidates": (
                        _candidate().model_copy(update={"sources": ()}),
                    )
                }
            )
        }
    )
    output = build_deterministic_review(
        _request(
            sources=(_source(),),
            claims=(_claim(),),
            specialist_outputs=(specialist,),
        )
    )

    assert output.approved_specialist_output_ids == ()


def test_complete_and_limited_narration_are_approved_when_closed() -> None:
    complete = build_deterministic_review(
        _request(specialist_outputs=(_narration_specialist(),))
    )
    limited = build_deterministic_review(
        _request(
            sources=(),
            claims=(),
            specialist_outputs=(_limited_narration(),),
        )
    )

    assert complete.approved_specialist_output_ids == ("output-narration",)
    assert limited.approved_specialist_output_ids == ("output-narration",)


def test_narration_referencing_rejected_claim_is_not_approved() -> None:
    request = _request(
        sources=(_source(),),
        claims=(_candidate_claim(source_ids=()),),
        specialist_outputs=(_narration_specialist(),),
    )

    output = build_deterministic_review(request)

    assert output.status is GroundingReviewStatus.REJECTED
    assert output.approved_specialist_output_ids == ()


def test_unknown_specialist_claim_is_not_invented_or_approved() -> None:
    request = _request(
        specialist_outputs=(
            _narration_specialist(
                claim_ids=("claim-a", "claim-unknown"),
            ),
        ),
    )

    output = build_deterministic_review(request)

    assert output.reviewed_claim_ids == ("claim-a",)
    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.UNSUPPORTED_CLAIM
    assert output.approved_specialist_output_ids == ()


def test_complete_and_limited_culture_are_approved_when_closed() -> None:
    culture_claim = _claim(
        "claim-culture",
        fact_kind=FactKind.CULTURE,
        poi_id=None,
    )
    complete = build_deterministic_review(
        _request(
            claims=(culture_claim,),
            specialist_outputs=(_culture_specialist(),),
        )
    )
    limited = build_deterministic_review(
        _request(
            sources=(),
            claims=(),
            specialist_outputs=(_limited_culture(),),
        )
    )

    assert complete.approved_specialist_output_ids == ("output-culture",)
    assert limited.approved_specialist_output_ids == ("output-culture",)


def test_culture_referencing_rejected_claim_is_not_approved() -> None:
    culture_claim = _candidate_claim(
        "claim-culture",
        fact_kind=FactKind.CULTURE,
        poi_id=None,
        source_ids=(),
    )
    output = build_deterministic_review(
        _request(
            sources=(_source(),),
            claims=(culture_claim,),
            specialist_outputs=(_culture_specialist(),),
        )
    )

    assert output.approved_specialist_output_ids == ()


def test_itinerary_valid_evidence_and_evidence_free_item_are_approved() -> None:
    evidenced = build_deterministic_review(
        _request(
            specialist_outputs=(
                _itinerary_specialist(
                    claim_ids=("claim-a",),
                    source_ids=("source-a",),
                ),
            )
        )
    )
    evidence_free = build_deterministic_review(
        _request(
            sources=(),
            claims=(),
            specialist_outputs=(_itinerary_specialist(),),
        )
    )

    assert evidenced.approved_specialist_output_ids == ("output-itinerary",)
    assert evidence_free.approved_specialist_output_ids == (
        "output-itinerary",
    )


def test_itinerary_claim_for_wrong_poi_is_rejected() -> None:
    output = build_deterministic_review(
        _request(
            specialist_outputs=(
                _itinerary_specialist(
                    claim_ids=("claim-a",),
                    source_ids=("source-a",),
                    poi_id="curated:poi-b",
                ),
            )
        )
    )

    assert _reason(
        output,
        "claim-a",
    ) is ClaimRejectionReason.UNSUPPORTED_CLAIM
    assert output.approved_specialist_output_ids == ()


def test_reviewer_schema_cannot_return_replacement_or_specialist_content() -> None:
    fields = set(GroundingReviewOutput.model_fields)
    rejection_fields = set(RejectedClaim.model_fields)

    assert fields == {
        "status",
        "reviewed_claim_ids",
        "approved_claim_ids",
        "rejected_claims",
        "approved_specialist_output_ids",
        "warnings",
    }
    assert rejection_fields == {"claim_id", "reason"}
    for forbidden in (
        "statement",
        "replacement",
        "narration",
        "guidance",
        "itinerary",
        "source",
        "price",
        "timestamp",
    ):
        assert forbidden not in fields


def test_invented_claim_output_and_warning_are_rejected_by_closure() -> None:
    request = _request(specialist_outputs=(_narration_specialist(),))
    deterministic = build_deterministic_review(request)
    invented_claim = GroundingReviewOutput(
        status=GroundingReviewStatus.APPROVED,
        reviewed_claim_ids=("claim-invented",),
        approved_claim_ids=("claim-invented",),
        rejected_claims=(),
        approved_specialist_output_ids=(),
        warnings=(),
    )
    invented_output = deterministic.model_copy(
        update={
            "approved_specialist_output_ids": ("output-invented",),
        }
    )
    invented_warning = deterministic.model_copy(
        update={
            "warnings": (
                AgentWarning(
                    stage=AgentKind.GROUNDING_REVIEWER,
                    code=FailureCode.GROUNDING_REJECTED,
                    message="Thông báo tự tạo.",
                    retryable=False,
                ),
            )
        }
    )

    for candidate in (invented_claim, invented_output, invented_warning):
        with pytest.raises((TypeError, ValueError)):
            validate_grounding_review_output(
                candidate,
                request,
                deterministic,
            )


def test_sdk_agent_and_run_configuration_are_locked_down() -> None:
    request = _request()
    expected = build_deterministic_review(request)
    runner = _RecordingRunner(_FakeRunResult(expected))

    output = asyncio.run(_executor(runner).review(request))

    assert output == expected
    assert len(runner.calls) == 1
    agent, _, max_turns, run_config = runner.calls[0]
    assert agent.name == "travel_grounding_reviewer"
    assert agent.output_type is GroundingReviewOutput
    assert agent.tools == []
    assert agent.handoffs == []
    assert agent.mcp_servers == []
    assert agent.model == "private-test-model"
    assert agent.model_settings.tool_choice == "none"
    assert agent.model_settings.parallel_tool_calls is False
    assert agent.model_settings.retry is not None
    assert agent.model_settings.retry.max_retries == 0
    assert max_turns == GROUNDING_MAX_TURNS == 1
    assert run_config.tracing_disabled is True
    assert run_config.trace_include_sensitive_data is False
    assert run_config.session_settings is None


@pytest.mark.parametrize("unexpected", ["plain text", {"status": "approved"}, 7])
def test_plain_text_and_wrong_model_output_fall_back(
    unexpected: object,
) -> None:
    request = _request()
    runner = _RecordingRunner(_FakeRunResult(unexpected))

    output = asyncio.run(_executor(runner).review(request))

    assert output == build_deterministic_review(request)
    assert len(runner.calls) == 1


def test_model_cannot_weaken_or_invent_stricter_claim_rejection() -> None:
    rejected_request = _request(
        sources=(_source(),),
        claims=(_candidate_claim(source_ids=()),),
    )
    deterministic_rejection = build_deterministic_review(rejected_request)
    weakened = GroundingReviewOutput(
        status=GroundingReviewStatus.APPROVED,
        reviewed_claim_ids=("claim-a",),
        approved_claim_ids=("claim-a",),
        rejected_claims=(),
        approved_specialist_output_ids=(),
        warnings=(),
    )
    approved_request = _request()
    unsupported_stricter = GroundingReviewOutput(
        status=GroundingReviewStatus.REJECTED,
        reviewed_claim_ids=("claim-a",),
        approved_claim_ids=(),
        rejected_claims=(
            RejectedClaim(
                claim_id="claim-a",
                reason=ClaimRejectionReason.UNSUPPORTED_CLAIM,
            ),
        ),
        approved_specialist_output_ids=(),
        warnings=(),
    )

    first = asyncio.run(
        _executor(
            _RecordingRunner(_FakeRunResult(weakened))
        ).review(rejected_request)
    )
    second = asyncio.run(
        _executor(
            _RecordingRunner(_FakeRunResult(unsupported_stricter))
        ).review(approved_request)
    )

    assert first == deterministic_rejection
    assert second == build_deterministic_review(approved_request)


def test_model_may_omit_an_otherwise_safe_specialist_output() -> None:
    request = _request(specialist_outputs=(_narration_specialist(),))
    deterministic = build_deterministic_review(request)
    stricter = deterministic.model_copy(
        update={"approved_specialist_output_ids": ()}
    )

    output = asyncio.run(
        _executor(
            _RecordingRunner(_FakeRunResult(stricter))
        ).review(request)
    )

    assert output.approved_specialist_output_ids == ()
    assert output.approved_claim_ids == deterministic.approved_claim_ids


def test_sdk_failure_and_service_failure_fall_back_without_retry() -> None:
    request = _request()
    runner = _RecordingRunner(RuntimeError("raw private response"))
    executor = _FakeExecutor(RuntimeError("different private response"))

    direct = asyncio.run(_executor(runner).review(request))
    serviced = asyncio.run(
        GroundingReviewerService(
            executor_factory=lambda: executor
        ).review(request)
    )

    assert direct == build_deterministic_review(request)
    assert serviced == direct
    assert len(runner.calls) == 1
    assert executor.calls == 1


def test_cancellation_propagates_without_fallback_or_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner = _RecordingRunner(asyncio.CancelledError())
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.grounding",
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            GroundingReviewerService(
                executor_factory=lambda: _executor(runner)
            ).review(_request())
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
def test_missing_or_blank_configuration_uses_deterministic_review(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    model: str | None,
) -> None:
    if api_key is None:
        monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_API_KEY_ENV, api_key)
    if model is None:
        monkeypatch.delenv(OPENAI_GROUNDING_MODEL_ENV, raising=False)
    else:
        monkeypatch.setenv(OPENAI_GROUNDING_MODEL_ENV, model)

    output = asyncio.run(GroundingReviewerService().review(_request()))

    assert output == build_deterministic_review(_request())


def test_serialization_is_compact_sorted_and_excludes_private_metadata() -> None:
    request = _request(specialist_outputs=(_narration_specialist(),))

    serialized = serialize_grounding_review_request(request)
    payload = json.loads(serialized)

    assert serialized == json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert payload["reviewed_claim_ids"] == ["claim-a"]
    assert payload["reviewed_specialist_output_ids"] == ["output-narration"]
    assert "Thông tin đã xác nhận riêng" in serialized
    for private in (
        "Nhãn nguồn riêng",
        "Đơn vị quản lý riêng",
        "https://",
        "DATABASE_URL",
        "FIREBASE",
        "OPENAI",
        "latitude",
        "longitude",
        "origin",
    ):
        assert private not in serialized


def test_safe_logs_exclude_content_ids_configuration_and_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_error = "raw private exception response"
    executor = _FakeExecutor(RuntimeError(private_error))
    caplog.set_level(
        logging.INFO,
        logger="travel_assistant.agents.grounding",
    )

    output = asyncio.run(
        GroundingReviewerService(
            executor_factory=lambda: executor
        ).review(_request())
    )

    assert output.status is GroundingReviewStatus.APPROVED
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "operation=review path=deterministic status=approved" in logs
    for private in (
        private_error,
        "private-key",
        "private-model",
        "claim-a",
        "source-a",
        "curated:poi-a",
        "Thông tin đã xác nhận",
        "Nhãn nguồn riêng",
        "125000",
        NOW.isoformat(),
    ):
        assert private not in logs


def test_static_instructions_lock_closed_review_and_no_new_facts() -> None:
    normalized = " ".join(
        GROUNDING_REVIEWER_INSTRUCTIONS.casefold().split()
    )
    for required in (
        "only the grounding reviewer",
        "return only the groundingreviewoutput",
        "never write replacement facts",
        "never introduce a claim id",
        "missing_source",
        "missing_price_timestamp",
        "supplied freshness requirements",
        "never use the current time",
        "disjoint and complete",
        "chain of thought",
    ):
        assert required in normalized


def test_package_import_needs_no_environment_or_network() -> None:
    script = """
import socket
def blocked(*args, **kwargs):
    raise AssertionError("network")
socket.create_connection = blocked
socket.socket.connect = blocked
import app.agents.grounding
print("ok")
"""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            OPENAI_API_KEY_ENV,
            OPENAI_GROUNDING_MODEL_ENV,
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


def test_dependency_routes_settings_and_scope_are_unchanged() -> None:
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
    assert OPENAI_GROUNDING_MODEL_ENV.casefold() not in Settings.model_fields

    package = BACKEND / "app" / "agents" / "grounding"
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
        "responsecomposer",
    ):
        assert forbidden not in combined
