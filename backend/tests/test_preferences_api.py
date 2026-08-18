"""Deterministic HTTP tests for the private preference resource."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from app.auth.models import (
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.main import create_app
from app.preferences.contracts import (
    SupportedPreferenceDocument,
)
from app.preferences.store import (
    PreferenceSchemaConflictError,
    PreferenceStoreError,
    StoredPreference,
)

TEST_DATABASE_URL = "postgresql+asyncpg://unused:unused@localhost/unused"
TEST_FIREBASE_PROJECT_ID = "travel-assistant-test"
PRIVATE_UID = "private-firebase-owner"
PRIVATE_VALUE = "Nội dung riêng tư không được log"


class TokenVerifier:
    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(uid=f"owner-{raw_token}")


class UnavailableTokenVerifier:
    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        raise AuthenticationServiceUnavailableError(
            "InvalidArgumentError project=private-project "
            "credential=/private/adc.json "
            "url=https://identitytoolkit.googleapis.com/v1/accounts:lookup "
            f"uid={PRIVATE_UID} token={raw_token}"
        )


class MemoryPreferenceStore:
    def __init__(self) -> None:
        self.records: dict[str, StoredPreference] = {}
        self.get_calls = 0
        self.replace_calls = 0

    async def get(self, firebase_uid: str) -> StoredPreference | None:
        self.get_calls += 1
        return self.records.get(firebase_uid)

    async def replace(
        self,
        firebase_uid: str,
        document: SupportedPreferenceDocument,
    ) -> StoredPreference:
        self.replace_calls += 1
        existing = self.records.get(firebase_uid)
        if (
            existing is not None
            and existing.schema_version > document.schema_version
        ):
            raise PreferenceSchemaConflictError
        record = StoredPreference(
            schema_version=document.schema_version,
            preferences=document.model_dump(mode="json")["preferences"],
            updated_at=datetime.now(timezone.utc),
        )
        self.records[firebase_uid] = record
        return record


class FailingPreferenceStore(MemoryPreferenceStore):
    async def get(self, firebase_uid: str) -> StoredPreference | None:
        del firebase_uid
        raise PreferenceStoreError

    async def replace(
        self,
        firebase_uid: str,
        document: SupportedPreferenceDocument,
    ) -> StoredPreference:
        del firebase_uid, document
        raise PreferenceStoreError


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr(TEST_DATABASE_URL),
        firebase_project_id=TEST_FIREBASE_PROJECT_ID,
        application_environment=ApplicationEnvironment.TEST,
    )


def _client(
    store: MemoryPreferenceStore,
    verifier: TokenVerifier | UnavailableTokenVerifier | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            _settings(),
            token_verifier=verifier or TokenVerifier(),
            preference_store=store,
        ),
        raise_server_exceptions=False,
    )


def _headers(token: str = "one") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_and_put_require_authentication_without_touching_store() -> None:
    store = MemoryPreferenceStore()
    with _client(store) as client:
        get_response = client.get("/preferences")
        put_response = client.put(
            "/preferences",
            json={"schema_version": 1, "preferences": {}},
        )

    assert get_response.status_code == 401
    assert put_response.status_code == 401
    assert store.get_calls == 0
    assert store.replace_calls == 0


def test_authentication_provider_failure_uses_shared_sanitized_503(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request_id = "preference-auth-unavailable"
    private_token = "private-preference-token"
    store = MemoryPreferenceStore()
    caplog.set_level(logging.DEBUG)
    with _client(store, UnavailableTokenVerifier()) as client:
        response = client.get(
            "/preferences",
            headers={
                "Authorization": f"Bearer {private_token}",
                "X-Request-ID": request_id,
            },
        )

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["error"] == {
        "code": "authentication_unavailable",
        "message": "Authentication is temporarily unavailable.",
        "request_id": request_id,
        "details": None,
    }
    assert store.get_calls == 0
    assert store.replace_calls == 0
    combined_logs = "\n".join(
        record.getMessage() for record in caplog.records
    )
    for private_value in (
        "InvalidArgumentError",
        "private-project",
        "/private/adc.json",
        "accounts:lookup",
        PRIVATE_UID,
        private_token,
        "Authorization",
    ):
        assert private_value not in response.text
        assert private_value not in combined_logs


def test_missing_row_returns_canonical_empty_document_without_write() -> None:
    store = MemoryPreferenceStore()
    with _client(store) as client:
        response = client.get("/preferences", headers=_headers())

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": 1,
        "preferences": {},
        "updated_at": None,
    }
    assert store.records == {}
    assert store.replace_calls == 0


def test_put_replaces_complete_document_and_never_exposes_owner() -> None:
    store = MemoryPreferenceStore()
    with _client(store) as client:
        first = client.put(
            "/preferences",
            headers=_headers(),
            json={
                "schema_version": 1,
                "preferences": {
                    "first": PRIVATE_VALUE,
                    "removed_later": True,
                },
            },
        )
        second = client.put(
            "/preferences",
            headers=_headers(),
            json={
                "schema_version": 1,
                "preferences": {"second": 2},
            },
        )
        fetched = client.get("/preferences", headers=_headers())

    assert first.status_code == 200
    assert second.status_code == 200
    assert fetched.json()["preferences"] == {"second": 2}
    assert "removed_later" not in fetched.text
    assert "uid" not in fetched.json()
    assert "user_id" not in fetched.json()
    assert PRIVATE_UID not in fetched.text
    assert datetime.fromisoformat(
        fetched.json()["updated_at"].replace("Z", "+00:00")
    ).tzinfo is not None


def test_schema_v2_replaces_legacy_and_legacy_cannot_downgrade_it() -> None:
    store = MemoryPreferenceStore()
    typed_payload = {
        "schema_version": 2,
        "preferences": {
            "interests": ["culture_and_history", "food_and_cafes"],
            "pace": "relaxed",
            "budget_preference": "budget",
        },
    }
    with _client(store) as client:
        legacy = client.put(
            "/preferences",
            headers=_headers(),
            json={"schema_version": 1, "preferences": {"legacy": True}},
        )
        typed = client.put(
            "/preferences",
            headers=_headers(),
            json=typed_payload,
        )
        downgrade = client.put(
            "/preferences",
            headers=_headers(),
            json={"schema_version": 1, "preferences": {}},
        )
        fetched = client.get("/preferences", headers=_headers())

    assert legacy.status_code == 200
    assert typed.status_code == 200
    assert typed.json()["preferences"]["interests"] == [
        "food_and_cafes",
        "culture_and_history",
    ]
    assert downgrade.status_code == 409
    assert downgrade.json()["error"]["code"] == "preference_schema_conflict"
    assert fetched.json()["schema_version"] == 2
    assert fetched.json()["preferences"] == typed.json()["preferences"]


def test_explicit_reset_is_a_canonical_schema_v2_full_replacement() -> None:
    store = MemoryPreferenceStore()
    with _client(store) as client:
        response = client.put(
            "/preferences",
            headers=_headers(),
            json={
                "schema_version": 2,
                "preferences": {
                    "interests": [],
                    "pace": None,
                    "budget_preference": None,
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["preferences"] == {
        "interests": [],
        "pace": None,
        "budget_preference": None,
    }


def test_two_authenticated_owners_are_isolated() -> None:
    store = MemoryPreferenceStore()
    with _client(store) as client:
        client.put(
            "/preferences",
            headers=_headers("one"),
            json={
                "schema_version": 1,
                "preferences": {"account": "one"},
            },
        )
        client.put(
            "/preferences",
            headers=_headers("two"),
            json={
                "schema_version": 1,
                "preferences": {"account": "two"},
            },
        )
        first = client.get("/preferences", headers=_headers("one"))
        second = client.get("/preferences", headers=_headers("two"))

    assert first.json()["preferences"] == {"account": "one"}
    assert second.json()["preferences"] == {"account": "two"}
    assert len(store.records) == 2


def test_invalid_envelopes_use_sanitized_standard_validation_error() -> None:
    store = MemoryPreferenceStore()
    invalid_payloads = [
        {"schema_version": 2, "preferences": {}},
        {"schema_version": 1, "preferences": {}, "unknown": True},
        {
            "schema_version": 1,
            "preferences": {PRIVATE_VALUE: 1.2},
        },
    ]
    with _client(store) as client:
        responses = [
            client.put("/preferences", headers=_headers(), json=payload)
            for payload in invalid_payloads
        ]

    assert store.replace_calls == 0
    for response in responses:
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert PRIVATE_VALUE not in response.text


def test_database_failure_is_sanitized_with_consistent_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request_id = "preference-failure-test"
    caplog.set_level(logging.ERROR, logger="travel_assistant.api")
    with _client(FailingPreferenceStore()) as client:
        response = client.get(
            "/preferences",
            headers={**_headers(PRIVATE_UID), "X-Request-ID": request_id},
        )

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["error"] == {
        "code": "preferences_unavailable",
        "message": "Preferences are temporarily unavailable.",
        "request_id": request_id,
        "details": None,
    }
    combined_logs = caplog.text
    assert PRIVATE_UID not in combined_logs
    assert PRIVATE_VALUE not in combined_logs
    assert "Bearer" not in combined_logs
