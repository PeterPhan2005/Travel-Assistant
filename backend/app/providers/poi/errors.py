"""Stable provider-neutral POI failure taxonomy."""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, model_validator

from app.providers.poi.models import PoiProviderKind


class ProviderErrorCode(StrEnum):
    """Failures that later HTTP/application layers may map safely."""

    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"
    MISCONFIGURED = "misconfigured"
    UNSUPPORTED = "unsupported"
    INTERNAL = "internal"


_ERROR_DEFAULTS: dict[ProviderErrorCode, tuple[str, bool]] = {
    ProviderErrorCode.TIMEOUT: ("Provider operation timed out.", True),
    ProviderErrorCode.UNAVAILABLE: (
        "Provider is temporarily unavailable.",
        True,
    ),
    ProviderErrorCode.RATE_LIMITED: (
        "Provider rate limit was reached.",
        True,
    ),
    ProviderErrorCode.INVALID_REQUEST: (
        "Provider rejected the normalized request.",
        False,
    ),
    ProviderErrorCode.INVALID_RESPONSE: (
        "Provider returned an invalid normalized response.",
        False,
    ),
    ProviderErrorCode.MISCONFIGURED: (
        "Provider is not configured.",
        False,
    ),
    ProviderErrorCode.UNSUPPORTED: (
        "Provider does not support this operation.",
        False,
    ),
    ProviderErrorCode.INTERNAL: (
        "Provider operation failed.",
        False,
    ),
}


class ProviderFailure(BaseModel):
    """Sanitized failure details carried by ``PoiProviderError``."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    provider: PoiProviderKind
    code: ProviderErrorCode
    message: str
    retryable: bool

    @classmethod
    def for_code(
        cls,
        provider: PoiProviderKind,
        code: ProviderErrorCode,
    ) -> ProviderFailure:
        """Create the one canonical public shape for a failure code."""
        message, retryable = _ERROR_DEFAULTS[code]
        return cls(
            provider=provider,
            code=code,
            message=message,
            retryable=retryable,
        )

    @model_validator(mode="after")
    def require_canonical_public_values(self) -> ProviderFailure:
        """Reject arbitrary detail that could expose an internal exception."""
        expected_message, expected_retryable = _ERROR_DEFAULTS[self.code]
        if self.message != expected_message or self.retryable is not expected_retryable:
            raise ValueError("Provider failure details must be canonical.")
        return self


class PoiProviderError(Exception):
    """The only adapter failure exposed through the provider protocol."""

    __slots__ = ("failure",)

    def __init__(self, failure: ProviderFailure) -> None:
        self.failure = failure
        super().__init__(failure.code.value)
