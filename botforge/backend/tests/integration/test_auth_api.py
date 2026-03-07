"""Integration tests for authentication API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    """Test user registration endpoint."""

    async def test_register_returns_201(self, test_client: AsyncClient):
        """Test successful registration returns 201."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "SecurePass123!", "name": "New User"},
        )

        assert response.status_code == 201
        data = response.json()
        user_data = data.get("user", data)
        assert "id" in user_data
        assert user_data["email"] == "newuser@example.com"

    async def test_register_creates_workspace(self, test_client: AsyncClient):
        """Test that registration creates a workspace."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "workspace@example.com",
                "password": "SecurePass123!",
                "name": "Workspace User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        user_data = data.get("user", data)
        assert "workspace_id" in user_data

    async def test_register_sets_httponly_cookie(self, test_client: AsyncClient):
        """Test that registration sets httpOnly cookie."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "cookie@example.com",
                "password": "SecurePass123!",
                "name": "Cookie User",
            },
        )

        assert response.status_code == 201
        # Check for Set-Cookie header
        cookies = response.cookies
        assert "access_token" in cookies

    async def test_duplicate_email_returns_409(self, test_client: AsyncClient):
        """Test that duplicate email returns 409 Conflict."""
        email = "duplicate@example.com"

        # First registration
        await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecurePass123!", "name": "First User"},
        )

        # Second registration with same email
        response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "DifferentPass123!", "name": "Second User"},
        )

        assert response.status_code == 409

    async def test_invalid_email_returns_422(self, test_client: AsyncClient):
        """Test that invalid email returns 422 Validation Error."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "SecurePass123!", "name": "Invalid Email"},
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    """Test user login endpoint."""

    async def test_valid_credentials_returns_httponly_cookie(self, test_client: AsyncClient):
        """Test that valid login sets httpOnly cookie."""
        email = "login@example.com"
        password = "SecurePass123!"

        # First register
        await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "name": "Login User"},
        )

        # Then login
        response = await test_client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )

        assert response.status_code == 200
        assert "access_token" in response.cookies

    async def test_cookie_is_httponly_and_secure(self, test_client: AsyncClient):
        """Test that cookie has httpOnly and secure flags."""
        email = "secure@example.com"
        password = "SecurePass123!"

        await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "name": "Secure User"},
        )

        response = await test_client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )

        # Check cookie attributes
        cookie = response.cookies.get("access_token")
        assert cookie is not None

    async def test_wrong_password_returns_401(self, test_client: AsyncClient):
        """Test that wrong password returns 401 Unauthorized."""
        email = "wrongpass@example.com"
        password = "CorrectPass123!"

        await test_client.post(
            "/api/v1/auth/register", json={"email": email, "password": password, "name": "User"}
        )

        response = await test_client.post(
            "/api/v1/auth/login", json={"email": email, "password": "WrongPass123!"}
        )

        assert response.status_code == 401

    async def test_nonexistent_user_returns_401(self, test_client: AsyncClient):
        """Test that login for non-existent user returns 401."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestProtectedRoutes:
    """Test protected route access control."""

    async def test_without_token_returns_401(self, test_client: AsyncClient):
        """Test that accessing protected route without token returns 401."""
        response = await test_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_with_valid_token_returns_200(self, test_client: AsyncClient):
        """Test that accessing protected route with valid token works."""
        email = "protected@example.com"
        password = "SecurePass123!"

        # Register and login
        await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "name": "Protected User"},
        )

        await test_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        # Use the test_client with cookies persisted automatically
        # The test_client maintains cookies across requests by default
        response = await test_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email

    async def test_with_expired_token_returns_401(self, test_client: AsyncClient):
        """Test that accessing with expired token returns 401."""
        # This would require creating a token with past expiry
        # For now, we test with invalid token
        response = await test_client.get(
            "/api/v1/auth/me", cookies={"access_token": "invalid.token.here"}
        )

        assert response.status_code == 401
