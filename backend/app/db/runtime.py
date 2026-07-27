"""Per-application async database runtime for HTTP request sessions."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(frozen=True, slots=True)
class DatabaseRuntime:
    """Own one app engine and its request-scoped session factory."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    async def dispose(self) -> None:
        """Release the app-owned connection pool on shutdown."""
        await self.engine.dispose()


def create_database_runtime(database_url: str) -> DatabaseRuntime:
    """Create lazy-connect SQLAlchemy resources for one running app."""
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return DatabaseRuntime(
        engine=engine,
        session_factory=async_sessionmaker(
            engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        ),
    )
