"""FastAPI application factory."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents.composer.service import ResponseComposerService
from app.agents.discovery.menu import SqlAlchemyPoiMenuReader
from app.agents.discovery.service import DiscoveryService
from app.agents.grounding.service import GroundingReviewerService
from app.agents.itinerary.service import ItineraryService
from app.agents.local_culture.service import LocalCultureService
from app.agents.narration.service import NarrationService
from app.agents.orchestration import (
    AgentOrchestrator,
    AgentOrchestratorService,
)
from app.agents.router.service import RouterService
from app.api.routes.assistant import create_assistant_router
from app.api.routes.auth import create_auth_router
from app.api.routes.health import create_health_router
from app.api.routes.itinerary_drafts import create_itinerary_drafts_router
from app.api.routes.itineraries import create_itineraries_router
from app.api.routes.pois import create_pois_router
from app.api.routes.preferences import create_preferences_router
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
from app.itinerary_generation import (
    StructuredItineraryGenerationService,
    StructuredItineraryGenerator,
)
from app.itinerary_generation.candidates import (
    DefaultItineraryCandidateResolver,
    SqlAlchemyCuratedCityCandidateReader,
)
from app.itineraries import (
    ItineraryStore,
    SavedItineraryService,
    SqlAlchemyItineraryStore,
)
from app.preferences.service import PreferenceService
from app.preferences.store import (
    PreferenceStore,
    SqlAlchemyPreferenceStore,
)


def create_app(
    settings: Settings | None = None,
    token_verifier: FirebaseTokenVerifier | None = None,
    poi_provider: PoiProvider | None = None,
    preference_store: PreferenceStore | None = None,
    assistant_orchestrator: AgentOrchestrator | None = None,
    itinerary_generator: StructuredItineraryGenerator | None = None,
    itinerary_store: ItineraryStore | None = None,
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
    database_runtime_lock = asyncio.Lock()

    async def ensure_database_runtime() -> DatabaseRuntime:
        nonlocal database_runtime
        if database_runtime is not None:
            return database_runtime
        async with database_runtime_lock:
            if database_runtime is None:
                database_runtime = create_database_runtime(
                    resolved_settings.database_url.get_secret_value()
                )
            return database_runtime

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        del app
        nonlocal database_runtime
        if poi_provider is None:
            await ensure_database_runtime()
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
        runtime = await ensure_database_runtime()
        async with runtime.session_factory() as session:
            yield CuratedPoiProvider(session)

    async def request_preference_service() -> AsyncIterator[
        PreferenceService
    ]:
        if preference_store is not None:
            yield PreferenceService(preference_store)
            return
        runtime = await ensure_database_runtime()
        async with runtime.session_factory() as session:
            yield PreferenceService(SqlAlchemyPreferenceStore(session))

    async def request_assistant_orchestrator() -> AsyncIterator[
        AgentOrchestrator
    ]:
        if assistant_orchestrator is not None:
            yield assistant_orchestrator
            return
        runtime = await ensure_database_runtime()
        async with runtime.session_factory() as session:
            provider = CuratedPoiProvider(session)
            yield AgentOrchestratorService(
                router=RouterService(),
                discovery=DiscoveryService(
                    provider,
                    SqlAlchemyPoiMenuReader(session),
                ),
                narration=NarrationService(),
                local_culture=LocalCultureService(),
                itinerary=ItineraryService(),
                grounding=GroundingReviewerService(),
                composer=ResponseComposerService(),
            )

    async def request_itinerary_generator() -> AsyncIterator[
        StructuredItineraryGenerator
    ]:
        if itinerary_generator is not None:
            yield itinerary_generator
            return
        runtime = await ensure_database_runtime()
        async with runtime.session_factory() as session:
            provider = CuratedPoiProvider(session)
            menu_reader = SqlAlchemyPoiMenuReader(session)
            yield StructuredItineraryGenerationService(
                DefaultItineraryCandidateResolver(
                    DiscoveryService(provider, menu_reader),
                    SqlAlchemyCuratedCityCandidateReader(session),
                    menu_reader,
                ),
                ItineraryService(),
            )

    async def request_saved_itinerary_service() -> AsyncIterator[
        SavedItineraryService
    ]:
        if itinerary_store is not None:
            yield SavedItineraryService(itinerary_store)
            return
        runtime = await ensure_database_runtime()
        async with runtime.session_factory() as session:
            yield SavedItineraryService(SqlAlchemyItineraryStore(session))

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
        create_assistant_router(
            request_assistant_orchestrator,
            authentication,
            request_preference_service,
        )
    )
    app.include_router(
        create_preferences_router(
            request_preference_service,
            authentication,
        )
    )
    app.include_router(
        create_itinerary_drafts_router(
            request_itinerary_generator,
            authentication,
        )
    )
    app.include_router(
        create_itineraries_router(
            request_saved_itinerary_service,
            authentication,
        )
    )
    app.include_router(
        create_pois_router(request_poi_provider, authentication)
    )
    return app
