"""Firebase-authenticated identity proof endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.auth.dependencies import FirebaseAuthentication
from app.auth.models import AuthenticatedPrincipal


class AuthMeResponse(BaseModel):
    """Minimal authenticated identity response."""

    model_config = ConfigDict(frozen=True)

    uid: str


def create_auth_router(authentication: FirebaseAuthentication) -> APIRouter:
    """Create a protected router bound to one verifier."""
    router = APIRouter()

    PrincipalDependency = Annotated[
        AuthenticatedPrincipal,
        Depends(authentication.required),
    ]

    @router.get("/auth/me", response_model=AuthMeResponse)
    async def auth_me(principal: PrincipalDependency) -> AuthMeResponse:
        """Return only the UID established by successful verification."""
        return AuthMeResponse(uid=principal.uid)

    return router
