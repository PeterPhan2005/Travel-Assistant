"""Canonical authenticated structured itinerary draft-generation endpoint."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import FirebaseAuthentication
from app.auth.models import AuthenticatedPrincipal
from app.itinerary_generation import (
    ItineraryDraftGenerationRequest,
    ItineraryDraftGenerationResponse,
    StructuredItineraryGenerator,
)
from app.middleware.request_id import REQUEST_ID_STATE_KEY

logger = logging.getLogger("travel_assistant.api")
ItineraryGeneratorDependency = Callable[
    [],
    AsyncIterator[StructuredItineraryGenerator],
]


def create_itinerary_drafts_router(
    generator_dependency: ItineraryGeneratorDependency,
    authentication: FirebaseAuthentication,
) -> APIRouter:
    """Create the sole generation-only itinerary draft route."""
    router = APIRouter()

    @router.post(
        "/v1/itinerary-drafts/generate",
        response_model=ItineraryDraftGenerationResponse,
    )
    async def generate_itinerary_draft(
        payload: ItineraryDraftGenerationRequest,
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(authentication.required),
        ],
        generator: Annotated[
            StructuredItineraryGenerator,
            Depends(generator_dependency),
        ],
        request: Request,
    ) -> ItineraryDraftGenerationResponse:
        del principal
        try:
            response = await generator.generate(payload)
        except asyncio.CancelledError:
            raise
        request_id = getattr(request.state, REQUEST_ID_STATE_KEY)
        logger.info(
            "operation=itinerary_draft_generate request_id=%s status=%s "
            "items=%d warnings=%d",
            request_id,
            response.status.value,
            len(response.items),
            len(response.warnings),
        )
        return response

    return router
