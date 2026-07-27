"""Firebase-authenticated identity proof endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from app.auth.models import (
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
    InvalidAuthenticationTokenError,
)
from app.auth.verifier import FirebaseTokenVerifier

_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}
_bearer = HTTPBearer(
    auto_error=False,
    bearerFormat="Firebase ID token",
    scheme_name="FirebaseBearer",
)


class AuthMeResponse(BaseModel):
    """Minimal authenticated identity response."""

    model_config = ConfigDict(frozen=True)

    uid: str


class AuthenticationHTTPException(HTTPException):
    """Controlled authentication failure with a stable public code."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail=message,
            headers=headers,
        )
        self.code = code


def create_auth_router(verifier: FirebaseTokenVerifier) -> APIRouter:
    """Create a protected router bound to one verifier."""
    router = APIRouter()

    async def authenticated_principal(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(_bearer),
        ],
    ) -> AuthenticatedPrincipal:
        if (
            credentials is None
            or credentials.scheme.lower() != "bearer"
            or not credentials.credentials.strip()
            or any(character.isspace() for character in credentials.credentials)
        ):
            raise AuthenticationHTTPException(
                status_code=401,
                code="authentication_required",
                message="A valid Bearer authentication token is required.",
                headers=_BEARER_CHALLENGE,
            )

        try:
            return await verifier.verify_id_token(credentials.credentials)
        except InvalidAuthenticationTokenError as error:
            raise AuthenticationHTTPException(
                status_code=401,
                code="invalid_token",
                message="The authentication token is invalid.",
                headers=_BEARER_CHALLENGE,
            ) from error
        except AuthenticationServiceUnavailableError as error:
            raise AuthenticationHTTPException(
                status_code=503,
                code="authentication_unavailable",
                message="Authentication is temporarily unavailable.",
            ) from error

    PrincipalDependency = Annotated[
        AuthenticatedPrincipal,
        Depends(authenticated_principal),
    ]

    @router.get("/auth/me", response_model=AuthMeResponse)
    async def auth_me(principal: PrincipalDependency) -> AuthMeResponse:
        """Return only the UID established by successful verification."""
        return AuthMeResponse(uid=principal.uid)

    return router
