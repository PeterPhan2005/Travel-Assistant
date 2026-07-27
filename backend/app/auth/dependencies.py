"""Required and optional Firebase Bearer authentication dependencies."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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


class FirebaseAuthentication:
    """Authenticate supplied Firebase credentials without retaining them."""

    def __init__(self, verifier: FirebaseTokenVerifier) -> None:
        self._verifier = verifier

    async def required(
        self,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(_bearer),
        ],
    ) -> AuthenticatedPrincipal:
        """Require one valid Firebase Bearer token."""
        return await self._authenticate(credentials)

    async def optional(
        self,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(_bearer),
        ],
        authorization: Annotated[
            str | None,
            Header(alias="Authorization"),
        ] = None,
    ) -> AuthenticatedPrincipal | None:
        """Allow a missing header but strictly verify any supplied header."""
        if authorization is None:
            return None
        return await self._authenticate(credentials)

    async def _authenticate(
        self,
        credentials: HTTPAuthorizationCredentials | None,
    ) -> AuthenticatedPrincipal:
        if (
            credentials is None
            or credentials.scheme.lower() != "bearer"
            or not credentials.credentials.strip()
            or any(
                character.isspace()
                for character in credentials.credentials
            )
        ):
            raise _authentication_required()

        try:
            return await self._verifier.verify_id_token(
                credentials.credentials
            )
        except InvalidAuthenticationTokenError as error:
            raise _invalid_token() from error
        except AuthenticationServiceUnavailableError as error:
            raise _authentication_unavailable() from error


def _authentication_required() -> AuthenticationHTTPException:
    return AuthenticationHTTPException(
        status_code=401,
        code="authentication_required",
        message="A valid Bearer authentication token is required.",
        headers=_BEARER_CHALLENGE,
    )


def _invalid_token() -> AuthenticationHTTPException:
    return AuthenticationHTTPException(
        status_code=401,
        code="invalid_token",
        message="The authentication token is invalid.",
        headers=_BEARER_CHALLENGE,
    )


def _authentication_unavailable() -> AuthenticationHTTPException:
    return AuthenticationHTTPException(
        status_code=503,
        code="authentication_unavailable",
        message="Authentication is temporarily unavailable.",
    )
