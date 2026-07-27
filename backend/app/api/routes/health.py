"""Unauthenticated service liveness endpoint."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.core.settings import ApplicationEnvironment, Settings


class HealthResponse(BaseModel):
    """Safe service metadata returned by the liveness check."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    service: str
    environment: ApplicationEnvironment
    version: str


def create_health_router(settings: Settings) -> APIRouter:
    """Create a router bound to one immutable settings instance."""
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Report process liveness without checking dependencies."""
        return HealthResponse(
            status="ok",
            service=settings.application_name,
            environment=settings.application_environment,
            version=settings.application_version,
        )

    return router
