"""
Dependency injection for FastAPI routes.
Provides: database sessions, auth, workspace scope.
Spec: docs/plans/phase-0-scaffold.md
"""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.
    Yields a database session and ensures it's closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_llm_router(request: Request):
    """
    LLM Router dependency (AX.11).
    Returns the singleton LLM router instance from app state.
    Note: For WebSocket endpoints, access websocket.app.state.llm_router directly.
    """
    return request.app.state.llm_router


# NOTE: Do NOT re-export get_current_user here — it causes a subtle bug.
# A wrapper function used with Depends() returns the inner function object
# instead of calling it as a dependency. Import directly from app.api.auth:
#   from app.api.auth import get_current_user
