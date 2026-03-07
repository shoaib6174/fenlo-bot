"""Integration test configuration and fixtures."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.main import app
from app.models.channel import ChannelConfig
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import hash_password


@pytest_asyncio.fixture
async def test_client(db_session: AsyncSession):
    """
    Create test client with database dependency overridden.

    This fixture ensures all API requests during tests use the test database
    session which runs in a transaction that will be rolled back after the test.
    Cookies are automatically persisted across requests within the same test.
    """

    # Override the database dependency to use test database session
    async def override_get_db():
        yield db_session

    # Replace the production dependency with our test version
    app.dependency_overrides[get_db] = override_get_db

    try:
        # Create and yield the test client with cookie persistence
        # follow_redirects=True ensures cookies are preserved
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", follow_redirects=True
        ) as client:
            yield client
    finally:
        # Clean up only the db dependency override (preserve others like rate limiter)
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """
    Create a test user with workspace for integration tests.

    Returns a User object with:
    - email: test@example.com
    - password: password123 (hashed)
    - associated workspace
    """
    # Create user first
    user = User(
        email="test@example.com", password_hash=hash_password("password123"), name="Test User"
    )
    db_session.add(user)
    await db_session.flush()

    # Create workspace with user as owner
    workspace = Workspace(owner_id=user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.flush()

    # Associate user with workspace
    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def auth_headers(test_client: AsyncClient, test_user: User, db_session: AsyncSession):
    """
    Create authenticated headers for API requests.

    Logs in the test user and returns headers with auth cookie + workspace_id.
    """
    # Login to get auth cookie
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},  # pragma: allowlist secret
    )

    assert response.status_code == 200
    access_token = response.cookies.get("access_token")

    # Get workspace_id from user
    from sqlalchemy import select

    stmt = select(WorkspaceMember).where(WorkspaceMember.user_id == test_user.id)
    result = await db_session.execute(stmt)
    workspace_id = result.scalar_one().workspace_id

    return {
        "Cookie": f"access_token={access_token}",
        "workspace_id": str(workspace_id),  # Store for test assertions
    }


@pytest_asyncio.fixture
async def widget_channel_config(db_session: AsyncSession, test_user: User):
    """
    Create a widget channel configuration for testing.

    Returns a dict with channel config data including:
    - id: Channel config UUID
    - workspace_id: Workspace UUID
    - All standard ChannelConfig fields
    - _db_session: Database session (for cross-workspace tests)
    """
    # Get workspace_id from test_user
    from sqlalchemy import select

    stmt = select(WorkspaceMember).where(WorkspaceMember.user_id == test_user.id)
    result = await db_session.execute(stmt)
    workspace_id = result.scalar_one().workspace_id

    # Create widget channel config
    config = ChannelConfig(
        workspace_id=workspace_id,
        channel="widget",
        provider=None,
        config={
            "colors": {"primary": "#007bff", "background": "#ffffff"},
            "position": "bottom-right",
            "greeting": "Hi! How can I help you today?",
            "allowed_domains": ["example.com", "*.example.com"],
            "widget_id_hmac_salt": "test-salt-12345",
        },
        is_active=True,
    )

    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)

    return {
        "id": str(config.id),
        "workspace_id": str(config.workspace_id),
        "channel": config.channel,
        "config": config.config,
        "is_active": config.is_active,
    }
