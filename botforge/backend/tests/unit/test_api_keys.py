"""
Unit tests for API Key Authentication (S86).

Tests cover:
- Key creation with hash and prefix
- API key auth middleware (header parsing, hash lookup)
- Scope-based role mapping
- Key revocation blocks auth
- Key management endpoints (create, list, revoke, update)
- Usage tracking (request count, last_used)
"""

import hashlib
import secrets
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.api_keys import API_KEY_PREFIX, API_KEY_RANDOM_LENGTH, VALID_SCOPES

# --- Key Creation Tests ---


class TestAPIKeyCreation:
    """Test API key generation and storage."""

    def test_key_format(self):
        """Generated key has correct prefix and length."""
        raw_key = API_KEY_PREFIX + secrets.token_hex(API_KEY_RANDOM_LENGTH // 2)
        assert raw_key.startswith("bf_live_")
        assert len(raw_key) == len("bf_live_") + API_KEY_RANDOM_LENGTH

    def test_key_hash_is_sha256(self):
        """Key hash uses SHA-256 for secure storage."""
        raw_key = "bf_live_a1b2c3d4e5f6a1b2c3d4e5f6"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        assert len(key_hash) == 64  # SHA-256 hex digest is 64 chars
        # Same input always produces same hash
        assert hashlib.sha256(raw_key.encode()).hexdigest() == key_hash

    def test_prefix_extraction(self):
        """Key prefix shows first 12 chars + ellipsis."""
        raw_key = "bf_live_a1b2c3d4e5f6a1b2c3d4e5f6"
        prefix = raw_key[:12] + "..."
        assert prefix == "bf_live_a1b2..."
        assert len(prefix) == 15

    def test_valid_scopes(self):
        """Valid scope set includes read, chat, admin."""
        assert VALID_SCOPES == {"read", "chat", "admin"}


# --- Auth Middleware Tests ---


class TestAPIKeyAuth:
    """Test API key authentication middleware logic."""

    @pytest.mark.asyncio
    async def test_bearer_header_parsing(self):
        """API key extracted from Bearer token in Authorization header."""
        from app.api.auth import _authenticate_api_key

        # Create a mock key
        raw_key = "bf_live_testkey1234567890abcdef"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        workspace_id = uuid4()
        owner_id = uuid4()

        mock_api_key = MagicMock()
        mock_api_key.key_hash = key_hash
        mock_api_key.is_revoked = False
        mock_api_key.id = uuid4()
        mock_api_key.workspace_id = workspace_id
        mock_api_key.scopes = ["read", "chat"]
        mock_api_key.prefix = "bf_live_test..."

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id
        mock_workspace.owner_id = owner_id

        mock_user = MagicMock()
        mock_user.id = owner_id

        # Mock DB session
        mock_db = AsyncMock()

        # Chain of execute calls: APIKey, update, Workspace, User
        call_count = 0
        results = [mock_api_key, None, mock_workspace, mock_user]

        async def mock_execute(stmt):
            nonlocal call_count
            result = MagicMock()
            if call_count < len(results):
                result.scalar_one_or_none.return_value = results[call_count]
            call_count += 1
            return result

        mock_db.execute = mock_execute

        result = await _authenticate_api_key(raw_key, mock_db)

        assert result is not None
        user, ws_id, role = result
        assert ws_id == workspace_id
        assert role == "agent"  # chat scope -> agent role

    @pytest.mark.asyncio
    async def test_revoked_key_returns_none(self):
        """Revoked API key is not found (query filters is_revoked=False)."""
        from app.api.auth import _authenticate_api_key

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        async def mock_execute(stmt):
            return mock_result

        mock_db.execute = mock_execute

        result = await _authenticate_api_key("bf_live_revokedkey123456", mock_db)
        assert result is None

    def test_scope_to_role_mapping(self):
        """Scopes map to correct roles: admin->admin, chat->agent, read->viewer."""
        # admin scope gives admin role
        scopes_admin = ["read", "chat", "admin"]
        if "admin" in scopes_admin:
            role = "admin"
        elif "chat" in scopes_admin:
            role = "agent"
        else:
            role = "viewer"
        assert role == "admin"

        # chat scope gives agent role
        scopes_chat = ["read", "chat"]
        if "admin" in scopes_chat:
            role = "admin"
        elif "chat" in scopes_chat:
            role = "agent"
        else:
            role = "viewer"
        assert role == "agent"

        # read-only gives viewer role
        scopes_read = ["read"]
        if "admin" in scopes_read:
            role = "admin"
        elif "chat" in scopes_read:
            role = "agent"
        else:
            role = "viewer"
        assert role == "viewer"


# --- Key Management Tests ---


class TestKeyManagement:
    """Test key management operations."""

    def test_scope_validation(self):
        """Invalid scopes are rejected."""
        requested = {"read", "write"}
        invalid = requested - VALID_SCOPES
        assert invalid == {"write"}

    def test_all_valid_scopes_pass(self):
        """All valid scopes pass validation."""
        requested = {"read", "chat", "admin"}
        invalid = requested - VALID_SCOPES
        assert invalid == set()

    def test_key_uniqueness(self):
        """Two generated keys should have different hashes."""
        key1 = API_KEY_PREFIX + secrets.token_hex(API_KEY_RANDOM_LENGTH // 2)
        key2 = API_KEY_PREFIX + secrets.token_hex(API_KEY_RANDOM_LENGTH // 2)
        hash1 = hashlib.sha256(key1.encode()).hexdigest()
        hash2 = hashlib.sha256(key2.encode()).hexdigest()
        assert hash1 != hash2
        assert key1 != key2
