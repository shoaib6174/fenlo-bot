"""Integration tests for Workspace Settings API.

Tests cover:
- GET /api/v1/settings (get settings)
- PUT /api/v1/settings (update settings)
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password


@pytest_asyncio.fixture
async def settings_client(db_session: AsyncSession):
    """Test client with DB override for settings tests."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def settings_user(db_session: AsyncSession):
    """Create owner user with workspace for settings tests."""
    user = User(
        id=uuid.uuid4(),
        email="settings@test.com",
        password_hash=hash_password("password123"),
        name="Settings User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Settings Workspace",
        features={"rag_enabled": True},
        settings={"bot_name": "TestBot"},
    )
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)

    user.workspace_id = workspace.id
    return user


@pytest_asyncio.fixture
async def settings_token(settings_user: User):
    """Token for settings tests."""
    return create_access_token(
        user_id=settings_user.id,
        workspace_id=settings_user.workspace_id,
        role="owner",
    )


@pytest.mark.asyncio
class TestGetSettings:
    """Tests for GET /api/v1/settings"""

    async def test_get_settings(self, settings_client, settings_token):
        """Returns actual workspace settings."""
        response = await settings_client.get(
            "/api/v1/settings",
            cookies={"access_token": settings_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Settings Workspace"
        assert data["settings"]["bot_name"] == "TestBot"
        assert data["features"]["rag_enabled"] is True


@pytest.mark.asyncio
class TestUpdateSettings:
    """Tests for PUT /api/v1/settings"""

    async def test_update_settings(self, settings_client, settings_token):
        """Updates workspace settings."""
        response = await settings_client.put(
            "/api/v1/settings",
            json={"bot_name": "UpdatedBot", "personality": "professional"},
            cookies={"access_token": settings_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Settings updated successfully"
        assert data["settings"]["bot_name"] == "UpdatedBot"
        assert data["settings"]["personality"] == "professional"
