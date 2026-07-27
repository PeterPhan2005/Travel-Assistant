"""Replaceable Firebase ID-token verification boundary."""

from typing import Protocol

from app.auth.models import AuthenticatedPrincipal


class FirebaseTokenVerifier(Protocol):
    """Verify one raw Firebase ID token and return only its trusted UID."""

    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        """Verify a Firebase ID token without retaining it."""
        ...
