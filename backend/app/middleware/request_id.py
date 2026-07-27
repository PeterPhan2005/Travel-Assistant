"""Request correlation ID validation and propagation."""

import re
from typing import TypedDict, cast
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_STATE_KEY = "request_id"
MAX_REQUEST_ID_LENGTH = 128
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class RequestState(TypedDict, total=False):
    """Request-scoped values stored on the ASGI HTTP scope."""

    request_id: str


def new_request_id() -> str:
    """Generate a UUID-based request ID."""
    return str(uuid4())


def normalize_request_id(candidate: str | None) -> str:
    """Preserve a safe caller ID or replace it with a generated UUID."""
    if (
        candidate is None
        or len(candidate) > MAX_REQUEST_ID_LENGTH
        or _VALID_REQUEST_ID.fullmatch(candidate) is None
    ):
        return new_request_id()
    return candidate


class RequestIdMiddleware:
    """Attach one validated request ID to every HTTP request and response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = normalize_request_id(
            Headers(scope=scope).get(REQUEST_ID_HEADER)
        )
        state = cast(RequestState, scope.setdefault("state", {}))
        state["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)
