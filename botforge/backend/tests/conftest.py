"""Pytest configuration and fixtures for backend tests."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.models.base import Base

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://botforge:botforge@localhost:5433/botforge_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine."""
    test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        # Create message partitions for testing (2026-01 through 2026-06)
        # Required because Base.metadata.create_all() doesn't run Alembic migrations
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS messages_2026_01 PARTITION OF messages
            FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS messages_2026_02 PARTITION OF messages
            FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS messages_2026_03 PARTITION OF messages
            FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS messages_2026_04 PARTITION OF messages
            FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS messages_2026_05 PARTITION OF messages
            FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS messages_2026_06 PARTITION OF messages
            FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
        """)
        )

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session for tests with automatic cleanup.

    Each test gets a fresh session with automatic table truncation after completion.
    This ensures test isolation.
    """
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

        # Cleanup: truncate all tables after test
        # This is more reliable than transaction rollback for async PostgreSQL
        try:
            await session.execute(text("TRUNCATE TABLE call_logs CASCADE"))
            await session.execute(text("TRUNCATE TABLE escalation_rules CASCADE"))
            await session.execute(text("TRUNCATE TABLE webhook_outbox CASCADE"))
            await session.execute(text("TRUNCATE TABLE webhook_actions CASCADE"))
            await session.execute(text("TRUNCATE TABLE messages CASCADE"))
            await session.execute(text("TRUNCATE TABLE conversations CASCADE"))
            await session.execute(text("TRUNCATE TABLE channel_configs CASCADE"))
            await session.execute(text("TRUNCATE TABLE documents CASCADE"))
            await session.execute(text("TRUNCATE TABLE knowledge_bases CASCADE"))
            await session.execute(text("TRUNCATE TABLE workspace_members CASCADE"))
            await session.execute(text("TRUNCATE TABLE workspaces CASCADE"))
            await session.execute(text("TRUNCATE TABLE users CASCADE"))
            await session.commit()
        except Exception:
            await session.rollback()


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        ENVIRONMENT="test",
        DATABASE_URL=TEST_DATABASE_URL,
        JWT_SECRET="test-secret-key-for-testing-only",
        LOG_LEVEL="ERROR",
    )


@pytest.fixture
async def redis_mock():
    """Provide fakeredis for tests to avoid event loop issues."""
    try:
        import fakeredis.aioredis

        # Create fake Redis connection
        redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        yield redis

        # Cleanup
        await redis.flushall()
        await redis.aclose()
    except ImportError:
        # Fallback to mock if fakeredis not available
        from unittest.mock import AsyncMock

        redis = AsyncMock()
        yield redis


@pytest.fixture
async def client(db_session):
    """Create unauthenticated test client."""
    from httpx import ASGITransport, AsyncClient

    # Override get_db dependency
    from app.dependencies import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(db_session):
    """Create authenticated test client with JWT token."""
    from httpx import ASGITransport, AsyncClient

    from app.dependencies import get_db
    from app.main import app
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.services.auth import create_access_token, hash_password

    # Create user and workspace
    user = User(
        email="auth_test@example.com",
        password_hash=hash_password("password123"),
        name="Auth Test User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(owner_id=user.id, name="Auth Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(workspace)

    # Generate JWT token
    token = create_access_token(
        user_id=user.id,
        workspace_id=workspace.id,
        role="admin",
    )

    # Override get_db dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c

    # Clean up overrides
    app.dependency_overrides.clear()
