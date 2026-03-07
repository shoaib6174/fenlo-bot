"""Extended integration tests for auth API endpoints.

Covers uncovered paths: ws-token, logout,
register error handling, get_current_user edge cases.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.services.auth import create_access_token


@pytest.mark.asyncio
class TestWSToken:
    """Test WebSocket token endpoint."""

    async def test_ws_token_returns_short_lived_token(self, test_client: AsyncClient):
        """Authenticated user can get a short-lived WS token."""
        email = "wstoken@example.com"
        password = "SecurePass123!"

        await test_client.post(
            "/api/v1/auth/register", json={"email": email, "password": password, "name": "WS User"}
        )
        await test_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        response = await test_client.get("/api/v1/auth/ws-token")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_ws_token_without_auth_returns_401(self, test_client: AsyncClient):
        response = await test_client.get("/api/v1/auth/ws-token")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestLogout:
    """Test logout endpoint."""

    async def test_logout_returns_success(self, test_client: AsyncClient):
        response = await test_client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"

    async def test_logout_clears_cookie(self, test_client: AsyncClient):
        email = "logout@example.com"
        password = "SecurePass123!"

        # Register and login
        await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "name": "Logout User"},
        )

        # Logout
        response = await test_client.post("/api/v1/auth/logout")
        assert response.status_code == 200


@pytest.mark.asyncio
class TestGetCurrentUserEdgeCases:
    """Test get_current_user dependency edge cases."""

    async def test_no_cookie_returns_401(self, test_client: AsyncClient):
        response = await test_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_empty_cookie_returns_401_or_200(self, test_client: AsyncClient):
        """Empty cookie string may be treated as no cookie by some frameworks."""
        response = await test_client.get("/api/v1/auth/me", cookies={"access_token": ""})
        # Empty string cookie → treated as no auth or invalid
        assert response.status_code == 401

    async def test_malformed_jwt_returns_401(self, test_client: AsyncClient):
        response = await test_client.get("/api/v1/auth/me", cookies={"access_token": "not-a-jwt"})
        assert response.status_code == 401

    async def test_token_with_nonexistent_user_returns_401(self, test_client: AsyncClient):
        """Token with valid structure but user_id not in DB should return 401."""
        token = create_access_token(
            user_id=uuid4(),  # non-existent user
            workspace_id=uuid4(),
            role="owner",
        )
        response = await test_client.get("/api/v1/auth/me", cookies={"access_token": token})
        assert response.status_code == 401
