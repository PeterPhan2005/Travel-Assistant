"""Unit tests for the production Firebase Admin SDK adapter."""

import asyncio
from dataclasses import FrozenInstanceError
from typing import TypedDict, cast

import firebase_admin  # type: ignore[import-untyped]
import pytest
from firebase_admin import App, auth
from google.auth import exceptions as google_auth_exceptions

from app.auth.firebase_admin import (
    MAX_FIREBASE_UID_LENGTH,
    FirebaseAdminTokenVerifier,
)
from app.auth.models import (
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
    InvalidAuthenticationTokenError,
)

TEST_PROJECT_ID = "travel-assistant-test"
SENTINEL_TOKEN = "adapter-sentinel-token-NEVER-STORE"


class InitializationCall(TypedDict):
    options: dict[str, object] | None
    name: str


class VerificationCall(TypedDict):
    token: str
    app: App | None
    check_revoked: bool
    clock_skew_seconds: int


def test_verifier_uses_project_scoped_app_and_checks_revocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    firebase_app = cast(App, object())
    initialization_calls: list[InitializationCall] = []
    verification_calls: list[VerificationCall] = []

    def initialize_app(
        credential: object | None = None,
        options: dict[str, object] | None = None,
        name: str = "[DEFAULT]",
    ) -> App:
        assert credential is None
        initialization_calls.append({"options": options, "name": name})
        return firebase_app

    def verify_id_token(
        id_token: str,
        app: App | None = None,
        check_revoked: bool = False,
        clock_skew_seconds: int = 0,
    ) -> dict[str, object]:
        verification_calls.append(
            {
                "token": id_token,
                "app": app,
                "check_revoked": check_revoked,
                "clock_skew_seconds": clock_skew_seconds,
            }
        )
        return {"uid": "firebase-user-123", "email": "not-exposed@example.com"}

    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)
    monkeypatch.setattr(auth, "verify_id_token", verify_id_token)
    verifier = FirebaseAdminTokenVerifier(TEST_PROJECT_ID)

    first_principal = asyncio.run(verifier.verify_id_token(SENTINEL_TOKEN))
    second_principal = asyncio.run(verifier.verify_id_token("second-token"))

    assert first_principal == AuthenticatedPrincipal(uid="firebase-user-123")
    assert second_principal == AuthenticatedPrincipal(uid="firebase-user-123")
    assert initialization_calls == [
        {
            "options": {"projectId": TEST_PROJECT_ID},
            "name": initialization_calls[0]["name"],
        }
    ]
    assert initialization_calls[0]["name"].startswith("travel-assistant-")
    assert verification_calls == [
        {
            "token": SENTINEL_TOKEN,
            "app": firebase_app,
            "check_revoked": True,
            "clock_skew_seconds": 0,
        },
        {
            "token": "second-token",
            "app": firebase_app,
            "check_revoked": True,
            "clock_skew_seconds": 0,
        },
    ]
    assert SENTINEL_TOKEN not in repr(verifier)
    assert all(
        stored_value != SENTINEL_TOKEN
        for stored_value in vars(verifier).values()
    )

    with pytest.raises(FrozenInstanceError):
        first_principal.uid = "mutated"  # type: ignore[misc]


@pytest.mark.parametrize(
    "decoded_token",
    [
        {},
        {"uid": 123},
        {"uid": ""},
        {"uid": "   "},
        {"uid": "u" * (MAX_FIREBASE_UID_LENGTH + 1)},
    ],
)
def test_invalid_decoded_uid_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    decoded_token: dict[str, object],
) -> None:
    firebase_app = cast(App, object())

    def initialize_app(
        credential: object | None = None,
        options: dict[str, object] | None = None,
        name: str = "[DEFAULT]",
    ) -> App:
        del credential, options, name
        return firebase_app

    def verify_id_token(
        id_token: str,
        app: App | None = None,
        check_revoked: bool = False,
        clock_skew_seconds: int = 0,
    ) -> dict[str, object]:
        del id_token, app, check_revoked, clock_skew_seconds
        return decoded_token

    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)
    monkeypatch.setattr(auth, "verify_id_token", verify_id_token)

    with pytest.raises(InvalidAuthenticationTokenError):
        asyncio.run(
            FirebaseAdminTokenVerifier(TEST_PROJECT_ID).verify_id_token(
                SENTINEL_TOKEN
            )
        )


@pytest.mark.parametrize(
    "sdk_error",
    [
        auth.InvalidIdTokenError("invalid"),
        auth.ExpiredIdTokenError("expired", ValueError("cause")),
        auth.RevokedIdTokenError("revoked"),
        auth.UserDisabledError("disabled"),
        auth.UserNotFoundError("deleted"),
        ValueError("malformed"),
    ],
)
def test_expected_invalid_sdk_failures_are_normalized(
    monkeypatch: pytest.MonkeyPatch,
    sdk_error: Exception,
) -> None:
    firebase_app = cast(App, object())

    def initialize_app(
        credential: object | None = None,
        options: dict[str, object] | None = None,
        name: str = "[DEFAULT]",
    ) -> App:
        del credential, options, name
        return firebase_app

    def verify_id_token(
        id_token: str,
        app: App | None = None,
        check_revoked: bool = False,
        clock_skew_seconds: int = 0,
    ) -> dict[str, object]:
        del id_token, app, check_revoked, clock_skew_seconds
        raise sdk_error

    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)
    monkeypatch.setattr(auth, "verify_id_token", verify_id_token)

    with pytest.raises(InvalidAuthenticationTokenError) as error:
        asyncio.run(
            FirebaseAdminTokenVerifier(TEST_PROJECT_ID).verify_id_token(
                SENTINEL_TOKEN
            )
        )

    assert SENTINEL_TOKEN not in str(error.value)


@pytest.mark.parametrize(
    "sdk_error",
    [
        auth.CertificateFetchError("certificates unavailable", OSError()),
        auth.InsufficientPermissionError(
            "permission denied",
            ValueError("cause"),
            None,
        ),
        firebase_admin.exceptions.InvalidArgumentError(
            "provider project mismatch",
        ),
        firebase_admin.exceptions.FirebaseError(
            "provider_failure",
            "provider configuration unavailable",
        ),
        firebase_admin.exceptions.UnavailableError("network unavailable"),
        google_auth_exceptions.TransportError("ADC transport unavailable"),
    ],
)
def test_sdk_unavailability_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
    sdk_error: Exception,
) -> None:
    firebase_app = cast(App, object())

    def initialize_app(
        credential: object | None = None,
        options: dict[str, object] | None = None,
        name: str = "[DEFAULT]",
    ) -> App:
        del credential, options, name
        return firebase_app

    def verify_id_token(
        id_token: str,
        app: App | None = None,
        check_revoked: bool = False,
        clock_skew_seconds: int = 0,
    ) -> dict[str, object]:
        del id_token, app, check_revoked, clock_skew_seconds
        raise sdk_error

    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)
    monkeypatch.setattr(auth, "verify_id_token", verify_id_token)

    with pytest.raises(AuthenticationServiceUnavailableError) as error:
        asyncio.run(
            FirebaseAdminTokenVerifier(TEST_PROJECT_ID).verify_id_token(
                SENTINEL_TOKEN
            )
        )

    assert SENTINEL_TOKEN not in str(error.value)


@pytest.mark.parametrize(
    "initialization_error",
    [
        google_auth_exceptions.DefaultCredentialsError(  # type: ignore[no-untyped-call]
            "credential unavailable",
        ),
        firebase_admin.exceptions.InvalidArgumentError(
            "project configuration mismatch",
        ),
        ValueError("invalid Firebase app configuration"),
    ],
)
def test_firebase_initialization_failure_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    initialization_error: Exception,
) -> None:
    def initialize_app(
        credential: object | None = None,
        options: dict[str, object] | None = None,
        name: str = "[DEFAULT]",
    ) -> App:
        del credential, options, name
        raise initialization_error

    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)

    with pytest.raises(AuthenticationServiceUnavailableError):
        asyncio.run(
            FirebaseAdminTokenVerifier(TEST_PROJECT_ID).verify_id_token(
                SENTINEL_TOKEN
            )
        )


def test_cancellation_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    firebase_app = cast(App, object())

    def initialize_app(
        credential: object | None = None,
        options: dict[str, object] | None = None,
        name: str = "[DEFAULT]",
    ) -> App:
        del credential, options, name
        return firebase_app

    def verify_id_token(
        id_token: str,
        app: App | None = None,
        check_revoked: bool = False,
        clock_skew_seconds: int = 0,
    ) -> dict[str, object]:
        del id_token, app, check_revoked, clock_skew_seconds
        raise asyncio.CancelledError

    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)
    monkeypatch.setattr(auth, "verify_id_token", verify_id_token)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            FirebaseAdminTokenVerifier(TEST_PROJECT_ID).verify_id_token(
                SENTINEL_TOKEN
            )
        )
