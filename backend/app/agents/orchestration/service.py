"""Strict application-code coordination across isolated typed services."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Protocol

from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    AgentRuntimeRequest,
    AgentRuntimeResult,
    AgentWarning,
    AnswerStatus,
    ComposerStageOutcome,
    DiscoveryCompleteness,
    DiscoveryOutput,
    DiscoveryRequest,
    DiscoverySpecialistOutput,
    DiscoveryStageOutcome,
    EvidenceBundle,
    FailureCode,
    GroundingReviewOutput,
    GroundingReviewRequest,
    GroundingReviewStatus,
    GroundingStageOutcome,
    IntentKind,
    ItineraryOutput,
    ItineraryRequest,
    ItinerarySpecialistOutput,
    ItineraryStageOutcome,
    LocalCultureOutput,
    LocalCultureRequest,
    LocalCultureSpecialistOutput,
    LocalCultureStageOutcome,
    NarrationOutput,
    NarrationRequest,
    NarrationSpecialistOutput,
    NarrationStageOutcome,
    ResponseComposerOutput,
    ResponseComposerRequest,
    RouterOutput,
    RouterRequest,
    RouterStageOutcome,
    RuntimeResultStatus,
    SpecialistKind,
    SpecialistOutput,
    StageOutcome,
    StageStatus,
)
from app.agents.orchestration.evidence import (
    build_approved_evidence,
    merge_candidate_evidence,
    merge_strict_evidence,
)
from app.agents.orchestration.execution import (
    MonotonicClock,
    execute_stage,
    latency_budget_failure,
    mapping_failure,
)
from app.agents.orchestration.policy import OrchestrationPolicy
from app.agents.orchestration.requests import (
    build_discovery_request,
    build_itinerary_request,
    build_local_culture_request,
    build_narration_request,
    build_router_request,
)

logger = logging.getLogger("travel_assistant.agents.orchestration")

_PARTIAL_DISCOVERY_MESSAGE = (
    "Một phần dữ liệu địa điểm chưa thể được xác nhận."
)
_LIMITED_SPECIALIST_MESSAGE = (
    "Chưa có đủ bằng chứng để hoàn tất nội dung được yêu cầu."
)
_UNSUPPORTED_MESSAGE = "Yêu cầu này hiện chưa thuộc phạm vi hỗ trợ."
_GROUNDING_MESSAGE = (
    "Một phần nội dung không vượt qua kiểm tra bằng chứng."
)

_SPECIALIST_ORDER = (
    SpecialistKind.NARRATION,
    SpecialistKind.LOCAL_CULTURE,
    SpecialistKind.ITINERARY,
)
_OUTPUT_IDS = {
    AgentKind.DISCOVERY: "runtime-discovery",
    AgentKind.NARRATION: "runtime-narration",
    AgentKind.LOCAL_CULTURE: "runtime-local-culture",
    AgentKind.ITINERARY: "runtime-itinerary",
}


class RouterBoundary(Protocol):
    """Typed Router service boundary used by the orchestrator."""

    async def route(self, request: RouterRequest) -> RouterOutput:
        """Return one validated Router output."""
        ...


class DiscoveryBoundary(Protocol):
    """Typed Discovery service boundary used by the orchestrator."""

    async def discover(self, request: DiscoveryRequest) -> DiscoveryOutput:
        """Return one validated Discovery output."""
        ...


class NarrationBoundary(Protocol):
    """Typed Narration service boundary used by the orchestrator."""

    async def narrate(self, request: NarrationRequest) -> NarrationOutput:
        """Return one validated Narration output."""
        ...


class LocalCultureBoundary(Protocol):
    """Typed Local Culture service boundary used by the orchestrator."""

    async def advise(
        self,
        request: LocalCultureRequest,
    ) -> LocalCultureOutput:
        """Return one validated Local Culture output."""
        ...


class ItineraryBoundary(Protocol):
    """Typed Itinerary service boundary used by the orchestrator."""

    async def draft(self, request: ItineraryRequest) -> ItineraryOutput:
        """Return one validated Itinerary output."""
        ...


class GroundingBoundary(Protocol):
    """Typed Grounding Reviewer service boundary used by the orchestrator."""

    async def review(
        self,
        request: GroundingReviewRequest,
    ) -> GroundingReviewOutput:
        """Return one validated Grounding review."""
        ...


class ComposerBoundary(Protocol):
    """Typed Response Composer service boundary used by the orchestrator."""

    async def compose(
        self,
        request: ResponseComposerRequest,
    ) -> ResponseComposerOutput:
        """Return one validated final output."""
        ...


class AgentOrchestrator(Protocol):
    """Public runtime boundary with one strict request and result."""

    async def run(
        self,
        request: AgentRuntimeRequest,
    ) -> AgentRuntimeResult:
        """Coordinate one request without exposing internal execution state."""
        ...


class AgentOrchestratorService:
    """Coordinate isolated services with scoped inputs and local run state."""

    def __init__(
        self,
        *,
        router: RouterBoundary,
        discovery: DiscoveryBoundary,
        narration: NarrationBoundary,
        local_culture: LocalCultureBoundary,
        itinerary: ItineraryBoundary,
        grounding: GroundingBoundary,
        composer: ComposerBoundary,
        policy: OrchestrationPolicy | None = None,
        monotonic_clock: MonotonicClock = time.monotonic,
    ) -> None:
        self._router = router
        self._discovery = discovery
        self._narration = narration
        self._local_culture = local_culture
        self._itinerary = itinerary
        self._grounding = grounding
        self._composer = composer
        self._policy = policy or OrchestrationPolicy()
        self._clock = monotonic_clock

    async def run(
        self,
        request: AgentRuntimeRequest,
    ) -> AgentRuntimeResult:
        """Run the dependency graph and return only a revalidated result."""
        started = self._clock()
        deadline = started + self._policy.overall_timeout_seconds
        stages: list[StageOutcome] = []
        wrappers: dict[str, SpecialistOutput] = {}

        router_request = build_router_request(request)
        router_stage = await self._run_router(router_request, deadline)
        stages.append(router_stage)
        router_output = router_stage.output
        supplied_evidence = [
            request.context.evidence
            if router_output is not None
            and router_output.primary_intent is not IntentKind.UNSUPPORTED
            else EvidenceBundle()
        ]
        plan = (
            router_output.specialist_plan
            if router_output is not None
            else ()
        )

        discovery_output: DiscoveryOutput | None = None
        if SpecialistKind.DISCOVERY in plan and router_output is not None:
            discovery_stage = await self._run_discovery(
                request,
                router_output,
                deadline,
            )
            stages.append(discovery_stage)
            discovery_output = discovery_stage.output
            if discovery_output is not None:
                supplied_evidence.append(discovery_output.evidence)
                wrapper = DiscoverySpecialistOutput(
                    agent=AgentKind.DISCOVERY,
                    output_id=_OUTPUT_IDS[AgentKind.DISCOVERY],
                    output=discovery_output,
                )
                wrappers[wrapper.output_id] = wrapper

        specialist_stages, specialist_evidence = await self._run_specialists(
            request=request,
            router=router_output,
            plan=plan,
            discovery=discovery_output,
            evidence_bundles=tuple(supplied_evidence),
            deadline=deadline,
        )
        supplied_evidence.extend(specialist_evidence)
        for stage in specialist_stages:
            stages.append(stage)
            stage_wrapper = _specialist_wrapper(stage)
            if stage_wrapper is not None:
                wrappers[stage_wrapper.output_id] = stage_wrapper

        grounding_stage, approved_evidence, approved_outputs = (
            await self._run_grounding(
                evidence_bundles=tuple(supplied_evidence),
                wrappers=tuple(
                    wrappers[key] for key in sorted(wrappers)
                ),
                deadline=deadline,
            )
        )
        stages.append(grounding_stage)

        upstream_warnings, _ = _collect_issues(tuple(stages))
        composer_stage = await self._run_composer(
            request=request,
            evidence=approved_evidence,
            approved_claim_ids=(
                grounding_stage.output.approved_claim_ids
                if grounding_stage.output is not None
                else ()
            ),
            approved_outputs=approved_outputs,
            warnings=upstream_warnings,
            deadline=deadline,
        )
        stages.append(composer_stage)

        warnings, failures = _collect_issues(tuple(stages))
        final_output = composer_stage.output
        status = _runtime_status(
            final_output=final_output,
            stages=tuple(stages),
            warnings=warnings,
            failures=failures,
        )
        result = AgentRuntimeResult(
            request_id=request.request_id,
            status=status,
            final_output=final_output,
            stages=tuple(stages),
            warnings=warnings,
            failures=failures,
        )
        validated = AgentRuntimeResult.model_validate(
            result.model_dump(mode="python")
        )
        logger.info(
            "operation=orchestrate request_id=%s status=%s "
            "stages=%d warnings=%d failures=%d",
            request.request_id,
            validated.status.value,
            len(validated.stages),
            len(validated.warnings),
            len(validated.failures),
        )
        return validated

    async def _run_router(
        self,
        request: RouterRequest,
        deadline: float,
    ) -> RouterStageOutcome:
        execution = await execute_stage(
            agent=AgentKind.ROUTER,
            invoke=lambda: self._router.route(request),
            output_type=RouterOutput,
            validate=_revalidate_router,
            timeout_seconds=self._policy.router_timeout_seconds,
            maximum_attempts=self._policy.maximum_attempts,
            deadline=deadline,
            clock=self._clock,
        )
        if execution.output is None:
            return RouterStageOutcome(
                agent=AgentKind.ROUTER,
                status=StageStatus.FAILED,
                duration_ms=execution.duration_ms,
                failure=execution.failure,
            )
        if execution.output.primary_intent is IntentKind.UNSUPPORTED:
            warning = AgentWarning(
                stage=AgentKind.ROUTER,
                code=FailureCode.UNSUPPORTED_INTENT,
                message=_UNSUPPORTED_MESSAGE,
                retryable=False,
            )
            return RouterStageOutcome(
                agent=AgentKind.ROUTER,
                status=StageStatus.PARTIAL,
                duration_ms=execution.duration_ms,
                output=execution.output,
                warning=warning,
            )
        return RouterStageOutcome(
            agent=AgentKind.ROUTER,
            status=StageStatus.SUCCESS,
            duration_ms=execution.duration_ms,
            output=execution.output,
        )

    async def _run_discovery(
        self,
        runtime_request: AgentRuntimeRequest,
        router: RouterOutput,
        deadline: float,
    ) -> DiscoveryStageOutcome:
        if self._clock() >= deadline:
            return _budget_discovery_stage()
        try:
            request = build_discovery_request(
                runtime_request,
                router,
                self._policy,
            )
        except (TypeError, ValueError):
            return DiscoveryStageOutcome(
                agent=AgentKind.DISCOVERY,
                status=StageStatus.FAILED,
                duration_ms=0.0,
                failure=mapping_failure(AgentKind.DISCOVERY),
            )
        execution = await execute_stage(
            agent=AgentKind.DISCOVERY,
            invoke=lambda: self._discovery.discover(request),
            output_type=DiscoveryOutput,
            validate=_revalidate_discovery,
            timeout_seconds=self._policy.discovery_timeout_seconds,
            maximum_attempts=self._policy.maximum_attempts,
            deadline=deadline,
            clock=self._clock,
        )
        if execution.output is None:
            return DiscoveryStageOutcome(
                agent=AgentKind.DISCOVERY,
                status=StageStatus.FAILED,
                duration_ms=execution.duration_ms,
                failure=execution.failure,
            )
        if execution.output.completeness is DiscoveryCompleteness.PARTIAL:
            warning = AgentWarning(
                stage=AgentKind.DISCOVERY,
                code=FailureCode.PARTIAL_RESULT,
                message=_PARTIAL_DISCOVERY_MESSAGE,
                retryable=False,
            )
            return DiscoveryStageOutcome(
                agent=AgentKind.DISCOVERY,
                status=StageStatus.PARTIAL,
                duration_ms=execution.duration_ms,
                output=execution.output,
                warning=warning,
            )
        return DiscoveryStageOutcome(
            agent=AgentKind.DISCOVERY,
            status=StageStatus.SUCCESS,
            duration_ms=execution.duration_ms,
            output=execution.output,
        )

    async def _run_specialists(
        self,
        *,
        request: AgentRuntimeRequest,
        router: RouterOutput | None,
        plan: tuple[SpecialistKind, ...],
        discovery: DiscoveryOutput | None,
        evidence_bundles: tuple[EvidenceBundle, ...],
        deadline: float,
    ) -> tuple[tuple[StageOutcome, ...], tuple[EvidenceBundle, ...]]:
        planned = tuple(kind for kind in _SPECIALIST_ORDER if kind in plan)
        if router is None or not planned:
            return (), ()

        outcomes: dict[SpecialistKind, StageOutcome] = {}
        tasks: dict[SpecialistKind, asyncio.Task[StageOutcome]] = {}
        supplied: list[EvidenceBundle] = []
        try:
            strict_evidence = merge_strict_evidence(evidence_bundles)
        except (TypeError, ValueError):
            strict_evidence = None

        for kind in planned:
            agent = _agent_for_specialist(kind)
            if self._clock() >= deadline:
                outcomes[kind] = _budget_specialist_stage(agent)
                continue
            try:
                if strict_evidence is None:
                    raise ValueError("Conflicting evidence.")
                if kind is SpecialistKind.NARRATION:
                    narration_request = build_narration_request(
                        request,
                        router,
                        discovery,
                        strict_evidence,
                        self._policy,
                    )
                    supplied.append(narration_request.evidence)
                    tasks[kind] = asyncio.create_task(
                        self._run_narration(
                            narration_request,
                            deadline,
                        )
                    )
                elif kind is SpecialistKind.LOCAL_CULTURE:
                    culture_request = build_local_culture_request(
                        request,
                        router,
                        strict_evidence,
                    )
                    supplied.append(culture_request.evidence)
                    tasks[kind] = asyncio.create_task(
                        self._run_local_culture(
                            culture_request,
                            deadline,
                        )
                    )
                else:
                    itinerary_request = build_itinerary_request(
                        request,
                        router,
                        discovery,
                        strict_evidence,
                        self._policy,
                    )
                    supplied.append(itinerary_request.evidence)
                    tasks[kind] = asyncio.create_task(
                        self._run_itinerary(
                            itinerary_request,
                            deadline,
                        )
                    )
            except (TypeError, ValueError):
                outcomes[kind] = _mapping_specialist_stage(agent)

        if tasks:
            ordered_kinds = tuple(
                kind for kind in planned if kind in tasks
            )
            ordered_tasks = tuple(tasks[kind] for kind in ordered_kinds)
            try:
                completed = await asyncio.gather(*ordered_tasks)
            except asyncio.CancelledError:
                for task in ordered_tasks:
                    task.cancel()
                await asyncio.gather(
                    *ordered_tasks,
                    return_exceptions=True,
                )
                raise
            for kind, outcome in zip(
                ordered_kinds,
                completed,
                strict=True,
            ):
                outcomes[kind] = outcome
        return (
            tuple(outcomes[kind] for kind in planned),
            tuple(supplied),
        )

    async def _run_narration(
        self,
        request: NarrationRequest,
        deadline: float,
    ) -> StageOutcome:
        execution = await execute_stage(
            agent=AgentKind.NARRATION,
            invoke=lambda: self._narration.narrate(request),
            output_type=NarrationOutput,
            validate=lambda output: _validate_narration(output, request),
            timeout_seconds=self._policy.specialist_timeout_seconds,
            maximum_attempts=self._policy.maximum_attempts,
            deadline=deadline,
            clock=self._clock,
        )
        if execution.output is None:
            return NarrationStageOutcome(
                agent=AgentKind.NARRATION,
                status=StageStatus.FAILED,
                duration_ms=execution.duration_ms,
                failure=execution.failure,
            )
        if execution.output.status is AnswerStatus.LIMITED:
            warning = _limited_warning(AgentKind.NARRATION)
            return NarrationStageOutcome(
                agent=AgentKind.NARRATION,
                status=StageStatus.PARTIAL,
                duration_ms=execution.duration_ms,
                output=execution.output,
                warning=warning,
            )
        return NarrationStageOutcome(
            agent=AgentKind.NARRATION,
            status=StageStatus.SUCCESS,
            duration_ms=execution.duration_ms,
            output=execution.output,
        )

    async def _run_local_culture(
        self,
        request: LocalCultureRequest,
        deadline: float,
    ) -> StageOutcome:
        execution = await execute_stage(
            agent=AgentKind.LOCAL_CULTURE,
            invoke=lambda: self._local_culture.advise(request),
            output_type=LocalCultureOutput,
            validate=lambda output: _validate_culture(output, request),
            timeout_seconds=self._policy.specialist_timeout_seconds,
            maximum_attempts=self._policy.maximum_attempts,
            deadline=deadline,
            clock=self._clock,
        )
        if execution.output is None:
            return LocalCultureStageOutcome(
                agent=AgentKind.LOCAL_CULTURE,
                status=StageStatus.FAILED,
                duration_ms=execution.duration_ms,
                failure=execution.failure,
            )
        if execution.output.status is AnswerStatus.LIMITED:
            warning = _limited_warning(AgentKind.LOCAL_CULTURE)
            return LocalCultureStageOutcome(
                agent=AgentKind.LOCAL_CULTURE,
                status=StageStatus.PARTIAL,
                duration_ms=execution.duration_ms,
                output=execution.output,
                warning=warning,
            )
        return LocalCultureStageOutcome(
            agent=AgentKind.LOCAL_CULTURE,
            status=StageStatus.SUCCESS,
            duration_ms=execution.duration_ms,
            output=execution.output,
        )

    async def _run_itinerary(
        self,
        request: ItineraryRequest,
        deadline: float,
    ) -> StageOutcome:
        execution = await execute_stage(
            agent=AgentKind.ITINERARY,
            invoke=lambda: self._itinerary.draft(request),
            output_type=ItineraryOutput,
            validate=lambda output: _validate_itinerary(output, request),
            timeout_seconds=self._policy.specialist_timeout_seconds,
            maximum_attempts=self._policy.maximum_attempts,
            deadline=deadline,
            clock=self._clock,
        )
        if execution.output is None:
            return ItineraryStageOutcome(
                agent=AgentKind.ITINERARY,
                status=StageStatus.FAILED,
                duration_ms=execution.duration_ms,
                failure=execution.failure,
            )
        return ItineraryStageOutcome(
            agent=AgentKind.ITINERARY,
            status=StageStatus.SUCCESS,
            duration_ms=execution.duration_ms,
            output=execution.output,
        )

    async def _run_grounding(
        self,
        *,
        evidence_bundles: tuple[EvidenceBundle, ...],
        wrappers: tuple[SpecialistOutput, ...],
        deadline: float,
    ) -> tuple[
        GroundingStageOutcome,
        EvidenceBundle,
        tuple[SpecialistOutput, ...],
    ]:
        if self._clock() >= deadline:
            return _budget_grounding_stage(), EvidenceBundle(), ()
        try:
            candidates = merge_candidate_evidence(evidence_bundles)
            request = GroundingReviewRequest(
                evidence=candidates,
                specialist_outputs=wrappers,
                freshness_requirements=(),
            )
        except (TypeError, ValueError):
            return (
                GroundingStageOutcome(
                    agent=AgentKind.GROUNDING_REVIEWER,
                    status=StageStatus.FAILED,
                    duration_ms=0.0,
                    failure=mapping_failure(
                        AgentKind.GROUNDING_REVIEWER,
                    ),
                ),
                EvidenceBundle(),
                (),
            )
        execution = await execute_stage(
            agent=AgentKind.GROUNDING_REVIEWER,
            invoke=lambda: self._grounding.review(request),
            output_type=GroundingReviewOutput,
            validate=lambda output: _validate_grounding(output, request),
            timeout_seconds=self._policy.grounding_timeout_seconds,
            maximum_attempts=self._policy.maximum_attempts,
            deadline=deadline,
            clock=self._clock,
        )
        if execution.output is None:
            return (
                GroundingStageOutcome(
                    agent=AgentKind.GROUNDING_REVIEWER,
                    status=StageStatus.FAILED,
                    duration_ms=execution.duration_ms,
                    failure=execution.failure,
                ),
                EvidenceBundle(),
                (),
            )
        try:
            approved_evidence = build_approved_evidence(
                candidates,
                execution.output,
            )
            approved_ids = set(
                execution.output.approved_specialist_output_ids
            )
            approved_outputs = tuple(
                output
                for output in wrappers
                if output.output_id in approved_ids
            )
        except (TypeError, ValueError):
            return (
                GroundingStageOutcome(
                    agent=AgentKind.GROUNDING_REVIEWER,
                    status=StageStatus.FAILED,
                    duration_ms=execution.duration_ms,
                    failure=mapping_failure(
                        AgentKind.GROUNDING_REVIEWER,
                        code=FailureCode.INVALID_OUTPUT,
                    ),
                ),
                EvidenceBundle(),
                (),
            )
        if execution.output.status is GroundingReviewStatus.APPROVED:
            stage = GroundingStageOutcome(
                agent=AgentKind.GROUNDING_REVIEWER,
                status=StageStatus.SUCCESS,
                duration_ms=execution.duration_ms,
                output=execution.output,
            )
        else:
            stage = GroundingStageOutcome(
                agent=AgentKind.GROUNDING_REVIEWER,
                status=StageStatus.PARTIAL,
                duration_ms=execution.duration_ms,
                output=execution.output,
                warning=AgentWarning(
                    stage=AgentKind.GROUNDING_REVIEWER,
                    code=FailureCode.GROUNDING_REJECTED,
                    message=_GROUNDING_MESSAGE,
                    retryable=False,
                ),
            )
        return stage, approved_evidence, approved_outputs

    async def _run_composer(
        self,
        *,
        request: AgentRuntimeRequest,
        evidence: EvidenceBundle,
        approved_claim_ids: tuple[str, ...],
        approved_outputs: tuple[SpecialistOutput, ...],
        warnings: tuple[AgentWarning, ...],
        deadline: float,
    ) -> ComposerStageOutcome:
        if self._clock() >= deadline:
            return _budget_composer_stage()
        try:
            composer_request = ResponseComposerRequest(
                user_query=request.user_query,
                locale=request.locale,
                evidence=evidence,
                approved_claim_ids=approved_claim_ids,
                approved_specialist_outputs=approved_outputs,
                warnings=warnings,
            )
        except (TypeError, ValueError):
            return ComposerStageOutcome(
                agent=AgentKind.RESPONSE_COMPOSER,
                status=StageStatus.FAILED,
                duration_ms=0.0,
                failure=mapping_failure(
                    AgentKind.RESPONSE_COMPOSER,
                ),
            )
        execution = await execute_stage(
            agent=AgentKind.RESPONSE_COMPOSER,
            invoke=lambda: self._composer.compose(composer_request),
            output_type=ResponseComposerOutput,
            validate=lambda output: _validate_composer(
                output,
                composer_request,
            ),
            timeout_seconds=self._policy.composer_timeout_seconds,
            maximum_attempts=self._policy.maximum_attempts,
            deadline=deadline,
            clock=self._clock,
        )
        if execution.output is None:
            return ComposerStageOutcome(
                agent=AgentKind.RESPONSE_COMPOSER,
                status=StageStatus.FAILED,
                duration_ms=execution.duration_ms,
                failure=execution.failure,
            )
        return ComposerStageOutcome(
            agent=AgentKind.RESPONSE_COMPOSER,
            status=StageStatus.SUCCESS,
            duration_ms=execution.duration_ms,
            output=execution.output,
        )


def _revalidate_router(output: RouterOutput) -> RouterOutput:
    return RouterOutput.model_validate(output.model_dump(mode="python"))


def _revalidate_discovery(output: DiscoveryOutput) -> DiscoveryOutput:
    return DiscoveryOutput.model_validate(output.model_dump(mode="python"))


def _validate_narration(
    output: NarrationOutput,
    request: NarrationRequest,
) -> NarrationOutput:
    validated = NarrationOutput.model_validate(
        output.model_dump(mode="python")
    )
    return validated.validate_against(request)


def _validate_culture(
    output: LocalCultureOutput,
    request: LocalCultureRequest,
) -> LocalCultureOutput:
    validated = LocalCultureOutput.model_validate(
        output.model_dump(mode="python")
    )
    return validated.validate_against(request)


def _validate_itinerary(
    output: ItineraryOutput,
    request: ItineraryRequest,
) -> ItineraryOutput:
    validated = ItineraryOutput.model_validate(
        output.model_dump(mode="python")
    )
    return validated.validate_against(request)


def _validate_grounding(
    output: GroundingReviewOutput,
    request: GroundingReviewRequest,
) -> GroundingReviewOutput:
    validated = GroundingReviewOutput.model_validate(
        output.model_dump(mode="python")
    )
    return validated.validate_against(request)


def _validate_composer(
    output: ResponseComposerOutput,
    request: ResponseComposerRequest,
) -> ResponseComposerOutput:
    validated = ResponseComposerOutput.model_validate(
        output.model_dump(mode="python")
    )
    return validated.validate_against(request)


def _limited_warning(agent: AgentKind) -> AgentWarning:
    return AgentWarning(
        stage=agent,
        code=FailureCode.INSUFFICIENT_EVIDENCE,
        message=_LIMITED_SPECIALIST_MESSAGE,
        retryable=False,
    )


def _agent_for_specialist(kind: SpecialistKind) -> AgentKind:
    if kind is SpecialistKind.NARRATION:
        return AgentKind.NARRATION
    if kind is SpecialistKind.LOCAL_CULTURE:
        return AgentKind.LOCAL_CULTURE
    if kind is SpecialistKind.ITINERARY:
        return AgentKind.ITINERARY
    raise ValueError("Discovery is not a fan-out specialist.")


def _mapping_specialist_stage(agent: AgentKind) -> StageOutcome:
    failure = mapping_failure(agent)
    if agent is AgentKind.NARRATION:
        return NarrationStageOutcome(
            agent=agent,
            status=StageStatus.FAILED,
            duration_ms=0.0,
            failure=failure,
        )
    if agent is AgentKind.LOCAL_CULTURE:
        return LocalCultureStageOutcome(
            agent=agent,
            status=StageStatus.FAILED,
            duration_ms=0.0,
            failure=failure,
        )
    return ItineraryStageOutcome(
        agent=AgentKind.ITINERARY,
        status=StageStatus.FAILED,
        duration_ms=0.0,
        failure=failure,
    )


def _budget_specialist_stage(agent: AgentKind) -> StageOutcome:
    failure = latency_budget_failure(agent)
    if agent is AgentKind.NARRATION:
        return NarrationStageOutcome(
            agent=agent,
            status=StageStatus.FAILED,
            duration_ms=0.0,
            failure=failure,
        )
    if agent is AgentKind.LOCAL_CULTURE:
        return LocalCultureStageOutcome(
            agent=agent,
            status=StageStatus.FAILED,
            duration_ms=0.0,
            failure=failure,
        )
    return ItineraryStageOutcome(
        agent=AgentKind.ITINERARY,
        status=StageStatus.FAILED,
        duration_ms=0.0,
        failure=failure,
    )


def _budget_discovery_stage() -> DiscoveryStageOutcome:
    return DiscoveryStageOutcome(
        agent=AgentKind.DISCOVERY,
        status=StageStatus.FAILED,
        duration_ms=0.0,
        failure=latency_budget_failure(AgentKind.DISCOVERY),
    )


def _budget_grounding_stage() -> GroundingStageOutcome:
    return GroundingStageOutcome(
        agent=AgentKind.GROUNDING_REVIEWER,
        status=StageStatus.FAILED,
        duration_ms=0.0,
        failure=latency_budget_failure(AgentKind.GROUNDING_REVIEWER),
    )


def _budget_composer_stage() -> ComposerStageOutcome:
    return ComposerStageOutcome(
        agent=AgentKind.RESPONSE_COMPOSER,
        status=StageStatus.FAILED,
        duration_ms=0.0,
        failure=latency_budget_failure(AgentKind.RESPONSE_COMPOSER),
    )


def _specialist_wrapper(stage: StageOutcome) -> SpecialistOutput | None:
    if isinstance(stage, NarrationStageOutcome) and stage.output is not None:
        return NarrationSpecialistOutput(
            agent=AgentKind.NARRATION,
            output_id=_OUTPUT_IDS[AgentKind.NARRATION],
            output=stage.output,
        )
    if (
        isinstance(stage, LocalCultureStageOutcome)
        and stage.output is not None
    ):
        return LocalCultureSpecialistOutput(
            agent=AgentKind.LOCAL_CULTURE,
            output_id=_OUTPUT_IDS[AgentKind.LOCAL_CULTURE],
            output=stage.output,
        )
    if isinstance(stage, ItineraryStageOutcome) and stage.output is not None:
        return ItinerarySpecialistOutput(
            agent=AgentKind.ITINERARY,
            output_id=_OUTPUT_IDS[AgentKind.ITINERARY],
            output=stage.output,
        )
    return None


def _collect_issues(
    stages: tuple[StageOutcome, ...],
) -> tuple[tuple[AgentWarning, ...], tuple[AgentFailure, ...]]:
    warnings: list[AgentWarning] = []
    failures: list[AgentFailure] = []
    for stage in stages:
        if stage.warning is not None and stage.warning not in warnings:
            warnings.append(stage.warning)
        if (
            isinstance(stage, ItineraryStageOutcome)
            and stage.output is not None
        ):
            for warning in stage.output.warnings:
                if warning not in warnings:
                    warnings.append(warning)
        if (
            isinstance(stage, GroundingStageOutcome)
            and stage.output is not None
        ):
            for warning in stage.output.warnings:
                if warning not in warnings:
                    warnings.append(warning)
        if stage.failure is not None and stage.failure not in failures:
            failures.append(stage.failure)
    return tuple(warnings), tuple(failures)


def _runtime_status(
    *,
    final_output: ResponseComposerOutput | None,
    stages: tuple[StageOutcome, ...],
    warnings: tuple[AgentWarning, ...],
    failures: tuple[AgentFailure, ...],
) -> RuntimeResultStatus:
    if final_output is None:
        return RuntimeResultStatus.FAILED
    if warnings or failures or any(
        stage.status is not StageStatus.SUCCESS for stage in stages
    ):
        return RuntimeResultStatus.PARTIAL
    return RuntimeResultStatus.SUCCESS
