"""Canonical authenticated assistant query endpoint."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.agents.orchestration import AgentOrchestrator
from app.assistant.contracts import (
    AssistantQueryRequest,
    AssistantQueryResponse,
)
from app.auth.dependencies import FirebaseAuthentication
from app.auth.models import AuthenticatedPrincipal
from app.middleware.request_id import REQUEST_ID_STATE_KEY
from app.preferences.service import PreferenceService
from app.preferences.store import PreferenceStoreError

logger = logging.getLogger("travel_assistant.api")
AssistantOrchestratorDependency = Callable[
    [],
    AsyncIterator[AgentOrchestrator],
]
PreferenceServiceDependency = Callable[[], AsyncIterator[PreferenceService]]


def create_assistant_router(
    orchestrator_dependency: AssistantOrchestratorDependency,
    authentication: FirebaseAuthentication,
    preference_service_dependency: PreferenceServiceDependency,
) -> APIRouter:
    """Create the sole private assistant query resource."""
    router = APIRouter()

    @router.post(
        "/v1/assistant/query",
        response_model=AssistantQueryResponse,
    )
    async def query_assistant(
        payload: AssistantQueryRequest,
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(authentication.required),
        ],
        orchestrator: Annotated[
            AgentOrchestrator,
            Depends(orchestrator_dependency),
        ],
        preference_service: Annotated[
            PreferenceService,
            Depends(preference_service_dependency),
        ],
        request: Request,
    ) -> AssistantQueryResponse:
        """Run one confirmed-text request without retaining identity or input."""
        request_id = getattr(request.state, REQUEST_ID_STATE_KEY)
        try:
            preference_projection = await preference_service.get_projection(
                principal.uid
            )
        except PreferenceStoreError:
            preference_projection = None
            logger.warning(
                "operation=assistant_preference_projection request_id=%s "
                "result=omitted",
                request_id,
            )
        del principal
        runtime_request = payload.to_runtime_request(
            request_id,
            preference_projection,
        )
        try:
            result = await orchestrator.run(runtime_request)
        except asyncio.CancelledError:
            raise
        response = AssistantQueryResponse.from_runtime(
            result,
            request_id=request_id,
        )
        logger.info(
            "operation=assistant_query request_id=%s status=%s intent=%s "
            "pois=%d sources=%d warnings=%d",
            request_id,
            response.status.value,
            response.intent.value if response.intent is not None else "none",
            len(response.poi_results),
            len(response.sources),
            len(response.warnings),
        )
        return response

    return router
