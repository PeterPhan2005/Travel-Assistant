"""Strict immutable contracts for offline labeled agent evaluations."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, model_validator

from app.agents.contracts import (
    ContractModel,
    DiscoveryCompleteness,
    FailureCode,
    GroundingReviewStatus,
    IntentKind,
    RuntimeResultStatus,
    SpecialistKind,
    SupportedCity,
)
from app.agents.contracts.narration import AnswerStatus
from app.agents.itinerary.errors import ItineraryFailureReason

MAX_EVAL_CASES = 500
MAX_CHECKS = 32
MAX_TAGS = 24
MAX_COUNT = 100_000
MAX_CASE_ID_LENGTH = 80
MAX_LABEL_LENGTH = 160
_CASE_ID_PATTERN = re.compile(
    r"^(router|discovery|narration|local-culture|itinerary|"
    r"grounding|composer|runtime)-[0-9]{3}$"
)
_TAG_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")


class AgentEvalTarget(StrEnum):
    """Closed evaluation target taxonomy in canonical execution order."""

    ROUTER = "router"
    DISCOVERY = "discovery"
    NARRATION = "narration"
    LOCAL_CULTURE = "local_culture"
    ITINERARY = "itinerary"
    GROUNDING_REVIEWER = "grounding_reviewer"
    RESPONSE_COMPOSER = "response_composer"
    RUNTIME = "runtime"


TARGET_ORDER = tuple(AgentEvalTarget)


class EvalCheckCode(StrEnum):
    """Closed, application-owned assertion taxonomy."""

    CONTRACT_VALID = "contract_valid"
    DETERMINISTIC_REPEAT = "deterministic_repeat"
    EVIDENCE_CLOSED = "evidence_closed"
    EXPECTED_FAILURE = "expected_failure"
    EXPECTED_INTENT = "expected_intent"
    EXPECTED_ITEMS = "expected_items"
    EXPECTED_ORDER = "expected_order"
    EXPECTED_PLAN = "expected_plan"
    EXPECTED_STATUS = "expected_status"
    EXPECTED_WARNING = "expected_warning"
    NO_NEW_FACT = "no_new_fact"
    NO_OVERLAP = "no_overlap"
    NO_UNEXPECTED_CALL = "no_unexpected_call"
    OPTIONAL_FIELDS_OMITTED = "optional_fields_omitted"
    PRIVACY_SAFE = "privacy_safe"
    SOURCE_UNION_EXACT = "source_union_exact"
    TIME_WINDOW_EXACT = "time_window_exact"
    WARNING_PRESERVED = "warning_preserved"


class RouterScenario(StrEnum):
    NEARBY_HCMC = "nearby_hcmc"
    POI_INFORMATION = "poi_information"
    CULTURE_CITY_CONFLICT = "culture_city_conflict"
    ITINERARY_BANGKOK = "itinerary_bangkok"
    GENERAL_HELP = "general_help"
    UNSUPPORTED = "unsupported"


class DiscoveryScenario(StrEnum):
    COMPLETE_ORDERED = "complete_ordered"
    EMPTY_COMPLETE = "empty_complete"
    PARTIAL_MENU = "partial_menu"
    TOTAL_PROVIDER_FAILURE = "total_provider_failure"
    CLOSED_OPTIONALS = "closed_optionals"


class NarrationScenario(StrEnum):
    COMPLETE_GROUNDED = "complete_grounded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNCONFIGURED = "unconfigured"
    INVALID_MODEL_OUTPUT = "invalid_model_output"
    INVALID_CLOSURE_AND_RANGE = "invalid_closure_and_range"


class LocalCultureScenario(StrEnum):
    COMPLETE_SUPPORTED = "complete_supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    STEREOTYPE_REJECTED = "stereotype_rejected"
    RESTRICTED_TOPIC_REJECTED = "restricted_topic_rejected"
    EXACT_UNION_AND_CAUTION = "exact_union_and_caution"


class ItineraryScenario(StrEnum):
    INPUT_ORDER_SELECTION = "input_order_selection"
    CONSTRAINT_SELECTION = "constraint_selection"
    EXACT_SCHEDULE = "exact_schedule"
    IMPOSSIBLE_WINDOW = "impossible_window"
    INVALID_MODEL_FALLBACK = "invalid_model_fallback"


class GroundingScenario(StrEnum):
    VALID_APPROVAL = "valid_approval"
    MISSING_SOURCE = "missing_source"
    MISSING_PRICE_TIMESTAMP = "missing_price_timestamp"
    STALE_EVIDENCE = "stale_evidence"
    CONFLICT_WITHHELD = "conflict_withheld"


class ComposerScenario(StrEnum):
    SAFE_FALLBACK = "safe_fallback"
    NARRATION_EXACT = "narration_exact"
    CULTURE_ITINERARY = "culture_itinerary"
    DISCOVERY_ORDER_OMISSION = "discovery_order_omission"
    PRICE_AND_WARNING = "price_and_warning"


class RuntimeScenario(StrEnum):
    COMPLETE_SUCCESS = "complete_success"
    SPECIALIST_FAILURE_PARTIAL = "specialist_failure_partial"
    DISCOVERY_WARNING_PARTIAL = "discovery_warning_partial"
    MISSING_ITINERARY_WINDOW = "missing_itinerary_window"
    GROUNDING_REJECTION = "grounding_rejection"
    RETRY_SUCCESS = "retry_success"
    LATENCY_BUDGET_FAILURE = "latency_budget_failure"


CaseId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=MAX_CASE_ID_LENGTH),
]
CaseLabel = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=MAX_LABEL_LENGTH),
]
CanonicalTag = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=40),
]
BoundedCount = Annotated[
    StrictInt,
    Field(ge=0, le=MAX_COUNT),
]
BasisPoints = Annotated[
    StrictInt,
    Field(ge=0, le=10_000),
]


class EvalExpected(ContractModel):
    """Closed expected assertions shared by every fixture case."""

    check_codes: Annotated[
        tuple[EvalCheckCode, ...],
        Field(min_length=1, max_length=MAX_CHECKS),
    ]
    status: str | None = Field(
        default=None,
        strict=True,
        min_length=1,
        max_length=64,
    )
    values: Annotated[
        tuple[str, ...],
        Field(max_length=20),
    ] = ()
    failure_code: str | None = Field(
        default=None,
        strict=True,
        min_length=1,
        max_length=64,
    )

    @model_validator(mode="after")
    def validate_expected(self) -> EvalExpected:
        """Keep check and value assertions canonical."""
        check_values = tuple(code.value for code in self.check_codes)
        if check_values != tuple(sorted(set(check_values))):
            raise ValueError("Expected check codes must be unique and sorted.")
        if self.values != tuple(sorted(set(self.values))):
            raise ValueError("Expected values must be unique and sorted.")
        return self


class _EvalCaseBase(ContractModel):
    case_id: CaseId
    label: CaseLabel
    tags: Annotated[
        tuple[CanonicalTag, ...],
        Field(min_length=1, max_length=MAX_TAGS),
    ]
    expected: EvalExpected

    @model_validator(mode="after")
    def validate_case_metadata(self) -> _EvalCaseBase:
        if not _CASE_ID_PATTERN.fullmatch(self.case_id):
            raise ValueError("Case ID is not canonical.")
        if self.tags != tuple(sorted(set(self.tags))):
            raise ValueError("Case tags must be unique and sorted.")
        if any(not _TAG_PATTERN.fullmatch(tag) for tag in self.tags):
            raise ValueError("Case tag is not canonical.")
        return self


class RouterEvalCase(_EvalCaseBase):
    target: Literal[AgentEvalTarget.ROUTER]
    scenario: RouterScenario
    expected_intent: IntentKind
    expected_plan: tuple[SpecialistKind, ...] = ()
    expected_city: SupportedCity | None = None


class DiscoveryEvalCase(_EvalCaseBase):
    target: Literal[AgentEvalTarget.DISCOVERY]
    scenario: DiscoveryScenario
    expected_completeness: DiscoveryCompleteness | None = None
    expected_candidate_ids: tuple[str, ...] = ()
    expected_failure: FailureCode | None = None


class NarrationEvalCase(_EvalCaseBase):
    target: Literal[AgentEvalTarget.NARRATION]
    scenario: NarrationScenario
    expected_status: AnswerStatus
    expected_word_count: Annotated[
        StrictInt,
        Field(ge=0, le=200),
    ] = 0


class LocalCultureEvalCase(_EvalCaseBase):
    target: Literal[AgentEvalTarget.LOCAL_CULTURE]
    scenario: LocalCultureScenario
    expected_status: AnswerStatus
    expected_guidance_count: Annotated[
        StrictInt,
        Field(ge=0, le=12),
    ] = 0


class ItineraryEvalCase(_EvalCaseBase):
    target: Literal[AgentEvalTarget.ITINERARY]
    scenario: ItineraryScenario
    expected_poi_ids: tuple[str, ...] = ()
    expected_failure: ItineraryFailureReason | None = None


class GroundingEvalCase(_EvalCaseBase):
    target: Literal[AgentEvalTarget.GROUNDING_REVIEWER]
    scenario: GroundingScenario
    expected_status: GroundingReviewStatus
    expected_approved_claim_ids: tuple[str, ...] = ()


class ComposerEvalCase(_EvalCaseBase):
    target: Literal[AgentEvalTarget.RESPONSE_COMPOSER]
    scenario: ComposerScenario
    expected_poi_ids: tuple[str, ...] = ()
    expected_warning_count: Annotated[
        StrictInt,
        Field(ge=0, le=20),
    ] = 0


class RuntimeEvalCase(_EvalCaseBase):
    target: Literal[AgentEvalTarget.RUNTIME]
    scenario: RuntimeScenario
    expected_status: RuntimeResultStatus
    expected_failure: FailureCode | None = None


AgentEvalCase = Annotated[
    RouterEvalCase
    | DiscoveryEvalCase
    | NarrationEvalCase
    | LocalCultureEvalCase
    | ItineraryEvalCase
    | GroundingEvalCase
    | ComposerEvalCase
    | RuntimeEvalCase,
    Field(discriminator="target"),
]


class AgentEvalFixtureSet(ContractModel):
    """One versioned, canonically ordered fixture collection."""

    schema_version: Literal[1]
    cases: Annotated[
        tuple[AgentEvalCase, ...],
        Field(min_length=1, max_length=MAX_EVAL_CASES),
    ]

    @model_validator(mode="after")
    def validate_cases(self) -> AgentEvalFixtureSet:
        case_ids = tuple(case.case_id for case in self.cases)
        if case_ids != tuple(sorted(set(case_ids))):
            raise ValueError("Eval case IDs must be unique and sorted.")
        return self


class AgentEvalThresholds(ContractModel):
    """Committed regression policy; threshold changes require review."""

    schema_version: Literal[1]
    minimum_total_cases: Annotated[
        StrictInt,
        Field(ge=41, le=MAX_EVAL_CASES),
    ]
    minimum_cases_by_target: tuple[tuple[AgentEvalTarget, StrictInt], ...]
    minimum_overall_pass_rate_basis_points: BasisPoints
    minimum_target_pass_rate_basis_points: tuple[
        tuple[AgentEvalTarget, BasisPoints], ...
    ]
    require_no_failed_cases: StrictBool
    required_targets: tuple[AgentEvalTarget, ...]
    required_tags: tuple[CanonicalTag, ...]
    required_check_codes: tuple[EvalCheckCode, ...]

    @model_validator(mode="after")
    def validate_policy(self) -> AgentEvalThresholds:
        count_targets = tuple(target for target, _ in self.minimum_cases_by_target)
        rate_targets = tuple(
            target
            for target, _ in self.minimum_target_pass_rate_basis_points
        )
        if count_targets != TARGET_ORDER or rate_targets != TARGET_ORDER:
            raise ValueError("Threshold target entries must be complete and ordered.")
        if self.required_targets != TARGET_ORDER:
            raise ValueError("Required targets must be complete and ordered.")
        if any(count < 1 for _, count in self.minimum_cases_by_target):
            raise ValueError("Target minimums must be positive.")
        if self.required_tags != tuple(sorted(set(self.required_tags))):
            raise ValueError("Required tags must be unique and sorted.")
        check_values = tuple(code.value for code in self.required_check_codes)
        if check_values != tuple(sorted(set(check_values))):
            raise ValueError("Required check codes must be unique and sorted.")
        return self


class AgentEvalCaseResult(ContractModel):
    """Privacy-safe result metadata for one labeled case."""

    case_id: CaseId
    target: AgentEvalTarget
    passed: StrictBool
    passed_check_codes: tuple[EvalCheckCode, ...]
    failed_check_codes: tuple[EvalCheckCode, ...]

    @model_validator(mode="after")
    def validate_result(self) -> AgentEvalCaseResult:
        passed_values = tuple(code.value for code in self.passed_check_codes)
        failed_values = tuple(code.value for code in self.failed_check_codes)
        if passed_values != tuple(sorted(set(passed_values))):
            raise ValueError("Passed checks must be unique and sorted.")
        if failed_values != tuple(sorted(set(failed_values))):
            raise ValueError("Failed checks must be unique and sorted.")
        if set(self.passed_check_codes) & set(self.failed_check_codes):
            raise ValueError("Passed and failed checks must be disjoint.")
        if self.passed is bool(self.failed_check_codes):
            raise ValueError("Case pass flag differs from failed checks.")
        return self


class AgentEvalTargetMetrics(ContractModel):
    target: AgentEvalTarget
    total: BoundedCount
    passed: BoundedCount
    failed: BoundedCount
    pass_rate_basis_points: BasisPoints

    @model_validator(mode="after")
    def validate_counts(self) -> AgentEvalTargetMetrics:
        if self.passed + self.failed != self.total:
            raise ValueError("Target counts do not add up.")
        if self.total == 0:
            raise ValueError("Target metric denominator must be nonzero.")
        return self


class AgentEvalCheckMetrics(ContractModel):
    check_code: EvalCheckCode
    total: BoundedCount
    passed: BoundedCount
    failed: BoundedCount
    pass_rate_basis_points: BasisPoints

    @model_validator(mode="after")
    def validate_counts(self) -> AgentEvalCheckMetrics:
        if self.passed + self.failed != self.total:
            raise ValueError("Check counts do not add up.")
        if self.total == 0:
            raise ValueError("Check metric denominator must be nonzero.")
        return self


class FailedCase(ContractModel):
    case_id: CaseId
    failed_check_codes: Annotated[
        tuple[EvalCheckCode, ...],
        Field(min_length=1, max_length=MAX_CHECKS),
    ]


class AgentEvalThresholdStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class AgentEvalThresholdResult(ContractModel):
    status: AgentEvalThresholdStatus
    failed_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_status(self) -> AgentEvalThresholdResult:
        if self.failed_codes != tuple(sorted(set(self.failed_codes))):
            raise ValueError("Threshold failure codes must be unique and sorted.")
        if self.status is AgentEvalThresholdStatus.PASS and self.failed_codes:
            raise ValueError("Passing thresholds cannot contain failures.")
        if self.status is AgentEvalThresholdStatus.FAIL and not self.failed_codes:
            raise ValueError("Failing thresholds require stable failure codes.")
        return self


class AgentEvalReport(ContractModel):
    """Canonical safe report with no case inputs, outputs, or timestamps."""

    report_schema_version: Literal[1]
    fixture_schema_version: Literal[1]
    total_cases: BoundedCount
    passed_cases: BoundedCount
    failed_cases: BoundedCount
    overall_pass_rate_basis_points: BasisPoints
    target_metrics: tuple[AgentEvalTargetMetrics, ...]
    check_metrics: tuple[AgentEvalCheckMetrics, ...]
    case_results: tuple[AgentEvalCaseResult, ...]
    failed_case_details: tuple[FailedCase, ...]
    threshold_result: AgentEvalThresholdResult

    @model_validator(mode="after")
    def validate_report(self) -> AgentEvalReport:
        if self.total_cases == 0:
            raise ValueError("Report requires at least one case.")
        if self.passed_cases + self.failed_cases != self.total_cases:
            raise ValueError("Overall counts do not add up.")
        if sum(metric.total for metric in self.target_metrics) != self.total_cases:
            raise ValueError("Target totals differ from overall total.")
        if tuple(metric.target for metric in self.target_metrics) != TARGET_ORDER:
            raise ValueError("Target metrics are not canonical.")
        check_values = tuple(metric.check_code.value for metric in self.check_metrics)
        if check_values != tuple(sorted(set(check_values))):
            raise ValueError("Check metrics are not canonical.")
        case_ids = tuple(result.case_id for result in self.case_results)
        if case_ids != tuple(sorted(set(case_ids))):
            raise ValueError("Case results are not canonical.")
        failed_ids = tuple(item.case_id for item in self.failed_case_details)
        if failed_ids != tuple(sorted(set(failed_ids))):
            raise ValueError("Failed case details are not canonical.")
        return self
