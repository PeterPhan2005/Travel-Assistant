"""Strict JSON loading and repository-owned path definitions."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from app.agent_evals.contracts import AgentEvalFixtureSet, AgentEvalThresholds

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_PATH = (
    BACKEND_ROOT / "evals" / "fixtures" / "agent-evals-v1.json"
)
DEFAULT_THRESHOLD_PATH = (
    BACKEND_ROOT / "evals" / "thresholds" / "agent-evals-v1.json"
)
DEFAULT_JSON_REPORT_PATH = (
    BACKEND_ROOT / "evals" / "reports" / "agent-evals-v1.json"
)
DEFAULT_MARKDOWN_REPORT_PATH = (
    BACKEND_ROOT / "evals" / "reports" / "agent-evals-v1.md"
)


class EvalDataError(Exception):
    """Sanitized fixture or threshold loading failure."""

    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _load_json_bytes(path: Path, *, failure_code: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        raise EvalDataError(failure_code) from None


def load_fixture_set(path: Path = DEFAULT_FIXTURE_PATH) -> AgentEvalFixtureSet:
    """Load one strict fixture set without exposing validation details."""
    try:
        return AgentEvalFixtureSet.model_validate_json(
            _load_json_bytes(path, failure_code="fixture_load_failed")
        )
    except (UnicodeError, ValueError, ValidationError):
        raise EvalDataError("fixture_invalid") from None


def load_thresholds(
    path: Path = DEFAULT_THRESHOLD_PATH,
) -> AgentEvalThresholds:
    """Load one strict committed threshold policy."""
    try:
        return AgentEvalThresholds.model_validate_json(
            _load_json_bytes(path, failure_code="threshold_load_failed")
        )
    except (UnicodeError, ValueError, ValidationError):
        raise EvalDataError("threshold_invalid") from None
