"""Deterministic integer metrics and committed-threshold evaluation."""

from __future__ import annotations

from collections import Counter

from app.agent_evals.contracts import (
    TARGET_ORDER,
    AgentEvalCaseResult,
    AgentEvalCheckMetrics,
    AgentEvalFixtureSet,
    AgentEvalReport,
    AgentEvalTarget,
    AgentEvalTargetMetrics,
    AgentEvalThresholdResult,
    AgentEvalThresholdStatus,
    AgentEvalThresholds,
    EvalCheckCode,
    FailedCase,
)


def basis_points(passed: int, total: int) -> int:
    """Calculate stable rounded-down integer basis points."""
    if total <= 0:
        raise ValueError("Metric denominator must be positive.")
    if passed < 0 or passed > total:
        raise ValueError("Metric numerator is invalid.")
    return passed * 10_000 // total


def build_report(
    fixtures: AgentEvalFixtureSet,
    results: tuple[AgentEvalCaseResult, ...],
    thresholds: AgentEvalThresholds,
) -> AgentEvalReport:
    """Aggregate canonical metrics and apply the committed policy."""
    if len(results) != len(fixtures.cases):
        raise ValueError("Result count differs from fixture count.")
    if tuple(result.case_id for result in results) != tuple(
        case.case_id for case in fixtures.cases
    ):
        raise ValueError("Result identities differ from fixtures.")

    target_metrics = tuple(
        _target_metrics(target, results) for target in TARGET_ORDER
    )
    represented_checks = tuple(
        sorted(
            {
                code
                for result in results
                for code in (
                    *result.passed_check_codes,
                    *result.failed_check_codes,
                )
            },
            key=lambda code: code.value,
        )
    )
    check_metrics = tuple(
        _check_metrics(code, results) for code in represented_checks
    )
    passed_cases = sum(result.passed for result in results)
    failed_case_details = tuple(
        FailedCase(
            case_id=result.case_id,
            failed_check_codes=result.failed_check_codes,
        )
        for result in results
        if not result.passed
    )
    threshold_result = evaluate_thresholds(
        fixtures=fixtures,
        results=results,
        thresholds=thresholds,
        target_metrics=target_metrics,
        overall_pass_rate_basis_points=basis_points(
            passed_cases,
            len(results),
        ),
    )
    return AgentEvalReport(
        report_schema_version=1,
        fixture_schema_version=fixtures.schema_version,
        total_cases=len(results),
        passed_cases=passed_cases,
        failed_cases=len(results) - passed_cases,
        overall_pass_rate_basis_points=basis_points(
            passed_cases,
            len(results),
        ),
        target_metrics=target_metrics,
        check_metrics=check_metrics,
        case_results=results,
        failed_case_details=failed_case_details,
        threshold_result=threshold_result,
    )


def _target_metrics(
    target: AgentEvalTarget,
    results: tuple[AgentEvalCaseResult, ...],
) -> AgentEvalTargetMetrics:
    selected = tuple(result for result in results if result.target is target)
    passed = sum(result.passed for result in selected)
    return AgentEvalTargetMetrics(
        target=target,
        total=len(selected),
        passed=passed,
        failed=len(selected) - passed,
        pass_rate_basis_points=basis_points(passed, len(selected)),
    )


def _check_metrics(
    code: EvalCheckCode,
    results: tuple[AgentEvalCaseResult, ...],
) -> AgentEvalCheckMetrics:
    selected = tuple(
        result
        for result in results
        if code in result.passed_check_codes
        or code in result.failed_check_codes
    )
    passed = sum(code in result.passed_check_codes for result in selected)
    return AgentEvalCheckMetrics(
        check_code=code,
        total=len(selected),
        passed=passed,
        failed=len(selected) - passed,
        pass_rate_basis_points=basis_points(passed, len(selected)),
    )


def evaluate_thresholds(
    *,
    fixtures: AgentEvalFixtureSet,
    results: tuple[AgentEvalCaseResult, ...],
    thresholds: AgentEvalThresholds,
    target_metrics: tuple[AgentEvalTargetMetrics, ...],
    overall_pass_rate_basis_points: int,
) -> AgentEvalThresholdResult:
    """Return only stable policy failure codes."""
    failures: set[str] = set()
    if len(fixtures.cases) < thresholds.minimum_total_cases:
        failures.add("minimum_total_cases")
    target_counts = Counter(case.target for case in fixtures.cases)
    for target, minimum in thresholds.minimum_cases_by_target:
        if target_counts[target] < minimum:
            failures.add(f"minimum_cases:{target.value}")
    if (
        overall_pass_rate_basis_points
        < thresholds.minimum_overall_pass_rate_basis_points
    ):
        failures.add("minimum_overall_pass_rate")
    minimum_rates = dict(thresholds.minimum_target_pass_rate_basis_points)
    for metric in target_metrics:
        if metric.pass_rate_basis_points < minimum_rates[metric.target]:
            failures.add(f"minimum_target_pass_rate:{metric.target.value}")
    if thresholds.require_no_failed_cases and any(
        not result.passed for result in results
    ):
        failures.add("failed_cases_present")
    present_targets = set(target_counts)
    for target in thresholds.required_targets:
        if target not in present_targets:
            failures.add(f"required_target:{target.value}")
    present_tags = {
        tag for case in fixtures.cases for tag in case.tags
    }
    for tag in thresholds.required_tags:
        if tag not in present_tags:
            failures.add(f"required_tag:{tag}")
    present_checks = {
        code for case in fixtures.cases for code in case.expected.check_codes
    }
    for code in thresholds.required_check_codes:
        if code not in present_checks:
            failures.add(f"required_check:{code.value}")
    ordered = tuple(sorted(failures))
    return AgentEvalThresholdResult(
        status=(
            AgentEvalThresholdStatus.FAIL
            if ordered
            else AgentEvalThresholdStatus.PASS
        ),
        failed_codes=ordered,
    )
