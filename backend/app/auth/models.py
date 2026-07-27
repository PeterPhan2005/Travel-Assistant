"""Application-facing authentication models and failures."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """The only verified Firebase identity exposed to application code."""

    uid: str


class InvalidAuthenticationTokenError(Exception):
    """The supplied credential is not a valid, active Firebase ID token."""


class AuthenticationServiceUnavailableError(Exception):
    """Firebase verification cannot currently make a trustworthy decision."""
