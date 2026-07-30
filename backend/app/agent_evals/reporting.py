"""Canonical JSON/Markdown rendering and atomic report persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from app.agent_evals.contracts import AgentEvalReport
from app.agent_evals.fixtures import BACKEND_ROOT


class EvalReportError(Exception):
    """Sanitized report comparison or persistence failure."""

    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def render_json(report: AgentEvalReport) -> bytes:
    """Render canonical UTF-8 JSON with Unicode and a terminal newline."""
    text = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    return f"{text}\n".encode()


def render_markdown(report: AgentEvalReport) -> bytes:
    """Render deterministic safe aggregate and case metadata."""
    lines = [
        "# Offline Agent Evaluation Report",
        "",
        f"Fixture schema version: {report.fixture_schema_version}",
        "",
        f"Threshold status: {report.threshold_result.status.value}",
        "",
        (
            f"Overall: {report.passed_cases}/{report.total_cases} passed; "
            f"{report.failed_cases} failed; "
            f"{report.overall_pass_rate_basis_points} basis points."
        ),
        "",
        (
            "The default suite is deterministic, offline, credential-free, "
            "and performs no real model request."
        ),
        "",
        "## Per-target metrics",
        "",
        "| Target | Total | Passed | Failed | Pass rate (bp) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        (
            f"| {metric.target.value} | {metric.total} | {metric.passed} | "
            f"{metric.failed} | {metric.pass_rate_basis_points} |"
        )
        for metric in report.target_metrics
    )
    lines.extend(
        [
            "",
            "## Per-check metrics",
            "",
            "| Check | Total | Passed | Failed | Pass rate (bp) |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(
        (
            f"| {metric.check_code.value} | {metric.total} | {metric.passed} | "
            f"{metric.failed} | {metric.pass_rate_basis_points} |"
        )
        for metric in report.check_metrics
    )
    lines.extend(
        [
            "",
            "## Case results",
            "",
            "| Case ID | Target | Status | Passed checks | Failed checks |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        (
            f"| {result.case_id} | {result.target.value} | "
            f"{'pass' if result.passed else 'fail'} | "
            f"{', '.join(code.value for code in result.passed_check_codes) or '-'} "
            f"| {', '.join(code.value for code in result.failed_check_codes) or '-'} |"
        )
        for result in report.case_results
    )
    if report.failed_case_details:
        lines.extend(
            [
                "",
                "## Failed cases",
                "",
                "| Case ID | Failed checks |",
                "| --- | --- |",
            ]
        )
        lines.extend(
            (
                f"| {item.case_id} | "
                f"{', '.join(code.value for code in item.failed_check_codes)} |"
            )
            for item in report.failed_case_details
        )
    return ("\n".join(lines) + "\n").encode()


def write_reports_atomic(
    *,
    json_path: Path,
    markdown_path: Path,
    json_bytes: bytes,
    markdown_bytes: bytes,
) -> None:
    """Write both repository-owned reports through same-directory temp files."""
    _require_repository_path(json_path)
    _require_repository_path(markdown_path)
    _atomic_write(json_path, json_bytes)
    _atomic_write(markdown_path, markdown_bytes)


def reports_match(
    *,
    json_path: Path,
    markdown_path: Path,
    json_bytes: bytes,
    markdown_bytes: bytes,
) -> bool:
    """Compare committed reports byte-for-byte without changing files."""
    try:
        return (
            json_path.read_bytes() == json_bytes
            and markdown_path.read_bytes() == markdown_bytes
        )
    except OSError:
        return False


def _require_repository_path(path: Path) -> None:
    try:
        path.resolve().relative_to(BACKEND_ROOT.resolve())
    except ValueError:
        raise EvalReportError("unsafe_report_path") from None


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(raw_path)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        temporary = None
    except OSError:
        raise EvalReportError("report_write_failed") from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
