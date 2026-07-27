"""Public error models and FastAPI exception handlers."""

import logging
from collections.abc import Mapping, Sequence
from typing import TypeAlias

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException

from app.middleware.request_id import (
    REQUEST_ID_HEADER,
    REQUEST_ID_STATE_KEY,
    new_request_id,
)

logger = logging.getLogger("travel_assistant.api")

ErrorLocationItem: TypeAlias = str | int


class ValidationIssue(BaseModel):
    """Sanitized location and category for an invalid request value."""

    model_config = ConfigDict(frozen=True)

    location: list[ErrorLocationItem]
    message: str
    type: str


class ErrorDetail(BaseModel):
    """Stable public error payload."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    request_id: str
    details: list[ValidationIssue] | None = None


class ErrorEnvelope(BaseModel):
    """Top-level JSON error contract."""

    model_config = ConfigDict(frozen=True)

    error: ErrorDetail


_HTTP_ERROR_DEFAULTS: Mapping[int, tuple[str, str]] = {
    400: ("bad_request", "Bad request."),
    401: ("unauthorized", "Authentication is required."),
    403: ("forbidden", "Access is forbidden."),
    404: ("not_found", "Resource not found."),
    405: ("method_not_allowed", "Method not allowed."),
    409: ("conflict", "Request conflicts with the current state."),
    422: ("validation_error", "Request validation failed."),
    429: ("too_many_requests", "Too many requests."),
}


def configure_error_logging(log_level: str) -> None:
    """Configure only the application logger without logging configuration."""
    logger.setLevel(log_level)


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, None)
    if isinstance(request_id, str):
        return request_id

    generated_request_id = new_request_id()
    setattr(request.state, REQUEST_ID_STATE_KEY, generated_request_id)
    return generated_request_id


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ValidationIssue] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    response_headers = dict(headers or {})
    response_headers[REQUEST_ID_HEADER] = request_id
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
        headers=response_headers,
    )


async def http_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Normalize controlled Starlette and FastAPI HTTP errors."""
    if not isinstance(exception, HTTPException):
        return await unexpected_exception_handler(request, exception)

    code, default_message = _HTTP_ERROR_DEFAULTS.get(
        exception.status_code,
        ("http_error", "The request could not be completed."),
    )
    message = (
        exception.detail
        if isinstance(exception.detail, str)
        and exception.detail not in {"Not Found", "Method Not Allowed"}
        else default_message
    )
    return _error_response(
        request=request,
        status_code=exception.status_code,
        code=code,
        message=message,
        headers=exception.headers,
    )


async def request_validation_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Return sanitized field locations without reflecting invalid inputs."""
    if not isinstance(exception, RequestValidationError):
        return await unexpected_exception_handler(request, exception)

    issues = [
        ValidationIssue(
            location=_validation_location(error.get("loc")),
            message="Invalid value.",
            type=_validation_type(error.get("type")),
        )
        for error in exception.errors()
    ]
    return _error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        details=issues,
    )


async def unexpected_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Hide internal exception data behind a stable generic response."""
    del exception
    request_id = _request_id(request)
    logger.error("Unhandled application error request_id=%s", request_id)
    return _error_response(
        request=request,
        status_code=500,
        code="internal_error",
        message="An internal server error occurred.",
    )


def _validation_location(value: object) -> list[ErrorLocationItem]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item for item in value if isinstance(item, (str, int))]


def _validation_type(value: object) -> str:
    return value if isinstance(value, str) else "validation_error"


def register_error_handlers(app: FastAPI) -> None:
    """Install the complete JSON error contract on an app instance."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )
    app.add_exception_handler(Exception, unexpected_exception_handler)
