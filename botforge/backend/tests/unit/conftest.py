"""Unit test conftest — override autouse DB fixtures when no DB is available."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession


@pytest.fixture(scope="session")
async def engine():
    """Override session-scoped engine. Yields None when test DB is unavailable."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool

        test_engine = create_async_engine(
            "postgresql+asyncpg://botforge:botforge@localhost:5433/botforge_test",  # pragma: allowlist secret
            poolclass=NullPool,
            echo=False,
        )
        async with test_engine.connect() as conn:
            pass  # connection check

        from sqlalchemy import text

        from app.models.base import Base

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            for month in range(1, 7):
                nxt = month + 1
                yr2 = 2026
                if nxt > 12:
                    nxt, yr2 = 1, 2027
                await conn.execute(
                    text(
                        f"CREATE TABLE IF NOT EXISTS messages_2026_{month:02d} "
                        f"PARTITION OF messages "
                        f"FOR VALUES FROM ('2026-{month:02d}-01') "
                        f"TO ('{yr2}-{nxt:02d}-01')"
                    )
                )

        yield test_engine

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()

    except Exception:
        yield None


@pytest.fixture(autouse=True)
async def db_session(engine):
    """Yield a mock AsyncSession when test DB is unavailable."""
    if engine is None:
        yield AsyncMock(spec=_AsyncSession)
        return

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        try:
            for tbl in [
                "call_logs",
                "escalation_rules",
                "webhook_outbox",
                "webhook_actions",
                "messages",
                "conversations",
                "channel_configs",
                "documents",
                "knowledge_bases",
                "workspace_members",
                "workspaces",
                "users",
            ]:
                await session.execute(text(f"TRUNCATE TABLE {tbl} CASCADE"))
            await session.commit()
        except Exception:
            await session.rollback()
