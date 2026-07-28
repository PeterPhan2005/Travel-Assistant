"""Strict code-orchestrated runtime request/result contracts."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import Field, StrictFloat, model_validator

from app.agents.contracts.common import (
    AgentFailure,
    AgentKind,
    AgentWarning,
    ContractModel,
    LocaleCode,
    NormalizedQuery,
    RequestId,
    SupportedCity,
    validate_issue_stage,
)
from app.agents.contracts.composer import ResponseComposerOutput
from app.agents.contracts.discovery import DiscoveryOrigin, DiscoveryOutput
from app.agents.contracts.grounding import GroundingReviewOutput
from app.agents.contracts.itinerary import ItineraryOutput
from app.agents.contracts.local_culture import LocalCultureOutput
from app.agents.contracts.narration import NarrationOutput
from app.agents.contracts.router import RouterOutput
from app.preferences.contracts import PreferenceDocument

DurationMilliseconds = Annotated[
    StrictFloat,
    Field(ge=0, le=3_600_000, allow_inf_nan=False),
]


class StageStatus(StrEnum):
    """Sanitized disposition of one separate agent execution."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class RuntimeResultStatus(StrEnum):
    """Overall runtime disposition."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


def _validate_stage_shape(
    *,
    agent: AgentKind,
    status: StageStatus,
    output_present: bool,
    warning: AgentWarning | None,
    failure: AgentFailure | None,
    duration_ms: float,
) -> None:
    if not math.isfinite(duration_ms):
        raise ValueError("Stage duration must be finite.")
    if warning is not None:
        validate_issue_stage(warning, agent)
    if failure is not None:
        validate_issue_stage(failure, agent)
    if status is StageStatus.SUCCESS:
        if not output_present or failure is not None:
            raise ValueError("Successful stage requires output and no failure.")
    elif status is StageStatus.PARTIAL:
        if not output_present or (warning is None and failure is None):
            raise ValueError(
                "Partial stage requires usable output and an issue."
            )
    elif output_present or failure is None:
        raise ValueError("Failed stage requires failure and no output.")


class RouterStageOutcome(ContractModel):
    """Sanitized Router Agent stage outcome."""

    agent: Literal[AgentKind.ROUTER]
    status: StageStatus
    duration_ms: DurationMilliseconds
    output: RouterOutput | None = None
    warning: AgentWarning | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> RouterStageOutcome:
        """Enforce router stage status consistency."""
        _validate_stage_shape(
            agent=AgentKind.ROUTER,
            status=self.status,
            output_present=self.output is not None,
            warning=self.warning,
            failure=self.failure,
            duration_ms=self.duration_ms,
        )
        return self


class DiscoveryStageOutcome(ContractModel):
    """Sanitized Discovery Agent stage outcome."""

    agent: Literal[AgentKind.DISCOVERY]
    status: StageStatus
    duration_ms: DurationMilliseconds
    output: DiscoveryOutput | None = None
    warning: AgentWarning | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> DiscoveryStageOutcome:
        """Enforce discovery stage status consistency."""
        _validate_stage_shape(
            agent=AgentKind.DISCOVERY,
            status=self.status,
            output_present=self.output is not None,
            warning=self.warning,
            failure=self.failure,
            duration_ms=self.duration_ms,
        )
        return self


class NarrationStageOutcome(ContractModel):
    """Sanitized Narration Agent stage outcome."""

    agent: Literal[AgentKind.NARRATION]
    status: StageStatus
    duration_ms: DurationMilliseconds
    output: NarrationOutput | None = None
    warning: AgentWarning | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> NarrationStageOutcome:
        """Enforce narration stage status consistency."""
        _validate_stage_shape(
            agent=AgentKind.NARRATION,
            status=self.status,
            output_present=self.output is not None,
            warning=self.warning,
            failure=self.failure,
            duration_ms=self.duration_ms,
        )
        return self


class LocalCultureStageOutcome(ContractModel):
    """Sanitized Local Culture Agent stage outcome."""

    agent: Literal[AgentKind.LOCAL_CULTURE]
    status: StageStatus
    duration_ms: DurationMilliseconds
    output: LocalCultureOutput | None = None
    warning: AgentWarning | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> LocalCultureStageOutcome:
        """Enforce local-culture stage status consistency."""
        _validate_stage_shape(
            agent=AgentKind.LOCAL_CULTURE,
            status=self.status,
            output_present=self.output is not None,
            warning=self.warning,
            failure=self.failure,
            duration_ms=self.duration_ms,
        )
        return self


class ItineraryStageOutcome(ContractModel):
    """Sanitized Itinerary Agent stage outcome."""

    agent: Literal[AgentKind.ITINERARY]
    status: StageStatus
    duration_ms: DurationMilliseconds
    output: ItineraryOutput | None = None
    warning: AgentWarning | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> ItineraryStageOutcome:
        """Enforce itinerary stage status consistency."""
        _validate_stage_shape(
            agent=AgentKind.ITINERARY,
            status=self.status,
            output_present=self.output is not None,
            warning=self.warning,
            failure=self.failure,
            duration_ms=self.duration_ms,
        )
        return self


class GroundingStageOutcome(ContractModel):
    """Sanitized Grounding Reviewer stage outcome."""

    agent: Literal[AgentKind.GROUNDING_REVIEWER]
    status: StageStatus
    duration_ms: DurationMilliseconds
    output: GroundingReviewOutput | None = None
    warning: AgentWarning | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> GroundingStageOutcome:
        """Enforce grounding stage status consistency."""
        _validate_stage_shape(
            agent=AgentKind.GROUNDING_REVIEWER,
            status=self.status,
            output_present=self.output is not None,
            warning=self.warning,
            failure=self.failure,
            duration_ms=self.duration_ms,
        )
        return self


class ComposerStageOutcome(ContractModel):
    """Sanitized Response Composer stage outcome."""

    agent: Literal[AgentKind.RESPONSE_COMPOSER]
    status: StageStatus
    duration_ms: DurationMilliseconds
    output: ResponseComposerOutput | None = None
    warning: AgentWarning | None = None
    failure: AgentFailure | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> ComposerStageOutcome:
        """Enforce response-composer stage status consistency."""
        _validate_stage_shape(
            agent=AgentKind.RESPONSE_COMPOSER,
            status=self.status,
            output_present=self.output is not None,
            warning=self.warning,
            failure=self.failure,
            duration_ms=self.duration_ms,
        )
        return self


StageOutcome: TypeAlias = Annotated[
    RouterStageOutcome
    | DiscoveryStageOutcome
    | NarrationStageOutcome
    | LocalCultureStageOutcome
    | ItineraryStageOutcome
    | GroundingStageOutcome
    | ComposerStageOutcome,
    Field(discriminator="agent"),
]

_STAGE_ORDER = {
    AgentKind.ROUTER: 0,
    AgentKind.DISCOVERY: 1,
    AgentKind.NARRATION: 2,
    AgentKind.LOCAL_CULTURE: 3,
    AgentKind.ITINERARY: 4,
    AgentKind.GROUNDING_REVIEWER: 5,
    AgentKind.RESPONSE_COMPOSER: 6,
}


class AgentRuntimeRequest(ContractModel):
    """Code-orchestrator input; origin is request-scoped and input-only."""

    request_id: RequestId
    user_query: NormalizedQuery
    locale: LocaleCode
    city: SupportedCity | None = None
    preferences: PreferenceDocument | None = None
    discovery_origin: DiscoveryOrigin | None = None


class AgentRuntimeResult(ContractModel):
    """Coordinate-free final result with sanitized per-stage outcomes."""

    request_id: RequestId
    status: RuntimeResultStatus
    final_output: ResponseComposerOutput | None = None
    stages: Annotated[
        tuple[StageOutcome, ...],
        Field(min_length=1, max_length=7),
    ]
    warnings: Annotated[
        tuple[AgentWarning, ...],
        Field(max_length=30),
    ] = ()
    failures: Annotated[
        tuple[AgentFailure, ...],
        Field(max_length=30),
    ] = ()

    @model_validator(mode="after")
    def validate_runtime_result(self) -> AgentRuntimeResult:
        """Fail closed on duplicate stages or inconsistent overall status."""
        agents = tuple(stage.agent for stage in self.stages)
        expected_agents = tuple(
            sorted(set(agents), key=_STAGE_ORDER.__getitem__)
        )
        if agents != expected_agents:
            raise ValueError(
                "Stage outcomes must be unique and in canonical order."
            )
        if self.final_output is not None:
            if self.final_output.warnings != self.warnings:
                raise ValueError(
                    "Final output must preserve runtime warnings."
                )
            composer_stages = tuple(
                stage
                for stage in self.stages
                if isinstance(stage, ComposerStageOutcome)
            )
            if len(composer_stages) != 1:
                raise ValueError(
                    "Usable final output requires one composer stage."
                )
            if composer_stages[0].output != self.final_output:
                raise ValueError(
                    "Final output differs from the composer stage output."
                )

        has_stage_issue = any(
            stage.status is not StageStatus.SUCCESS for stage in self.stages
        )
        if self.status is RuntimeResultStatus.SUCCESS:
            if self.final_output is None:
                raise ValueError("Successful runtime requires final output.")
            if self.failures or has_stage_issue:
                raise ValueError(
                    "Successful runtime cannot contain a failed stage."
                )
        elif self.status is RuntimeResultStatus.PARTIAL:
            if self.final_output is None:
                raise ValueError("Partial runtime requires usable final output.")
            if not self.warnings and not self.failures and not has_stage_issue:
                raise ValueError(
                    "Partial runtime requires a warning or failure."
                )
        else:
            if self.final_output is not None:
                raise ValueError(
                    "Failed runtime cannot contain a successful final answer."
                )
            if not self.failures:
                raise ValueError("Failed runtime requires a safe failure.")
        return self
