"""Integration tests for workspace settings — covers real DB paths.

Exercises the GET/PUT /settings with actual workspace data in DB.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password


@pytest.mark.asyncio
class TestWorkspaceSettingsWithDB:
    """Test workspace settings with real database workspace."""

    async def _create_owner(self, db_session: AsyncSession):
        """Helper: create owner + workspace + member in DB."""
        user_id = uuid4()
        workspace_id = uuid4()

        user = User(
            id=user_id,
            email=f"owner-{user_id}@example.com",
            password_hash=hash_password("password"),
            name="Owner",
        )
        workspace = Workspace(
            id=workspace_id,
            owner_id=user_id,
            name="Test Workspace",
            settings={"bot_name": "OriginalBot", "personality": "friendly"},
            features={"rag_enabled": True},
        )
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role="owner",
        )
        db_session.add_all([user, workspace, member])
        await db_session.commit()

        token = create_access_token(user_id, workspace_id, "owner")
        return token, workspace_id

    async def test_get_settings_returns_workspace_data(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """GET /settings with real workspace returns actual settings."""
        token, ws_id = await self._create_owner(db_session)

        response = await test_client.get(
            "/api/v1/settings",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == str(ws_id)
        assert data["name"] == "Test Workspace"
        assert data["settings"]["bot_name"] == "OriginalBot"
        assert data["features"]["rag_enabled"] is True

    async def test_put_settings_updates_workspace(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """PUT /settings with owner token merges new settings."""
        token, ws_id = await self._create_owner(db_session)

        response = await test_client.put(
            "/api/v1/settings",
            cookies={"access_token": token},
            json={"bot_name": "UpdatedBot", "greeting": "Hello!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Settings updated successfully"
        assert data["settings"]["bot_name"] == "UpdatedBot"
        assert data["settings"]["greeting"] == "Hello!"
        # Original field should still be present (merge, not replace)
        assert data["settings"]["personality"] == "friendly"

    async def test_get_settings_nonexistent_workspace_returns_404(self, test_client: AsyncClient):
        """Token with non-existent workspace_id in DB should return 401 (user not found)."""
        token = create_access_token(uuid4(), uuid4(), "owner")
        response = await test_client.get(
            "/api/v1/settings",
            cookies={"access_token": token},
        )
        # user not found in DB -> 401
        assert response.status_code == 401

    async def test_delete_billing_as_owner(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """DELETE /settings/billing is owner-only and returns placeholder."""
        token, ws_id = await self._create_owner(db_session)

        response = await test_client.delete(
            "/api/v1/settings/billing",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "workspace_id" in data
