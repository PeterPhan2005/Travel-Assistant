"""Deterministic HTTP tests for authenticated saved-itinerary CRUD."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from collections.abc import Callable
from typing import cast
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from app.auth.models import (
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
    InvalidAuthenticationTokenError,
)
from app.core.settings import ApplicationEnvironment, Settings
from app.itineraries import (
    ItineraryConflictError,
    ItineraryDeleteResponse,
    ItineraryNotFoundError,
    ItineraryReplaceRequest,
    ItineraryStore,
    SavedItineraryResponse,
    SavedItineraryService,
)
from app.main import create_app
from app.providers.poi.models import PoiDiscoveryRequest, PoiResultEnvelope

ITINERARY_ID = UUID("10000000-0000-4000-8000-000000000001")
ITEM_ONE_ID = "20000000-0000-4000-8000-000000000001"
ITEM_TWO_ID = "20000000-0000-4000-8000-000000000002"


class TokenVerifier:
    async def verify_id_token(self, raw_token: str) -> AuthenticatedPrincipal:
        if raw_token == "invalid":
            raise InvalidAuthenticationTokenError
        if raw_token == "unavailable":
            raise AuthenticationServiceUnavailableError
        return AuthenticatedPrincipal(uid=f"firebase-{raw_token}")


class UnusedPoiProvider:
    async def discover(
        self,
        request: PoiDiscoveryRequest,
    ) -> PoiResultEnvelope:
        del request
        raise AssertionError("POI provider must not be called")


class MemoryItineraryStore:
    def __init__(self) -> None:
        self.rows: dict[UUID, tuple[str, SavedItineraryResponse]] = {}
        self.tombstones: dict[UUID, tuple[str, int]] = {}

    async def list(self, firebase_uid: str) -> tuple[SavedItineraryResponse, ...]:
        return tuple(
            response
            for _, response in sorted(
                (
                    (response.local_date, response)
                    for owner, response in self.rows.values()
                    if owner == firebase_uid
                ),
                key=lambda value: (value[0], value[1].id),
                reverse=True,
            )
        )

    async def get(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
    ) -> SavedItineraryResponse | None:
        stored = self.rows.get(itinerary_id)
        return stored[1] if stored is not None and stored[0] == firebase_uid else None

    async def replace(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
        snapshot: ItineraryReplaceRequest,
    ) -> SavedItineraryResponse:
        tombstone = self.tombstones.get(itinerary_id)
        current = self.rows.get(itinerary_id)
        if tombstone is not None:
            if tombstone[0] != firebase_uid:
                raise ItineraryNotFoundError
            raise ItineraryConflictError
        if current is not None and current[0] != firebase_uid:
            raise ItineraryNotFoundError
        revision = 1 if current is None else current[1].revision + 1
        expected = 0 if current is None else current[1].revision
        if snapshot.base_revision != expected:
            raise ItineraryConflictError
        response = SavedItineraryResponse(
            id=itinerary_id,
            revision=revision,
            **snapshot.model_dump(exclude={"base_revision"}),
        )
        self.rows[itinerary_id] = (firebase_uid, response)
        return response

    async def delete(
        self,
        firebase_uid: str,
        itinerary_id: UUID,
        base_revision: int,
    ) -> ItineraryDeleteResponse:
        tombstone = self.tombstones.get(itinerary_id)
        current = self.rows.get(itinerary_id)
        if tombstone is not None:
            if tombstone[0] != firebase_uid:
                raise ItineraryNotFoundError
            if base_revision > tombstone[1]:
                raise ItineraryConflictError
            return ItineraryDeleteResponse(
                id=itinerary_id,
                revision=tombstone[1],
            )
        if current is not None and current[0] != firebase_uid:
            raise ItineraryNotFoundError
        expected = 0 if current is None else current[1].revision
        if base_revision != expected:
            raise ItineraryConflictError
        revision = expected + 1
        self.rows.pop(itinerary_id, None)
        self.tombstones[itinerary_id] = (firebase_uid, revision)
        return ItineraryDeleteResponse(id=itinerary_id, revision=revision)


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr(
            "postgresql+asyncpg://unused:never-connect@database.invalid/unused"
        ),
        firebase_project_id="travel-assistant-test",
        application_environment=ApplicationEnvironment.TEST,
    )


def _client(
    store: ItineraryStore | None = None,
    verifier: TokenVerifier | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            _settings(),
            token_verifier=verifier or TokenVerifier(),
            poi_provider=UnusedPoiProvider(),
            itinerary_store=store or MemoryItineraryStore(),
        )
    )


def _snapshot(*, base_revision: int = 0, title: str = "Một ngày ở Sài Gòn") -> dict[str, object]:
    return {
        "base_revision": base_revision,
        "title": title,
        "city": "hcmc",
        "local_date": "2026-08-03",
        "timezone": "Asia/Ho_Chi_Minh",
        "start_local_time": "09:00",
        "end_local_time": "17:00",
        "items": [
            {
                "id": ITEM_ONE_ID,
                "position": 0,
                "title": "Bưu điện Thành phố",
                "start_local_time": "09:00",
                "end_local_time": "12:00",
            },
            {
                "id": ITEM_TWO_ID,
                "position": 1,
                "title": "Bảo tàng Chứng tích Chiến tranh",
                "start_local_time": "13:00",
                "end_local_time": "17:00",
            },
        ],
        "assumptions": ["Đây là lịch trình nháp được chia theo khung giờ."],
        "warnings": [],
    }


def _auth(token: str = "one") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("token", "status", "code"),
    [
        (None, 401, "authentication_required"),
        ("invalid", 401, "invalid_token"),
        ("unavailable", 503, "authentication_unavailable"),
    ],
)
def test_private_routes_require_available_valid_authentication(
    token: str | None,
    status: int,
    code: str,
) -> None:
    headers = {} if token is None else _auth(token)
    with _client() as client:
        response = client.get("/v1/itineraries", headers=headers)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_create_get_list_replace_conflict_delete_and_tombstone() -> None:
    store = MemoryItineraryStore()
    with _client(store) as client:
        created = client.put(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth(),
            json=_snapshot(),
        )
        fetched = client.get(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth(),
        )
        listed = client.get("/v1/itineraries", headers=_auth())
        stale = client.put(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth(),
            json=_snapshot(base_revision=0, title="stale"),
        )
        replaced = client.put(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth(),
            json=_snapshot(base_revision=1, title="Bản mới"),
        )
        deleted = client.request(
            "DELETE",
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth(),
            json={"base_revision": 2},
        )
        stale_after_delete = client.put(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth(),
            json=_snapshot(base_revision=2),
        )

    assert created.status_code == 200
    assert created.json()["revision"] == 1
    assert created.json()["start_local_time"] == "09:00:00"
    assert [item["position"] for item in created.json()["items"]] == [0, 1]
    assert fetched.json() == created.json()
    assert listed.json() == {"itineraries": [created.json()]}
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "itinerary_conflict"
    assert replaced.status_code == 200
    assert replaced.json()["revision"] == 2
    assert replaced.json()["title"] == "Bản mới"
    assert deleted.json() == {
        "id": str(ITINERARY_ID),
        "revision": 3,
        "deleted": True,
    }
    assert stale_after_delete.status_code == 409


def test_cross_account_ids_are_non_enumerating_and_lists_are_isolated() -> None:
    store = MemoryItineraryStore()
    with _client(store) as client:
        assert client.put(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth("one"),
            json=_snapshot(),
        ).status_code == 200
        get_other = client.get(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth("two"),
        )
        put_other = client.put(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth("two"),
            json=_snapshot(),
        )
        delete_other = client.request(
            "DELETE",
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth("two"),
            json={"base_revision": 1},
        )
        other_list = client.get("/v1/itineraries", headers=_auth("two"))

    for response in (get_other, put_other, delete_other):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "itinerary_not_found"
    assert other_list.json() == {"itineraries": []}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: body.update({"uid": "forbidden"}),
        lambda body: body.update({"latitude": 10.7}),
        lambda body: body.update({"notes": "not persisted"}),
        lambda body: body.update({"timezone": "UTC"}),
        lambda body: body.update({"start_local_time": "17:00"}),
        lambda body: cast(list[dict[str, object]], body["items"])[1].update(
            {"position": 0}
        ),
        lambda body: cast(list[dict[str, object]], body["items"])[1].update(
            {"start_local_time": "11:00"}
        ),
    ],
)
def test_snapshot_validation_rejects_unknown_identity_location_notes_and_order(
    mutate: Callable[[dict[str, object]], None],
) -> None:
    body = deepcopy(_snapshot())
    mutate(body)
    with _client() as client:
        response = client.put(
            f"/v1/itineraries/{ITINERARY_ID}",
            headers=_auth(),
            json=body,
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_public_response_and_logs_omit_private_and_internal_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = "SENTINEL-ITINERARY-CONTENT"
    body = _snapshot(title=sentinel)
    with caplog.at_level(logging.INFO, logger="travel_assistant.api"):
        with _client() as client:
            response = client.put(
                f"/v1/itineraries/{ITINERARY_ID}",
                headers=_auth("private-token"),
                json=body,
            )
    public = response.text.lower()
    for forbidden in (
        "firebase_uid",
        "user_id",
        "authorization",
        "latitude",
        "longitude",
        "notes",
        "trace_id",
        "prompt",
        "model",
    ):
        assert forbidden not in public
    logs = caplog.text
    assert sentinel not in logs
    assert "private-token" not in logs
    assert "firebase-private-token" not in logs


def test_service_preserves_cancellation() -> None:
    class CancelledStore(MemoryItineraryStore):
        async def list(
            self,
            firebase_uid: str,
        ) -> tuple[SavedItineraryResponse, ...]:
            del firebase_uid
            raise asyncio.CancelledError

    service = SavedItineraryService(CancelledStore())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(service.list("firebase-one"))
