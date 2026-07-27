"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.auth import create_auth_router
from app.api.routes.health import create_health_router
from app.api.routes.pois import create_pois_router
from app.auth.dependencies import FirebaseAuthentication
from app.auth.firebase_admin import FirebaseAdminTokenVerifier
from app.auth.verifier import FirebaseTokenVerifier
from app.core.errors import configure_error_logging, register_error_handlers
from app.core.settings import Settings
from app.db.runtime import DatabaseRuntime, create_database_runtime
from app.middleware.privacy import RedactAccessLogQueryMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.providers.poi.contracts import PoiProvider
from app.providers.poi.curated import CuratedPoiProvider


def create_app(
    settings: Settings | None = None,
    token_verifier: FirebaseTokenVerifier | None = None,
    poi_provider: PoiProvider | None = None,
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
    authentication = FirebaseAuthentication(resolved_token_verifier)
    database_runtime: DatabaseRuntime | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        del app
        nonlocal database_runtime
        if poi_provider is None:
            database_runtime = create_database_runtime(
                resolved_settings.database_url.get_secret_value()
            )
        try:
            yield
        finally:
            if database_runtime is not None:
                await database_runtime.dispose()
                database_runtime = None

    async def request_poi_provider() -> AsyncIterator[PoiProvider]:
        if poi_provider is not None:
            yield poi_provider
            return
        if database_runtime is None:
            raise RuntimeError("Database runtime is not available.")
        async with database_runtime.session_factory() as session:
            yield CuratedPoiProvider(session)

    app = FastAPI(
        title=resolved_settings.application_name,
        version=resolved_settings.application_version,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RedactAccessLogQueryMiddleware)
    register_error_handlers(app)
    app.include_router(create_health_router(resolved_settings))
    app.include_router(create_auth_router(authentication))
    app.include_router(
        create_pois_router(request_poi_provider, authentication)
    )
    return app
