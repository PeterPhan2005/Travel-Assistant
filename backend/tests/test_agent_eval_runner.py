"""Contracts, execution, reporting, CLI, and regression tests for T050."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from collections.abc import Coroutine
from pathlib import Path
from typing import NoReturn

import pytest
from pydantic import ValidationError

from app.agent_evals.cli import main
from app.agent_evals.contracts import (
    TARGET_ORDER,
    AgentEvalCaseResult,
    AgentEvalFixtureSet,
    AgentEvalReport,
    AgentEvalThresholdStatus,
    AgentEvalThresholds,
    EvalCheckCode,
)
from app.agent_evals.fixtures import (
    DEFAULT_FIXTURE_PATH,
    DEFAULT_JSON_REPORT_PATH,
    DEFAULT_MARKDOWN_REPORT_PATH,
    DEFAULT_THRESHOLD_PATH,
    EvalDataError,
    load_fixture_set,
    load_thresholds,
)
from app.agent_evals.metrics import basis_points, build_report
from app.agent_evals.reporting import (
    render_json,
    render_markdown,
    reports_match,
    write_reports_atomic,
)
from app.agent_evals.runner import run_evaluations

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def _report() -> AgentEvalReport:
    return asyncio.run(
        run_evaluations(load_fixture_set(), load_thresholds())
    )


def test_fixture_distribution_and_required_coverage() -> None:
    fixtures = load_fixture_set()
    counts = Counter(case.target for case in fixtures.cases)

    assert len(fixtures.cases) == 43
    assert counts[TARGET_ORDER[0]] == 6
    assert counts[TARGET_ORDER[-1]] == 7
    assert all(counts[target] >= 5 for target in TARGET_ORDER[1:-1])
    assert {target for target in TARGET_ORDER} == set(counts)
    tags = {tag for case in fixtures.cases for tag in case.tags}
    assert {"closure", "deterministic", "privacy", "safety"} <= tags


def test_contracts_are_strict_frozen_extra_forbidden_and_schemas_generate() -> None:
    fixtures = load_fixture_set()
    thresholds = load_thresholds()
    report = _report()

    for model in (fixtures, thresholds, report):
        assert model.model_config["extra"] == "forbid"
        assert model.model_config["frozen"] is True
        assert model.model_config["strict"] is True
        with pytest.raises(ValidationError):
            type(model).model_validate(
                {**model.model_dump(mode="python"), "unknown": "field"}
            )
    assert AgentEvalFixtureSet.model_json_schema()
    assert AgentEvalThresholds.model_json_schema()
    assert AgentEvalReport.model_json_schema()


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        (lambda value: value.update({"schema_version": 2}), "fixture_invalid"),
        (
            lambda value: value["cases"][0].update({"target": "unknown"}),
            "fixture_invalid",
        ),
        (
            lambda value: value["cases"][0]["expected"]["check_codes"].append(
                "unknown_check"
            ),
            "fixture_invalid",
        ),
        (
            lambda value: value["cases"][0]["tags"].append(
                value["cases"][0]["tags"][0]
            ),
            "fixture_invalid",
        ),
        (
            lambda value: value["cases"].insert(0, value["cases"][1]),
            "fixture_invalid",
        ),
    ],
)
def test_malformed_fixtures_fail_with_one_stable_code(
    tmp_path: Path,
    mutation: object,
    error_code: str,
) -> None:
    value = json.loads(DEFAULT_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert callable(mutation)
    mutation(value)
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(EvalDataError) as captured:
        load_fixture_set(path)

    assert captured.value.code == error_code
    assert str(captured.value) == error_code


def test_all_committed_cases_pass_with_exact_integer_metrics() -> None:
    report = _report()

    assert report.total_cases == 43
    assert report.passed_cases == 43
    assert report.failed_cases == 0
    assert report.overall_pass_rate_basis_points == 10_000
    assert report.threshold_result.status is AgentEvalThresholdStatus.PASS
    assert report.threshold_result.failed_codes == ()
    assert sum(metric.total for metric in report.target_metrics) == 43
    assert all(
        metric.pass_rate_basis_points == 10_000
        for metric in report.target_metrics
    )
    assert all(
        metric.pass_rate_basis_points == 10_000
        for metric in report.check_metrics
    )
    assert all(result.passed for result in report.case_results)
    assert all(
        EvalCheckCode.DETERMINISTIC_REPEAT in result.passed_check_codes
        for result in report.case_results
    )


def test_basis_points_rejects_empty_or_invalid_denominator() -> None:
    assert basis_points(1, 3) == 3_333
    with pytest.raises(ValueError):
        basis_points(0, 0)
    with pytest.raises(ValueError):
        basis_points(2, 1)


def test_threshold_regression_fails_closed() -> None:
    fixtures = load_fixture_set()
    thresholds = load_thresholds().model_copy(
        update={"minimum_total_cases": 44}
    )
    passing = _report()
    regressed = build_report(
        fixtures,
        passing.case_results,
        thresholds,
    )

    assert regressed.threshold_result.status is AgentEvalThresholdStatus.FAIL
    assert regressed.threshold_result.failed_codes == (
        "minimum_total_cases",
    )


def test_failed_case_and_missing_target_reject_baseline() -> None:
    fixtures = load_fixture_set()
    thresholds = load_thresholds()
    passing = _report()
    first = passing.case_results[0]
    regressed_first = AgentEvalCaseResult(
        case_id=first.case_id,
        target=first.target,
        passed=False,
        passed_check_codes=tuple(
            code
            for code in first.passed_check_codes
            if code is not EvalCheckCode.CONTRACT_VALID
        ),
        failed_check_codes=(EvalCheckCode.CONTRACT_VALID,),
    )
    regressed = build_report(
        fixtures,
        (regressed_first, *passing.case_results[1:]),
        thresholds,
    )

    assert regressed.threshold_result.status is AgentEvalThresholdStatus.FAIL
    assert "failed_cases_present" in regressed.threshold_result.failed_codes
    assert "minimum_overall_pass_rate" in (
        regressed.threshold_result.failed_codes
    )

    without_runtime = AgentEvalFixtureSet(
        schema_version=1,
        cases=tuple(
            case
            for case in fixtures.cases
            if case.target is not TARGET_ORDER[-1]
        ),
    )
    without_runtime_results = tuple(
        result
        for result in passing.case_results
        if result.target is not TARGET_ORDER[-1]
    )
    with pytest.raises(ValueError):
        build_report(
            without_runtime,
            without_runtime_results,
            thresholds,
        )


def test_fixture_file_is_synthetic_and_contains_no_credential_shape() -> None:
    text = DEFAULT_FIXTURE_PATH.read_text(encoding="utf-8").casefold()

    for forbidden in (
        "api_key",
        "authorization",
        "bearer ",
        "firebase",
        "password",
        "postgresql://",
        "/users/",
    ):
        assert forbidden not in text
    assert "latitude" not in text
    assert "longitude" not in text


def test_reports_are_byte_deterministic_unicode_safe_and_current() -> None:
    first = _report()
    second = _report()
    first_json = render_json(first)
    first_markdown = render_markdown(first)

    assert first == second
    assert first_json == render_json(second)
    assert first_markdown == render_markdown(second)
    assert first_json.endswith(b"\n")
    assert first_markdown.endswith(b"\n")
    assert b"credential-free" in first_markdown
    assert "threshold_result" in first_json.decode()
    assert "generation_timestamp" not in first_json.decode()
    assert str(ROOT) not in first_json.decode()
    assert str(ROOT) not in first_markdown.decode()
    for forbidden in (
        "user_query",
        "latitude",
        "longitude",
        "final_text",
        "api_key",
        "trace_id",
    ):
        assert forbidden not in first_json.decode().casefold()
        assert forbidden not in first_markdown.decode().casefold()
    assert DEFAULT_JSON_REPORT_PATH.read_bytes() == first_json
    assert DEFAULT_MARKDOWN_REPORT_PATH.read_bytes() == first_markdown


def test_atomic_writer_and_comparison_leave_no_temp_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agent_evals import reporting

    report = _report()
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    monkeypatch.setattr(reporting, "BACKEND_ROOT", tmp_path)

    write_reports_atomic(
        json_path=json_path,
        markdown_path=markdown_path,
        json_bytes=render_json(report),
        markdown_bytes=render_markdown(report),
    )

    assert reports_match(
        json_path=json_path,
        markdown_path=markdown_path,
        json_bytes=render_json(report),
        markdown_bytes=render_markdown(report),
    )
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_cli_check_succeeds_and_makes_no_changes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before_json = DEFAULT_JSON_REPORT_PATH.read_bytes()
    before_markdown = DEFAULT_MARKDOWN_REPORT_PATH.read_bytes()

    result = main(["check"])

    assert result == 0
    assert DEFAULT_JSON_REPORT_PATH.read_bytes() == before_json
    assert DEFAULT_MARKDOWN_REPORT_PATH.read_bytes() == before_markdown
    output = capsys.readouterr()
    assert output.err == ""
    assert "fixtures=43 passed=43 failed=0 threshold=pass" in output.out
    assert "failure_code=none" in output.out


def test_cli_detects_report_and_threshold_regression_safely(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    edited_report = tmp_path / "edited.json"
    edited_markdown = tmp_path / "edited.md"
    edited_report.write_bytes(DEFAULT_JSON_REPORT_PATH.read_bytes() + b" ")
    edited_markdown.write_bytes(DEFAULT_MARKDOWN_REPORT_PATH.read_bytes())

    report_exit = main(
        [
            "check",
            "--json-report",
            str(edited_report),
            "--markdown-report",
            str(edited_markdown),
        ]
    )
    report_output = capsys.readouterr()
    assert report_exit == 1
    assert "failure_code=report_regression" in report_output.out
    assert report_output.err == ""

    threshold_value = json.loads(
        DEFAULT_THRESHOLD_PATH.read_text(encoding="utf-8")
    )
    threshold_value["minimum_total_cases"] = 44
    threshold_path = tmp_path / "thresholds.json"
    threshold_path.write_text(
        json.dumps(threshold_value),
        encoding="utf-8",
    )
    threshold_exit = main(
        ["check", "--thresholds", str(threshold_path)]
    )
    threshold_output = capsys.readouterr()
    assert threshold_exit == 1
    assert "failure_code=threshold_regression" in threshold_output.out
    assert threshold_output.err == ""


def test_cli_fixture_failure_and_keyboard_interrupt_are_sanitized(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")

    assert main(["check", "--fixtures", str(malformed)]) == 2
    malformed_output = capsys.readouterr()
    assert "failure_code=fixture_invalid" in malformed_output.out
    assert malformed_output.err == ""

    def interrupt(
        awaitable: Coroutine[object, object, AgentEvalReport],
    ) -> NoReturn:
        awaitable.close()
        raise KeyboardInterrupt

    monkeypatch.setattr("app.agent_evals.cli.asyncio.run", interrupt)
    assert main(["check"]) == 2
    interrupted_output = capsys.readouterr()
    assert "failure_code=cancelled" in interrupted_output.out
    assert interrupted_output.err == ""


def test_default_execution_ignores_model_and_service_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_ROUTER_MODEL",
        "OPENAI_DISCOVERY_MODEL",
        "OPENAI_NARRATION_MODEL",
        "OPENAI_LOCAL_CULTURE_MODEL",
        "OPENAI_ITINERARY_MODEL",
        "OPENAI_GROUNDING_MODEL",
        "OPENAI_COMPOSER_MODEL",
        "DATABASE_URL",
        "FIREBASE_PROJECT_ID",
    ):
        monkeypatch.setenv(name, "must-not-be-read")

    report = _report()

    assert report.failed_cases == 0
    assert report.threshold_result.status is AgentEvalThresholdStatus.PASS
