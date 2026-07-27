"""FastAPI application factory."""

from fastapi import FastAPI

from app.api.routes.auth import create_auth_router
from app.api.routes.health import create_health_router
from app.auth.firebase_admin import FirebaseAdminTokenVerifier
from app.auth.verifier import FirebaseTokenVerifier
from app.core.errors import configure_error_logging, register_error_handlers
from app.core.settings import Settings
from app.middleware.request_id import RequestIdMiddleware


def create_app(
    settings: Settings | None = None,
    token_verifier: FirebaseTokenVerifier | None = None,
) -> FastAPI:
    """Build an independent application without starting external services."""
    resolved_settings = (
        settings
        if settings is not None
        else Settings()  # type: ignore[call-arg]
    )
    configure_error_logging(resolved_settings.log_level.value)
    resolved_token_verifier = (
        token_verifier
        if token_verifier is not None
        else FirebaseAdminTokenVerifier(resolved_settings.firebase_project_id)
    )

    app = FastAPI(
        title=resolved_settings.application_name,
        version=resolved_settings.application_version,
    )
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(create_health_router(resolved_settings))
    app.include_router(create_auth_router(resolved_token_verifier))
    return app
