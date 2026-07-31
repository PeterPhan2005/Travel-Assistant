"""Authenticated assistant HTTP transport boundary."""

from app.assistant.contracts import (
    AssistantQueryRequest,
    AssistantQueryResponse,
)

__all__ = ["AssistantQueryRequest", "AssistantQueryResponse"]
