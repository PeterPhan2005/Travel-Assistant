"""Transport-level privacy controls for sensitive URL query values."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RedactAccessLogQueryMiddleware:
    """Clear the query string only when the response reaches the server."""

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

        async def send_without_access_log_query(message: Message) -> None:
            if message["type"] == "http.response.start":
                scope["query_string"] = b""
            await send(message)

        await self.app(scope, receive, send_without_access_log_query)
