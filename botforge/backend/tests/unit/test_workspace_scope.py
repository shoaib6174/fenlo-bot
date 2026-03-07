"""Unit tests for workspace isolation middleware.

Tests workspace_id extraction from JWT, invalid tokens,
missing workspace_id, and WorkspaceRateLimiter.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.middleware.workspace_scope import (
    WorkspaceRateLimiter,
    get_current_workspace,
    get_workspace_id_from_token,
)
from app.services.auth import create_access_token


class TestGetWorkspaceIdFromToken:
    """Test workspace_id extraction from JWT."""

    def test_valid_token_returns_workspace_id(self):
        user_id = uuid4()
        workspace_id = uuid4()
        token = create_access_token(user_id, workspace_id, "owner")
        result = get_workspace_id_from_token(token)
        assert result == str(workspace_id)

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            get_workspace_id_from_token("invalid.token.here")
        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in exc_info.value.detail

    def test_tampered_token_raises_401(self):
        user_id = uuid4()
        workspace_id = uuid4()
        token = create_access_token(user_id, workspace_id, "owner")
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc_info:
            get_workspace_id_from_token(tampered)
        assert exc_info.value.status_code == 401

    def test_token_without_workspace_id_raises_401(self):
        """Token with missing workspace_id should raise."""
        from jose import jwt

        from app.config import settings

        # Create a token without workspace_id
        payload = {"sub": str(uuid4()), "role": "owner"}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            get_workspace_id_from_token(token)
        assert exc_info.value.status_code == 401
        assert "No workspace" in exc_info.value.detail


@pytest.mark.asyncio
class TestGetCurrentWorkspace:
    """Test the async dependency wrapper."""

    async def test_delegates_to_get_workspace_id_from_token(self):
        user_id = uuid4()
        workspace_id = uuid4()
        token = create_access_token(user_id, workspace_id, "admin")
        result = await get_current_workspace(token)
        assert result == str(workspace_id)

    async def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_workspace("bad-token")
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestWorkspaceRateLimiter:
    """Test per-workspace rate limiting."""

    async def test_default_limit_is_100(self):
        limiter = WorkspaceRateLimiter()
        assert limiter.default_limit == 100

    async def test_check_rate_limit_allows_workspace(self):
        limiter = WorkspaceRateLimiter()
        result = await limiter.check_rate_limit("ws-123")
        assert result is True
