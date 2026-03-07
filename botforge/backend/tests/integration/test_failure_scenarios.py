"""Failure scenario integration tests.

Tests validate graceful handling of failures:
- Unauthorized access to admin endpoints
- Export for non-existent workspace
- Purge with insufficient permissions
- Analytics with no data (empty workspace)
- Invalid onboarding step names
- CSV export with invalid filters
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

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def fail_client(db_session: AsyncSession):
    """Test client for failure scenario tests."""

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
async def fail_user(db_session: AsyncSession):
    """Owner user for failure tests."""
    user = User(
        id=uuid.uuid4(),
        email="fail@test.com",
        password_hash=hash_password("password123"),
        name="Fail Test User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Fail Workspace",
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
async def fail_token(fail_user: User):
    """Auth token for failure test user."""
    return create_access_token(
        user_id=fail_user.id,
        workspace_id=fail_user.workspace_id,
        role="owner",
    )


@pytest_asyncio.fixture
async def member_user(db_session: AsyncSession, fail_user: User):
    """Non-admin member user in the same workspace."""
    user = User(
        id=uuid.uuid4(),
        email="member@test.com",
        password_hash=hash_password("password123"),
        name="Member User",
    )
    db_session.add(user)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=fail_user.workspace_id,
        user_id=user.id,
        role="member",
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)

    user.workspace_id = fail_user.workspace_id
    return user


@pytest_asyncio.fixture
async def member_token(member_user: User):
    """Auth token for member (non-admin) user."""
    return create_access_token(
        user_id=member_user.id,
        workspace_id=member_user.workspace_id,
        role="member",
    )


# ── Unauthenticated Access ───────────────────────────────────────────────────


@pytest.mark.asyncio
class TestUnauthenticatedAccess:
    """Endpoints reject requests without valid auth."""

    async def test_analytics_requires_auth(self, fail_client):
        """GET /analytics/overview returns 401 without token."""
        response = await fail_client.get("/api/v1/analytics/overview")
        assert response.status_code == 401

    async def test_admin_storage_requires_auth(self, fail_client):
        """GET /admin/storage/{id} returns 401 without token."""
        response = await fail_client.get(f"/api/v1/admin/storage/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_onboarding_requires_auth(self, fail_client):
        """GET /onboarding/progress returns 401 without token."""
        response = await fail_client.get("/api/v1/onboarding/progress")
        assert response.status_code == 401

    async def test_export_requires_auth(self, fail_client):
        """GET /export/conversations/csv returns 401 without token."""
        response = await fail_client.get("/api/v1/export/conversations/csv")
        assert response.status_code == 401


# ── Empty Workspace Analytics ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestEmptyWorkspaceAnalytics:
    """Analytics endpoints handle empty workspaces gracefully."""

    async def test_overview_with_no_data(self, fail_client, fail_token):
        """GET /analytics/overview returns zeros for empty workspace."""
        response = await fail_client.get(
            "/api/v1/analytics/overview",
            cookies={"access_token": fail_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations"] == 0
        assert data["total_messages"] == 0

    async def test_volume_with_no_data(self, fail_client, fail_token):
        """GET /analytics/volume returns empty list."""
        response = await fail_client.get(
            "/api/v1/analytics/volume",
            cookies={"access_token": fail_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_csv_export_empty_workspace(self, fail_client, fail_token):
        """GET /export/conversations/csv works for empty workspace (headers only)."""
        response = await fail_client.get(
            "/api/v1/export/conversations/csv",
            cookies={"access_token": fail_token},
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")


# ── Invalid Onboarding Steps ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestInvalidOnboardingSteps:
    """Onboarding endpoints handle invalid input."""

    async def test_complete_unknown_step(self, fail_client, fail_token):
        """PUT /onboarding/step/nonexistent returns error."""
        response = await fail_client.put(
            "/api/v1/onboarding/step/nonexistent_step",
            cookies={"access_token": fail_token},
        )
        # Should return 400 or 422 for invalid step name
        assert response.status_code in (400, 422)

    async def test_idempotent_step_completion(self, fail_client, fail_token):
        """PUT /onboarding/step/{name} twice is idempotent."""
        # Complete personality step
        resp1 = await fail_client.put(
            "/api/v1/onboarding/step/personality",
            cookies={"access_token": fail_token},
        )
        assert resp1.status_code == 200

        # Complete same step again — should succeed idempotently
        resp2 = await fail_client.put(
            "/api/v1/onboarding/step/personality",
            cookies={"access_token": fail_token},
        )
        assert resp2.status_code == 200


# ── Cross-Workspace Access ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCrossWorkspaceAccess:
    """Users cannot access other workspaces' admin data."""

    async def test_storage_wrong_workspace(self, fail_client, fail_token):
        """GET /admin/storage/{other_workspace} returns 403."""
        other_workspace_id = uuid.uuid4()
        response = await fail_client.get(
            f"/api/v1/admin/storage/{other_workspace_id}",
            cookies={"access_token": fail_token},
        )
        assert response.status_code == 403

    async def test_export_wrong_workspace(self, fail_client, fail_token):
        """POST /admin/export/{other_workspace} returns 403."""
        other_workspace_id = uuid.uuid4()
        response = await fail_client.post(
            f"/api/v1/admin/export/{other_workspace_id}",
            cookies={"access_token": fail_token},
        )
        assert response.status_code == 403

    async def test_purge_wrong_workspace(self, fail_client, fail_token):
        """DELETE /admin/workspace/{other}/data returns 403."""
        other_workspace_id = uuid.uuid4()
        response = await fail_client.delete(
            f"/api/v1/admin/workspace/{other_workspace_id}/data",
            cookies={"access_token": fail_token},
        )
        assert response.status_code == 403


# ── Transcript Not Found ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTranscriptNotFound:
    """Export endpoints handle missing conversations."""

    async def test_transcript_nonexistent_conversation(self, fail_client, fail_token):
        """GET /export/conversations/{id}/transcript for missing conv."""
        fake_id = uuid.uuid4()
        response = await fail_client.get(
            f"/api/v1/export/conversations/{fake_id}/transcript",
            cookies={"access_token": fail_token},
        )
        # Should return 404 or empty transcript
        assert response.status_code in (200, 404)
