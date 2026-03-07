"""Unit tests for Widget Backend (S50)."""

import time
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.channel import ChannelConfig
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.channels.provider import InboundMessage
from app.modules.channels.widget_provider import WidgetProvider
from app.services.auth import hash_password

# --- Test Fixtures ---


@pytest.fixture
def widget_config_data():
    """Valid widget configuration."""
    return {
        "colors": {"primary": "#007bff", "background": "#ffffff"},
        "position": "bottom-right",
        "greeting": "Hi! How can I help you today?",
        "allowed_domains": ["example.com"],
        "widget_id_hmac_salt": "test_secret_salt_12345",
    }


@pytest.fixture
async def workspace_with_widget(db_session, widget_config_data):
    """Create a workspace with a widget channel config."""
    # Create user
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    # Create workspace
    workspace = Workspace(owner_id=user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.flush()

    # Create widget config
    widget_config = ChannelConfig(
        workspace_id=workspace.id,
        channel="widget",
        config=widget_config_data,
        is_active=True,
    )
    db_session.add(widget_config)
    await db_session.commit()
    await db_session.refresh(widget_config)

    return workspace, widget_config, user


# --- TestChannelProvider ---


class TestChannelProvider:
    """Test ChannelProvider protocol interface and widget config validation."""

    async def test_provider_interface_contract(self):
        """WidgetProvider implements ChannelProvider protocol."""
        provider = WidgetProvider()

        # Protocol methods exist and are callable
        assert hasattr(provider, "send_message")
        assert hasattr(provider, "validate_config")
        assert hasattr(provider, "process_inbound")
        assert hasattr(provider, "format_message")

    async def test_widget_config_validation(self):
        """Widget config validation accepts valid configs and rejects invalid ones."""
        provider = WidgetProvider()

        # Valid config
        valid_config = {
            "allowed_domains": ["example.com"],
            "widget_id_hmac_salt": "secret123",
        }
        assert await provider.validate_config(valid_config)

        # Invalid: missing allowed_domains
        invalid_config_1 = {"widget_id_hmac_salt": "secret123"}
        assert not await provider.validate_config(invalid_config_1)

        # Invalid: empty allowed_domains
        invalid_config_2 = {"allowed_domains": [], "widget_id_hmac_salt": "secret123"}
        assert not await provider.validate_config(invalid_config_2)

        # Invalid: missing widget_id_hmac_salt
        invalid_config_3 = {"allowed_domains": ["example.com"]}
        assert not await provider.validate_config(invalid_config_3)

        # Invalid: empty widget_id_hmac_salt
        invalid_config_4 = {"allowed_domains": ["example.com"], "widget_id_hmac_salt": ""}
        assert not await provider.validate_config(invalid_config_4)


# --- TestWidgetBackend ---


class TestWidgetBackend:
    """Test widget backend API endpoints (config CRUD, public config, error reporting)."""

    async def test_widget_config_fetch_public(self, client: AsyncClient, workspace_with_widget):
        """Widget public config endpoint returns config without JWT."""
        _, widget_config, _ = workspace_with_widget

        # Fetch config with valid Origin
        response = await client.get(
            f"/api/v1/widget/{widget_config.id}/config",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert data["widget_id"] == str(widget_config.id)
        assert data["colors"] == {"primary": "#007bff", "background": "#ffffff"}
        assert data["position"] == "bottom-right"
        assert data["greeting"] == "Hi! How can I help you today?"
        assert data["widget_api_version"] == 1
        assert "hmac" in data
        assert "hmac_timestamp" in data

        # Sensitive data NOT included
        assert "widget_id_hmac_salt" not in data
        assert "allowed_domains" not in data
        assert "workspace_id" not in data

    async def test_widget_config_404_invalid_id(self, client: AsyncClient):
        """Unknown widget ID returns 404."""
        invalid_id = uuid4()

        response = await client.get(
            f"/api/v1/widget/{invalid_id}/config",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error"]["message"] == "Widget not found"

    async def test_widget_config_rejects_invalid_origin(
        self, client: AsyncClient, workspace_with_widget
    ):
        """Widget config endpoint rejects requests from unauthorized domains."""
        _, widget_config, _ = workspace_with_widget

        # Request from unauthorized origin
        response = await client.get(
            f"/api/v1/widget/{widget_config.id}/config",
            headers={"Origin": "https://evil.com"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"]["message"] == "Origin not allowed"

    async def test_widget_error_reporting(self, client: AsyncClient, workspace_with_widget):
        """Widget error reporting endpoint accepts valid payload."""
        _, widget_config, _ = workspace_with_widget

        error_payload = {
            "widget_id": str(widget_config.id),
            "error_type": "websocket_disconnect",
            "message": "Connection closed unexpectedly",
            "stack_trace": "Error: ...",
            "browser": "Chrome 120",
            "url": "https://example.com/page",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        response = await client.post("/api/v1/widget/error", json=error_payload)

        # Error logged, returns 204 No Content
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_widget_error_silently_ignores_invalid_widget(self, client: AsyncClient):
        """Widget error endpoint silently ignores errors for non-existent widgets."""
        invalid_id = uuid4()

        error_payload = {
            "widget_id": str(invalid_id),
            "error_type": "render_error",
            "message": "Failed to render",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Should return 204 even for invalid widget (prevents enumeration)
        response = await client.post("/api/v1/widget/error", json=error_payload)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.skip(reason="TODO: Fix authenticated_client fixture to use workspace_with_widget")
    async def test_channel_config_crud(
        self, authenticated_client: AsyncClient, workspace_with_widget, widget_config_data
    ):
        """Channel config CRUD operations work with workspace isolation."""
        workspace, existing_widget, _ = workspace_with_widget

        # CREATE: Create a new widget config
        create_payload = {
            "channel": "widget",
            "config": widget_config_data,
            "is_active": True,
        }
        response = await authenticated_client.post("/api/v1/channels", json=create_payload)
        assert response.status_code == status.HTTP_201_CREATED
        new_widget = response.json()
        assert new_widget["channel"] == "widget"
        assert new_widget["workspace_id"] == str(workspace.id)

        # READ: List all channel configs
        response = await authenticated_client.get("/api/v1/channels")
        assert response.status_code == status.HTTP_200_OK
        configs = response.json()
        assert len(configs) == 2  # Existing + new

        # READ: Get specific config
        response = await authenticated_client.get(f"/api/v1/channels/{new_widget['id']}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == new_widget["id"]

        # UPDATE: Update config
        update_payload = {
            "config": {**widget_config_data, "position": "bottom-left"},
            "is_active": False,
        }
        response = await authenticated_client.put(
            f"/api/v1/channels/{new_widget['id']}", json=update_payload
        )
        assert response.status_code == status.HTTP_200_OK
        updated = response.json()
        assert updated["config"]["position"] == "bottom-left"
        assert updated["is_active"] is False

        # DELETE: Soft delete (deactivate)
        response = await authenticated_client.delete(f"/api/v1/channels/{new_widget['id']}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft delete (config still exists but is_active=False)
        response = await authenticated_client.get(f"/api/v1/channels/{new_widget['id']}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is False

    @pytest.mark.skip(reason="TODO: Fix authenticated_client fixture to use workspace_with_widget")
    async def test_channel_config_workspace_scoped(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Channel configs are workspace-scoped — cannot access other workspace's configs."""
        # Create a second workspace with a widget
        user2 = User(
            email="other@example.com",
            password_hash=hash_password("password123"),
            name="Other User",
        )
        db_session.add(user2)
        await db_session.flush()

        workspace2 = Workspace(owner_id=user2.id, name="Other Workspace")
        db_session.add(workspace2)
        await db_session.flush()

        widget2 = ChannelConfig(
            workspace_id=workspace2.id,
            channel="widget",
            config={"allowed_domains": ["other.com"], "widget_id_hmac_salt": "other_salt"},
            is_active=True,
        )
        db_session.add(widget2)
        await db_session.commit()

        # Try to access other workspace's widget from authenticated client (workspace 1)
        response = await authenticated_client.get(f"/api/v1/channels/{widget2.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# --- TestWidgetDomainAllowlist ---


class TestWidgetDomainAllowlist:
    """Test domain allowlist matching rules (Spec Panel Review M-04)."""

    def test_bare_domain_matches_exact_origin(self):
        """Bare domain 'example.com' matches https://example.com only (not subdomains)."""
        provider = WidgetProvider()

        # Exact match
        assert provider.validate_domain("https://example.com", ["example.com"])

        # With port
        assert provider.validate_domain("https://example.com:8080", ["example.com"])

        # Subdomain NOT matched
        assert not provider.validate_domain("https://app.example.com", ["example.com"])

    def test_wildcard_matches_subdomains(self):
        """Wildcard '*.example.com' matches subdomains only."""
        provider = WidgetProvider()

        # Subdomain matches
        assert provider.validate_domain("https://app.example.com", ["*.example.com"])
        assert provider.validate_domain("https://api.example.com", ["*.example.com"])

        # Bare domain NOT matched
        assert not provider.validate_domain("https://example.com", ["*.example.com"])

    def test_wildcard_does_not_match_bare_domain(self):
        """Wildcard '*.example.com' does NOT match bare https://example.com."""
        provider = WidgetProvider()

        assert not provider.validate_domain("https://example.com", ["*.example.com"])

    def test_localhost_not_implicitly_allowed(self):
        """localhost and 127.0.0.1 are NOT implicitly allowed — must be explicitly listed."""
        provider = WidgetProvider()

        # Not allowed by default
        assert not provider.validate_domain("http://localhost:3000", ["example.com"])
        assert not provider.validate_domain("http://127.0.0.1:3000", ["example.com"])

        # Allowed when explicitly listed
        assert provider.validate_domain("http://localhost:3000", ["localhost:3000"])
        assert provider.validate_domain("http://127.0.0.1:3000", ["127.0.0.1:3000"])

    def test_case_insensitive_matching(self):
        """Domain matching is case-insensitive."""
        provider = WidgetProvider()

        assert provider.validate_domain("https://Example.COM", ["example.com"])
        assert provider.validate_domain("https://app.Example.com", ["*.example.com"])

    def test_multiple_domains_allowed(self):
        """Multiple domains in allowlist — matches any."""
        provider = WidgetProvider()

        allowed = ["example.com", "*.example.com", "localhost:3000"]

        assert provider.validate_domain("https://example.com", allowed)
        assert provider.validate_domain("https://app.example.com", allowed)
        assert provider.validate_domain("http://localhost:3000", allowed)
        assert not provider.validate_domain("https://evil.com", allowed)


# --- TestWidgetSecurity ---


class TestWidgetSecurity:
    """Test widget security measures (Spec Panel Review T-01)."""

    async def test_widget_config_does_not_leak_workspace(
        self, client: AsyncClient, workspace_with_widget
    ):
        """Widget public config response contains only display config, no sensitive data."""
        _, widget_config, _ = workspace_with_widget

        response = await client.get(
            f"/api/v1/widget/{widget_config.id}/config",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Public fields only
        assert "widget_id" in data
        assert "colors" in data
        assert "position" in data
        assert "greeting" in data
        assert "widget_api_version" in data
        assert "hmac" in data
        assert "hmac_timestamp" in data

        # Sensitive fields NOT leaked
        assert "widget_id_hmac_salt" not in data
        assert "allowed_domains" not in data
        assert "workspace_id" not in data
        assert "is_active" not in data

    async def test_widget_error_rejects_oversized_payload(self, client: AsyncClient):
        """Widget error endpoint rejects payloads > 10KB."""
        # Create oversized payload (message > 1000 chars, stack_trace > 5000 chars)
        oversized_payload = {
            "widget_id": str(uuid4()),
            "error_type": "render_error",
            "message": "x" * 1001,  # Exceeds 1000 char limit
            "stack_trace": "y" * 5001,  # Exceeds 5000 char limit
            "timestamp": datetime.now(UTC).isoformat(),
        }

        response = await client.post("/api/v1/widget/error", json=oversized_payload)

        # Pydantic validation error (422)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_hmac_generation_and_validation(self, widget_config_data):
        """HMAC generation and validation work correctly with TTL."""
        provider = WidgetProvider()
        widget_id = str(uuid4())
        hmac_salt = widget_config_data["widget_id_hmac_salt"]

        # Generate HMAC
        hmac_value, hmac_timestamp = provider.generate_hmac(widget_id, hmac_salt)

        # Validate immediately (should pass)
        assert provider.validate_hmac(widget_id, hmac_value, hmac_timestamp, hmac_salt)

        # Validate with wrong widget_id (should fail)
        assert not provider.validate_hmac(str(uuid4()), hmac_value, hmac_timestamp, hmac_salt)

        # Validate with wrong HMAC (should fail)
        assert not provider.validate_hmac(widget_id, "invalid_hmac", hmac_timestamp, hmac_salt)

        # Validate with expired timestamp (> 5 minutes old)
        expired_timestamp = int(time.time()) - 301  # 5 min + 1 sec ago
        assert not provider.validate_hmac(widget_id, hmac_value, expired_timestamp, hmac_salt)

    async def test_process_inbound_validates_payload(self, workspace_with_widget):
        """process_inbound rejects malformed payloads."""
        _, widget_config, _ = workspace_with_widget
        provider = WidgetProvider()

        # Valid payload
        valid_payload = {
            "type": "message",
            "content": "Hello",
            "session_id": str(uuid4()),
            "message_id": str(uuid4()),
        }
        result: InboundMessage = await provider.process_inbound(valid_payload, widget_config)
        assert result.content == "Hello"
        assert result.sender_id  # Session ID
        assert result.provider_message_id  # Message ID

        # Invalid: missing content
        with pytest.raises(ValueError, match="'content' must be a non-empty string"):
            await provider.process_inbound({"session_id": "123"}, widget_config)

        # Invalid: missing message_id
        with pytest.raises(ValueError, match="'message_id' is required"):
            await provider.process_inbound({"content": "Hello", "session_id": "123"}, widget_config)

        # Invalid: not a dict
        with pytest.raises(ValueError, match="must be a dict"):
            await provider.process_inbound("not_a_dict", widget_config)

    async def test_widget_id_not_enumerable(self, client: AsyncClient):
        """Widget IDs are UUIDs (random, not sequential) — cannot enumerate."""
        # Try to access a random UUID (should 404)
        random_id = uuid4()
        response = await client.get(
            f"/api/v1/widget/{random_id}/config",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Error message does not reveal if workspace exists
        assert response.json()["error"]["message"] == "Widget not found"
