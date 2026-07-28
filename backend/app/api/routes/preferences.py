"""Canonical authenticated user-preference HTTP resource."""

import logging
from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import FirebaseAuthentication
from app.auth.models import AuthenticatedPrincipal
from app.middleware.request_id import REQUEST_ID_STATE_KEY
from app.preferences.contracts import PreferenceDocument, PreferenceResponse
from app.preferences.service import PreferenceService
from app.preferences.store import PreferenceStoreError

logger = logging.getLogger("travel_assistant.api")
PreferenceServiceDependency = Callable[[], AsyncIterator[PreferenceService]]


class PreferenceHTTPException(HTTPException):
    """Controlled sanitized preference failure."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            detail="Preferences are temporarily unavailable.",
        )
        self.code = "preferences_unavailable"


def create_preferences_router(
    service_dependency: PreferenceServiceDependency,
    authentication: FirebaseAuthentication,
) -> APIRouter:
    """Create the sole private preference resource."""
    router = APIRouter()

    @router.get("/preferences", response_model=PreferenceResponse)
    async def get_preferences(
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(authentication.required),
        ],
        service: Annotated[
            PreferenceService,
            Depends(service_dependency),
        ],
        request: Request,
    ) -> PreferenceResponse:
        """Read only the authenticated owner's current document."""
        try:
            return await service.get(principal.uid)
        except PreferenceStoreError as error:
            _log_failure(request, operation="get")
            raise PreferenceHTTPException from error

    @router.put("/preferences", response_model=PreferenceResponse)
    async def replace_preferences(
        document: PreferenceDocument,
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(authentication.required),
        ],
        service: Annotated[
            PreferenceService,
            Depends(service_dependency),
        ],
        request: Request,
    ) -> PreferenceResponse:
        """Replace the authenticated owner's complete document."""
        try:
            return await service.replace(principal.uid, document)
        except PreferenceStoreError as error:
            _log_failure(request, operation="put")
            raise PreferenceHTTPException from error

    return router


def _log_failure(request: Request, *, operation: str) -> None:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, "unavailable")
    logger.error(
        "Preference operation failed request_id=%s operation=%s "
        "code=persistence_failure",
        request_id,
        operation,
    )
