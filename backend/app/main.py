"""FastAPI application factory."""

from fastapi import FastAPI

from app.api.routes.health import create_health_router
from app.core.errors import configure_error_logging, register_error_handlers
from app.core.settings import Settings
from app.middleware.request_id import RequestIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an independent application without starting external services."""
    resolved_settings = (
        settings
        if settings is not None
        else Settings()  # type: ignore[call-arg]
    )
    configure_error_logging(resolved_settings.log_level.value)

    app = FastAPI(
        title=resolved_settings.application_name,
        version=resolved_settings.application_version,
    )
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(create_health_router(resolved_settings))
    return app
