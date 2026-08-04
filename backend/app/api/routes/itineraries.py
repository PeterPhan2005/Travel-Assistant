"""Canonical authenticated saved-itinerary CRUD resource."""

import logging
from collections.abc import AsyncIterator, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import FirebaseAuthentication
from app.auth.models import AuthenticatedPrincipal
from app.itineraries import (
    ItineraryConflictError,
    ItineraryDeleteRequest,
    ItineraryDeleteResponse,
    ItineraryNotFoundError,
    ItineraryReplaceRequest,
    ItineraryStoreError,
    SavedItineraryListResponse,
    SavedItineraryResponse,
    SavedItineraryService,
)
from app.middleware.request_id import REQUEST_ID_STATE_KEY

logger = logging.getLogger("travel_assistant.api")
ItineraryServiceDependency = Callable[
    [],
    AsyncIterator[SavedItineraryService],
]


class SavedItineraryHTTPException(HTTPException):
    """Controlled saved-itinerary failure with a stable public code."""

    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code


def create_itineraries_router(
    service_dependency: ItineraryServiceDependency,
    authentication: FirebaseAuthentication,
) -> APIRouter:
    """Create one private full-snapshot saved-itinerary resource."""
    router = APIRouter(prefix="/v1/itineraries")

    @router.get("", response_model=SavedItineraryListResponse)
    async def list_itineraries(
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(authentication.required),
        ],
        service: Annotated[
            SavedItineraryService,
            Depends(service_dependency),
        ],
        request: Request,
    ) -> SavedItineraryListResponse:
        try:
            response = await service.list(principal.uid)
        except ItineraryStoreError as error:
            _log_failure(request, operation="list", category="persistence")
            raise _unavailable() from error
        _log_success(
            request,
            operation="list",
            count=len(response.itineraries),
        )
        return response

    @router.get("/{itinerary_id}", response_model=SavedItineraryResponse)
    async def get_itinerary(
        itinerary_id: UUID,
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(authentication.required),
        ],
        service: Annotated[
            SavedItineraryService,
            Depends(service_dependency),
        ],
        request: Request,
    ) -> SavedItineraryResponse:
        try:
            response = await service.get(principal.uid, itinerary_id)
        except ItineraryNotFoundError as error:
            raise _not_found() from error
        except ItineraryStoreError as error:
            _log_failure(request, operation="get", category="persistence")
            raise _unavailable() from error
        _log_success(request, operation="get", count=1)
        return response

    @router.put("/{itinerary_id}", response_model=SavedItineraryResponse)
    async def replace_itinerary(
        itinerary_id: UUID,
        snapshot: ItineraryReplaceRequest,
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(authentication.required),
        ],
        service: Annotated[
            SavedItineraryService,
            Depends(service_dependency),
        ],
        request: Request,
    ) -> SavedItineraryResponse:
        try:
            response = await service.replace(
                principal.uid,
                itinerary_id,
                snapshot,
            )
        except ItineraryNotFoundError as error:
            raise _not_found() from error
        except ItineraryConflictError as error:
            _log_failure(request, operation="put", category="conflict")
            raise _conflict() from error
        except ItineraryStoreError as error:
            _log_failure(request, operation="put", category="persistence")
            raise _unavailable() from error
        _log_success(request, operation="put", count=len(response.items))
        return response

    @router.delete("/{itinerary_id}", response_model=ItineraryDeleteResponse)
    async def delete_itinerary(
        itinerary_id: UUID,
        command: ItineraryDeleteRequest,
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(authentication.required),
        ],
        service: Annotated[
            SavedItineraryService,
            Depends(service_dependency),
        ],
        request: Request,
    ) -> ItineraryDeleteResponse:
        try:
            response = await service.delete(
                principal.uid,
                itinerary_id,
                command.base_revision,
            )
        except ItineraryNotFoundError as error:
            raise _not_found() from error
        except ItineraryConflictError as error:
            _log_failure(request, operation="delete", category="conflict")
            raise _conflict() from error
        except ItineraryStoreError as error:
            _log_failure(
                request,
                operation="delete",
                category="persistence",
            )
            raise _unavailable() from error
        _log_success(request, operation="delete", count=0)
        return response

    return router


def _not_found() -> SavedItineraryHTTPException:
    return SavedItineraryHTTPException(
        status_code=404,
        code="itinerary_not_found",
        message="Itinerary not found.",
    )


def _conflict() -> SavedItineraryHTTPException:
    return SavedItineraryHTTPException(
        status_code=409,
        code="itinerary_conflict",
        message="The itinerary revision conflicts with current state.",
    )


def _unavailable() -> SavedItineraryHTTPException:
    return SavedItineraryHTTPException(
        status_code=503,
        code="itineraries_unavailable",
        message="Saved itineraries are temporarily unavailable.",
    )


def _log_success(request: Request, *, operation: str, count: int) -> None:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, "unavailable")
    logger.info(
        "operation=itinerary_%s request_id=%s result=success count=%d",
        operation,
        request_id,
        count,
    )


def _log_failure(
    request: Request,
    *,
    operation: str,
    category: str,
) -> None:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, "unavailable")
    logger.warning(
        "operation=itinerary_%s request_id=%s result=%s",
        operation,
        request_id,
        category,
    )
