"""Sanitized non-interactive CLI for offline agent evaluation baselines."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Sequence

from app.agent_evals.contracts import AgentEvalThresholdStatus
from app.agent_evals.fixtures import (
    DEFAULT_FIXTURE_PATH,
    DEFAULT_JSON_REPORT_PATH,
    DEFAULT_MARKDOWN_REPORT_PATH,
    DEFAULT_THRESHOLD_PATH,
    EvalDataError,
    load_fixture_set,
    load_thresholds,
)
from app.agent_evals.reporting import (
    EvalReportError,
    render_json,
    render_markdown,
    reports_match,
    write_reports_atomic,
)
from app.agent_evals.runner import run_evaluations


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.agent_evals",
        description="Offline deterministic agent evaluation baseline.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("write", "check"):
        command = commands.add_parser(name)
        command.add_argument(
            "--fixtures",
            type=Path,
            default=DEFAULT_FIXTURE_PATH,
        )
        command.add_argument(
            "--thresholds",
            type=Path,
            default=DEFAULT_THRESHOLD_PATH,
        )
        command.add_argument(
            "--json-report",
            type=Path,
            default=DEFAULT_JSON_REPORT_PATH,
        )
        command.add_argument(
            "--markdown-report",
            type=Path,
            default=DEFAULT_MARKDOWN_REPORT_PATH,
        )
    return parser


def _relative_label(path: Path) -> str:
    if path == DEFAULT_JSON_REPORT_PATH:
        return "evals/reports/agent-evals-v1.json"
    if path == DEFAULT_MARKDOWN_REPORT_PATH:
        return "evals/reports/agent-evals-v1.md"
    return path.name


def _summary(
    *,
    command: str,
    total: int,
    passed: int,
    failed: int,
    threshold: str,
    json_path: Path,
    markdown_path: Path,
    failure_code: str = "none",
) -> None:
    print(
        f"command={command} fixtures={total} passed={passed} failed={failed} "
        f"threshold={threshold} "
        f"json_report={_relative_label(json_path)} "
        f"markdown_report={_relative_label(markdown_path)} "
        f"failure_code={failure_code}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run one deterministic command and return a controlled exit code."""
    arguments = _parser().parse_args(argv)
    command = str(arguments.command)
    json_path = cast_path(arguments.json_report)
    markdown_path = cast_path(arguments.markdown_report)
    try:
        fixtures = load_fixture_set(cast_path(arguments.fixtures))
        thresholds = load_thresholds(cast_path(arguments.thresholds))
        report = asyncio.run(run_evaluations(fixtures, thresholds))
        json_bytes = render_json(report)
        markdown_bytes = render_markdown(report)
        failure_code = "none"
        if report.failed_cases:
            failure_code = "case_regression"
        elif report.threshold_result.status is AgentEvalThresholdStatus.FAIL:
            failure_code = "threshold_regression"
        elif command == "check" and not reports_match(
            json_path=json_path,
            markdown_path=markdown_path,
            json_bytes=json_bytes,
            markdown_bytes=markdown_bytes,
        ):
            failure_code = "report_regression"
        if command == "write":
            write_reports_atomic(
                json_path=json_path,
                markdown_path=markdown_path,
                json_bytes=json_bytes,
                markdown_bytes=markdown_bytes,
            )
        _summary(
            command=command,
            total=report.total_cases,
            passed=report.passed_cases,
            failed=report.failed_cases,
            threshold=report.threshold_result.status.value,
            json_path=json_path,
            markdown_path=markdown_path,
            failure_code=failure_code,
        )
        return 0 if failure_code == "none" else 1
    except KeyboardInterrupt:
        code = "cancelled"
    except asyncio.CancelledError:
        code = "cancelled"
    except EvalDataError as error:
        code = error.code
    except EvalReportError as error:
        code = error.code
    except Exception:
        code = "evaluation_failed"
    _summary(
        command=command,
        total=0,
        passed=0,
        failed=0,
        threshold="fail",
        json_path=json_path,
        markdown_path=markdown_path,
        failure_code=code,
    )
    return 2


def cast_path(value: object) -> Path:
    if not isinstance(value, Path):
        raise TypeError("Expected parsed path.")
    return value
