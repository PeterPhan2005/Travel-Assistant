"""Credential-free deterministic execution of labeled evaluation cases."""

from __future__ import annotations

import asyncio

from app.agent_evals.contracts import (
    AgentEvalCase,
    AgentEvalCaseResult,
    AgentEvalFixtureSet,
    AgentEvalReport,
    AgentEvalThresholds,
    EvalCheckCode,
)
from app.agent_evals.metrics import build_report
from app.agent_evals.scenarios import execute_case


async def run_evaluations(
    fixtures: AgentEvalFixtureSet,
    thresholds: AgentEvalThresholds,
) -> AgentEvalReport:
    """Execute every case and repeat all determinism-tagged cases."""
    results: list[AgentEvalCaseResult] = []
    for case in fixtures.cases:
        results.append(await _run_case(case))
    return build_report(fixtures, tuple(results), thresholds)


async def _run_case(case: AgentEvalCase) -> AgentEvalCaseResult:
    requested = set(case.expected.check_codes)
    try:
        first = await execute_case(case)
        passed = set(first.passed_checks)
        if "deterministic" in case.tags:
            second = await execute_case(case)
            if first.canonical_output == second.canonical_output:
                passed.add(EvalCheckCode.DETERMINISTIC_REPEAT)
        passed_requested = tuple(
            sorted(requested & passed, key=lambda code: code.value)
        )
        failed_requested = tuple(
            sorted(requested - passed, key=lambda code: code.value)
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        passed_requested = ()
        failed_requested = tuple(
            sorted(requested, key=lambda code: code.value)
        )
    return AgentEvalCaseResult(
        case_id=case.case_id,
        target=case.target,
        passed=not failed_requested,
        passed_check_codes=passed_requested,
        failed_check_codes=failed_requested,
    )
