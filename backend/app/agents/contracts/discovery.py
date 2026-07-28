"""Strict Discovery Agent contracts over provider-neutral POI values."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StrictBool, model_validator

from app.agents.contracts.common import (
    AgentFailure,
    AgentKind,
    ContractModel,
    EvidenceBundle,
    FactKind,
    FailureCode,
    ShortText,
    validate_sorted_unique,
)
from app.providers.poi.models import (
    MAX_DISCOVERY_RADIUS_METRES,
    MAX_DISCOVERY_RESULTS,
    Coordinates,
    PoiDiscoveryResult,
    SupportedCity,
)


class DiscoveryCompleteness(StrEnum):
    """Whether discovery is complete or a safe usable partial result."""

    COMPLETE = "complete"
    PARTIAL = "partial"


class DiscoveryOrigin(Coordinates):
    """Request-scoped WGS84 origin, never copied into runtime results."""

    model_config = ContractModel.model_config


class DiscoveryCandidate(PoiDiscoveryResult):
    """Strict normalized T032 POI candidate reused without provider payloads."""

    model_config = ContractModel.model_config


class DiscoveryRequest(ContractModel):
    """Scoped discovery input containing the only accepted request origin."""

    city: SupportedCity
    origin: DiscoveryOrigin
    radius_metres: Annotated[
        int,
        Field(strict=True, gt=0, le=MAX_DISCOVERY_RADIUS_METRES),
    ]
    limit: Annotated[
        int,
        Field(strict=True, gt=0, le=MAX_DISCOVERY_RESULTS),
    ]
    query: ShortText | None = None
    category: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=80),
    ] | None = None
    requested_fact_kinds: Annotated[
        tuple[FactKind, ...],
        Field(min_length=1, max_length=len(FactKind)),
    ]

    @model_validator(mode="after")
    def validate_fact_needs(self) -> DiscoveryRequest:
        """Keep requested fact needs deterministic and duplicate-free."""
        values = tuple(item.value for item in self.requested_fact_kinds)
        validate_sorted_unique(values, label="Requested fact kinds")
        return self


class DiscoveryOutput(ContractModel):
    """Normalized candidates, evidence, and sanitized partial-provider state."""

    candidates: Annotated[
        tuple[DiscoveryCandidate, ...],
        Field(max_length=MAX_DISCOVERY_RESULTS),
    ] = ()
    evidence: EvidenceBundle
    provider_failures: Annotated[
        tuple[AgentFailure, ...],
        Field(max_length=10),
    ] = ()
    completeness: DiscoveryCompleteness
    is_truncated: StrictBool

    @model_validator(mode="after")
    def validate_discovery_result(self) -> DiscoveryOutput:
        """Enforce stable candidates, evidence closure, and partial semantics."""
        candidate_ids = tuple(item.id for item in self.candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Candidate IDs must be unique.")
        known_sources = self.evidence.source_ids
        for candidate in self.candidates:
            candidate_source_ids = {
                source.source_id for source in candidate.sources
            }
            if not candidate_source_ids.issubset(known_sources):
                raise ValueError("Candidate references a missing source.")
        for failure in self.provider_failures:
            if failure.stage is not AgentKind.DISCOVERY:
                raise ValueError(
                    "Provider failure must belong to discovery."
                )
            if failure.code not in {
                FailureCode.INVALID_OUTPUT,
                FailureCode.PROVIDER_TIMEOUT,
                FailureCode.PROVIDER_UNAVAILABLE,
            }:
                raise ValueError("Discovery provider failure code is invalid.")
        is_partial = self.completeness is DiscoveryCompleteness.PARTIAL
        if is_partial:
            if not self.candidates:
                raise ValueError(
                    "Partial discovery requires at least one usable candidate."
                )
            if not self.provider_failures and not self.is_truncated:
                raise ValueError(
                    "Partial discovery requires a failure or truncation."
                )
        elif self.provider_failures or self.is_truncated:
            raise ValueError(
                "Complete discovery cannot contain failures or truncation."
            )
        return self
