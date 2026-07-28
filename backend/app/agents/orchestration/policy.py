"""Immutable bounded policy for application-code orchestration."""

from typing import Annotated, Literal

from pydantic import Field, StrictFloat

from app.agents.contracts import ContractModel, NarrationWordRange

MAX_ORCHESTRATION_DISCOVERY_RADIUS_METRES = 50_000
MAX_ORCHESTRATION_DISCOVERY_RESULTS = 20


class OrchestrationPolicy(ContractModel):
    """Explicit time, retry, and request defaults with no wall-clock values."""

    overall_timeout_seconds: Annotated[
        StrictFloat,
        Field(gt=0, le=120, allow_inf_nan=False),
    ] = 30.0
    router_timeout_seconds: Annotated[
        StrictFloat,
        Field(gt=0, le=60, allow_inf_nan=False),
    ] = 3.0
    discovery_timeout_seconds: Annotated[
        StrictFloat,
        Field(gt=0, le=60, allow_inf_nan=False),
    ] = 8.0
    specialist_timeout_seconds: Annotated[
        StrictFloat,
        Field(gt=0, le=60, allow_inf_nan=False),
    ] = 8.0
    grounding_timeout_seconds: Annotated[
        StrictFloat,
        Field(gt=0, le=60, allow_inf_nan=False),
    ] = 5.0
    composer_timeout_seconds: Annotated[
        StrictFloat,
        Field(gt=0, le=60, allow_inf_nan=False),
    ] = 5.0
    maximum_attempts: Literal[1, 2] = 2
    discovery_radius_metres: Annotated[
        int,
        Field(
            strict=True,
            gt=0,
            le=MAX_ORCHESTRATION_DISCOVERY_RADIUS_METRES,
        ),
    ] = 5_000
    discovery_limit: Annotated[
        int,
        Field(
            strict=True,
            gt=0,
            le=MAX_ORCHESTRATION_DISCOVERY_RESULTS,
        ),
    ] = 5
    narration_word_range: NarrationWordRange = NarrationWordRange(
        minimum_words=100,
        maximum_words=200,
    )
    default_itinerary_maximum_stops: Annotated[
        int,
        Field(strict=True, gt=0, le=20),
    ] = 5
