"""Integration tests for channel embed code API (S78)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestEmbedCodeGeneration:
    """Test embed code generation endpoint."""

    async def test_get_embed_code_returns_200(
        self, test_client: AsyncClient, auth_headers: dict, widget_channel_config: dict
    ):
        """Test successful embed code generation returns 200."""
        config_id = widget_channel_config["id"]

        response = await test_client.get(
            f"/api/v1/channels/{config_id}/embed-code", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "html" in data
        assert "widget_id" in data
        assert "widget_url" in data

        # Verify HTML snippet format
        html = data["html"]
        assert "<script" in html
        assert f'data-widget-id="{config_id}"' in html
        assert "data-hmac=" in html
        assert "data-timestamp=" in html
        assert "data-theme=" in html
        assert "data-position=" in html

    async def test_embed_code_includes_hmac(
        self, test_client: AsyncClient, auth_headers: dict, widget_channel_config: dict
    ):
        """Test that embed code includes HMAC authentication."""
        config_id = widget_channel_config["id"]

        response = await test_client.get(
            f"/api/v1/channels/{config_id}/embed-code", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        html = data["html"]

        # HMAC should be present
        assert 'data-hmac="' in html
        assert 'data-timestamp="' in html

        # Extract HMAC value (should be 64 char hex string for SHA256)
        hmac_start = html.find('data-hmac="') + len('data-hmac="')
        hmac_end = html.find('"', hmac_start)
        hmac_value = html[hmac_start:hmac_end]

        assert len(hmac_value) == 64  # SHA256 hex digest length
        assert all(c in "0123456789abcdef" for c in hmac_value)

    async def test_embed_code_widget_url_matches_frontend(
        self, test_client: AsyncClient, auth_headers: dict, widget_channel_config: dict
    ):
        """Test that widget URL uses configured frontend URL."""
        config_id = widget_channel_config["id"]

        response = await test_client.get(
            f"/api/v1/channels/{config_id}/embed-code", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Widget URL should point to frontend
        widget_url = data["widget_url"]
        assert "/widget.js" in widget_url
        # Should use configured FRONTEND_URL (localhost in tests)
        assert "localhost" in widget_url or widget_url.startswith("http")

    async def test_non_widget_channel_returns_400(
        self, test_client: AsyncClient, auth_headers: dict, test_db_session
    ):
        """Test that non-widget channels return 400."""
        from app.models.channel import ChannelConfig

        # Create a non-widget channel (e.g., WhatsApp)
        whatsapp_config = ChannelConfig(
            workspace_id=auth_headers["workspace_id"],
            channel="whatsapp",
            provider="twilio",
            config={
                "phone_number": "+1234567890",
                "template_messages": [],
            },
            is_active=True,
        )
        test_db_session.add(whatsapp_config)
        await test_db_session.commit()
        await test_db_session.refresh(whatsapp_config)

        response = await test_client.get(
            f"/api/v1/channels/{whatsapp_config.id}/embed-code", headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "not supported" in data["error"]["message"].lower()

    async def test_nonexistent_channel_returns_404(
        self, test_client: AsyncClient, auth_headers: dict
    ):
        """Test that nonexistent channel ID returns 404."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"

        response = await test_client.get(
            f"/api/v1/channels/{fake_uuid}/embed-code", headers=auth_headers
        )

        assert response.status_code == 404

    async def test_unauthorized_access_returns_401(
        self, test_client: AsyncClient, widget_channel_config: dict
    ):
        """Test that unauthorized access returns 401."""
        config_id = widget_channel_config["id"]

        response = await test_client.get(f"/api/v1/channels/{config_id}/embed-code")

        assert response.status_code == 401

    async def test_cross_workspace_access_returns_404(
        self,
        test_client: AsyncClient,
        auth_headers: dict,
        widget_channel_config: dict,
        test_db_session,
    ):
        """Test that accessing another workspace's channel returns 404."""
        # Create another user in different workspace
        from app.models.user import User
        from app.models.workspace import Workspace, WorkspaceMember
        from app.services.auth import hash_password

        # Create new workspace
        other_workspace = Workspace(name="Other Workspace")
        test_db_session.add(other_workspace)
        await test_db_session.flush()

        # Create user in other workspace
        other_user = User(
            email="other@example.com",
            password_hash=hash_password("SecurePass123!"),
            name="Other User",
        )
        test_db_session.add(other_user)
        await test_db_session.flush()

        # Associate user with new workspace
        other_member = WorkspaceMember(
            workspace_id=other_workspace.id, user_id=other_user.id, role="owner"
        )
        test_db_session.add(other_member)
        await test_db_session.commit()

        # Login as other user
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "other@example.com",
                "password": "SecurePass123!",  # pragma: allowlist secret
            },
        )
        other_token = login_response.cookies.get("access_token")
        other_headers = {"Cookie": f"access_token={other_token}"}

        # Try to access original workspace's channel
        config_id = widget_channel_config["id"]
        response = await test_client.get(
            f"/api/v1/channels/{config_id}/embed-code", headers=other_headers
        )

        assert response.status_code == 404
