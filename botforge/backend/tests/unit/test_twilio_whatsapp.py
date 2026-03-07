"""Unit tests for Twilio WhatsApp Integration (S51) + status callbacks."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select

from app.models.channel import ChannelConfig, MessageDeliveryLog
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.channels.provider import InboundMessage
from app.modules.channels.twilio_whatsapp_provider import TwilioWhatsAppProvider
from app.services.auth import hash_password

# --- Test Fixtures ---

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "twilio_webhooks"


@pytest.fixture
def twilio_config_data():
    """Valid Twilio WhatsApp configuration."""
    return {
        "recipient_phone": "+15551234567",  # Will be set dynamically per conversation
    }


@pytest.fixture
async def workspace_with_whatsapp(db_session, twilio_config_data):
    """Create a workspace with a WhatsApp channel config."""
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

    # Create whatsapp config
    whatsapp_config = ChannelConfig(
        workspace_id=workspace.id,
        channel="whatsapp",
        config=twilio_config_data,
        is_active=True,
    )
    db_session.add(whatsapp_config)
    await db_session.commit()
    await db_session.refresh(whatsapp_config)

    return workspace, whatsapp_config, user


@pytest.fixture
def valid_webhook_payload():
    """Load valid Twilio webhook payload from fixture."""
    with open(FIXTURES_DIR / "valid_message.json") as f:
        return json.load(f)


@pytest.fixture
def webhook_payload_with_media():
    """Load Twilio webhook payload with media from fixture."""
    with open(FIXTURES_DIR / "message_with_media.json") as f:
        return json.load(f)


# --- TestTwilioProvider ---


class TestTwilioProvider:
    """Test TwilioWhatsAppProvider interface and message handling."""

    async def test_provider_interface_contract(self):
        """TwilioWhatsAppProvider implements ChannelProvider protocol."""
        provider = TwilioWhatsAppProvider()

        # Protocol methods exist and are callable
        assert hasattr(provider, "send_message")
        assert hasattr(provider, "validate_config")
        assert hasattr(provider, "process_inbound")
        assert hasattr(provider, "format_message")

    @patch("app.modules.channels.twilio_whatsapp_provider.settings")
    async def test_config_validation(self, mock_settings):
        """Config validation checks for Twilio credentials in settings."""
        provider = TwilioWhatsAppProvider()

        # Valid config (credentials set)
        mock_settings.twilio_account_sid = (
            "ACtest00000000000000000000000000"  # pragma: allowlist secret
        )
        mock_settings.twilio_auth_token = "test_auth_token_1234567890"
        mock_settings.twilio_sandbox_phone = "+14155238886"
        assert await provider.validate_config({})

        # Invalid: missing account_sid
        mock_settings.twilio_account_sid = ""
        assert not await provider.validate_config({})

        # Invalid: missing auth_token
        mock_settings.twilio_account_sid = "ACtest00000000000000000000000000"
        mock_settings.twilio_auth_token = ""
        assert not await provider.validate_config({})

        # Invalid: missing sandbox_phone
        mock_settings.twilio_auth_token = "test_auth_token_1234567890"
        mock_settings.twilio_sandbox_phone = ""
        assert not await provider.validate_config({})

    async def test_process_inbound_valid_message(
        self, valid_webhook_payload, workspace_with_whatsapp
    ):
        """process_inbound extracts message from valid Twilio payload."""
        _, whatsapp_config, _ = workspace_with_whatsapp
        provider = TwilioWhatsAppProvider()

        result: InboundMessage = await provider.process_inbound(
            valid_webhook_payload, whatsapp_config
        )

        assert result.content == "Hello from WhatsApp"
        assert result.sender_id == "+15551234567"  # Without "whatsapp:" prefix
        assert result.provider_message_id == "SM1234567890abcdef1234567890abcdef"
        assert result.metadata == {}  # No media

    async def test_process_inbound_with_media(
        self, webhook_payload_with_media, workspace_with_whatsapp
    ):
        """process_inbound extracts media URLs when present."""
        _, whatsapp_config, _ = workspace_with_whatsapp
        provider = TwilioWhatsAppProvider()

        result: InboundMessage = await provider.process_inbound(
            webhook_payload_with_media, whatsapp_config
        )

        assert result.content == "Check out this image"
        assert result.sender_id == "+15551234567"
        assert "media_urls" in result.metadata
        assert len(result.metadata["media_urls"]) == 1

    async def test_process_inbound_rejects_invalid_payload(self, workspace_with_whatsapp):
        """process_inbound rejects malformed payloads."""
        _, whatsapp_config, _ = workspace_with_whatsapp
        provider = TwilioWhatsAppProvider()

        # Invalid: not a dict
        with pytest.raises(ValueError, match="must be a dict"):
            await provider.process_inbound("not_a_dict", whatsapp_config)

        # Invalid: missing MessageSid
        with pytest.raises(ValueError, match="'MessageSid' is required"):
            await provider.process_inbound({"Body": "Hello"}, whatsapp_config)

        # Invalid: missing Body
        with pytest.raises(ValueError, match="'Body' must be a non-empty string"):
            await provider.process_inbound({"MessageSid": "SM123"}, whatsapp_config)

        # Invalid: missing From
        with pytest.raises(ValueError, match="'From' is required"):
            await provider.process_inbound(
                {"MessageSid": "SM123", "Body": "Hello"}, whatsapp_config
            )

    async def test_format_message(self):
        """format_message returns plain text (no special formatting for WhatsApp)."""
        provider = TwilioWhatsAppProvider()

        formatted = await provider.format_message("Hello, world!", {})
        assert formatted == "Hello, world!"


# --- TestTwilioSignatureValidation ---


class TestTwilioSignatureValidation:
    """Test Twilio webhook signature validation (HMAC-SHA1)."""

    @patch("app.modules.channels.twilio_whatsapp_provider.settings")
    def test_valid_signature(self, mock_settings):
        """Valid Twilio signature passes validation."""
        provider = TwilioWhatsAppProvider()

        # Set auth token
        mock_settings.twilio_auth_token = "test_auth_token_12345"

        # Build test data
        url = "https://example.com/api/v1/channels/whatsapp/webhook"
        params = {
            "MessageSid": "SM123",
            "Body": "Test",
            "From": "whatsapp:+15551234567",
            "To": "whatsapp:+14155238886",
        }

        # Generate expected signature using Twilio's algorithm
        import base64
        import hashlib
        import hmac

        data = url
        for key in sorted(params.keys()):
            data += key + params[key]

        expected_signature = base64.b64encode(
            hmac.new(
                b"test_auth_token_12345",
                data.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("utf-8")

        # Validate
        assert provider.validate_webhook_signature(expected_signature, url, params)

    @patch("app.modules.channels.twilio_whatsapp_provider.settings")
    def test_invalid_signature(self, mock_settings):
        """Invalid Twilio signature is rejected."""
        provider = TwilioWhatsAppProvider()

        # Set auth token
        mock_settings.twilio_auth_token = "test_auth_token_12345"

        # Build test data
        url = "https://example.com/api/v1/channels/whatsapp/webhook"
        params = {"MessageSid": "SM123", "Body": "Test"}

        # Use wrong signature
        invalid_signature = "invalid_signature_value"

        # Validate
        assert not provider.validate_webhook_signature(invalid_signature, url, params)

    @patch("app.modules.channels.twilio_whatsapp_provider.settings")
    def test_missing_auth_token(self, mock_settings):
        """Signature validation fails when auth token is not configured."""
        provider = TwilioWhatsAppProvider()

        # No auth token set
        mock_settings.twilio_auth_token = ""

        url = "https://example.com/api/v1/channels/whatsapp/webhook"
        params = {"MessageSid": "SM123"}

        assert not provider.validate_webhook_signature("any_signature", url, params)


# --- TestTwilioWebhook ---


class TestTwilioWebhook:
    """Test Twilio webhook endpoint."""

    @pytest.mark.skip(reason="TODO: Fix webhook endpoint test - needs mock for asyncio.create_task")
    @patch("app.api.whatsapp.TwilioWhatsAppProvider.validate_webhook_signature")
    async def test_webhook_validates_signature(
        self, mock_validate_signature, client: AsyncClient, valid_webhook_payload
    ):
        """Webhook validates Twilio signature before processing."""
        mock_validate_signature.return_value = True

        # Build request with signature header
        headers = {"X-Twilio-Signature": "valid_signature_here"}

        response = await client.post(
            "/api/v1/channels/whatsapp/webhook",
            data=valid_webhook_payload,
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert mock_validate_signature.called

    async def test_webhook_rejects_missing_signature(
        self, client: AsyncClient, valid_webhook_payload
    ):
        """Webhook rejects requests without signature header."""
        # No X-Twilio-Signature header
        response = await client.post(
            "/api/v1/channels/whatsapp/webhook",
            data=valid_webhook_payload,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error = response.json()
        assert "Missing X-Twilio-Signature" in error["error"]["message"]

    @pytest.mark.skip(reason="TODO: Fix webhook endpoint test - needs mock for asyncio.create_task")
    @patch("app.api.whatsapp.TwilioWhatsAppProvider.validate_webhook_signature")
    async def test_webhook_rejects_invalid_signature(
        self, mock_validate_signature, client: AsyncClient, valid_webhook_payload
    ):
        """Webhook rejects requests with invalid signature."""
        mock_validate_signature.return_value = False

        headers = {"X-Twilio-Signature": "invalid_signature"}

        response = await client.post(
            "/api/v1/channels/whatsapp/webhook",
            data=valid_webhook_payload,
            headers=headers,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error = response.json()
        assert "Invalid Twilio signature" in error["error"]["message"]


# --- TestTwilioSendMessage ---


class TestTwilioSendMessage:
    """Test sending WhatsApp messages via Twilio."""

    @pytest.mark.skip(reason="TODO: Mock Twilio Client - requires twilio SDK mock")
    @patch("app.modules.channels.twilio_whatsapp_provider.TwilioClient")
    async def test_send_message_success(
        self, mock_twilio_client, workspace_with_whatsapp, twilio_config_data
    ):
        """send_message sends WhatsApp message via Twilio REST API."""
        _, whatsapp_config, _ = workspace_with_whatsapp

        # Mock Twilio client
        mock_message = MagicMock()
        mock_message.sid = "SM1234567890abcdef1234567890abcdef"
        mock_twilio_client.return_value.messages.create.return_value = mock_message

        provider = TwilioWhatsAppProvider()
        result = await provider.send_message(
            conversation_id=uuid4(),
            message="Test response",
            config=whatsapp_config,
        )

        assert result.success is True
        assert result.provider_message_id == "SM1234567890abcdef1234567890abcdef"
        assert result.error is None

    @pytest.mark.skip(reason="TODO: Mock Twilio Client - requires twilio SDK mock")
    @patch("app.modules.channels.twilio_whatsapp_provider.TwilioClient")
    async def test_send_message_missing_recipient(
        self, mock_twilio_client, workspace_with_whatsapp
    ):
        """send_message fails when recipient_phone is missing from config."""
        _, whatsapp_config, _ = workspace_with_whatsapp

        # Clear recipient_phone from config
        whatsapp_config.config = {}

        provider = TwilioWhatsAppProvider()
        result = await provider.send_message(
            conversation_id=uuid4(),
            message="Test response",
            config=whatsapp_config,
        )

        assert result.success is False
        assert "Recipient phone number not found" in result.error
        assert result.should_retry is False


# --- TestWhatsAppStatusCallback ---


class TestWhatsAppStatusCallback:
    """Test Twilio WhatsApp status callback endpoint."""

    @pytest.fixture
    def status_payload(self):
        """Valid Twilio status callback form payload."""
        return {
            "MessageSid": "SM1234567890abcdef1234567890abcdef",
            "MessageStatus": "delivered",
            "To": "whatsapp:+15551234567",
            "From": "whatsapp:+14155238886",
            "AccountSid": "ACtest00000000000000000000000000",
        }

    @patch("app.api.whatsapp.TwilioWhatsAppProvider.validate_webhook_signature")
    @patch("app.core.redis.get_resilient_redis")
    async def test_status_callback_logs_delivery(
        self,
        mock_get_redis,
        mock_validate_sig,
        client: AsyncClient,
        db_session,
        workspace_with_whatsapp,
        status_payload,
    ):
        """Valid status callback creates a MessageDeliveryLog entry."""
        mock_validate_sig.return_value = True

        # Mock Redis: not a duplicate
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_get_redis.return_value = mock_redis

        headers = {"X-Twilio-Signature": "valid_signature"}

        response = await client.post(
            "/api/v1/channels/whatsapp/status",
            data=status_payload,
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify delivery log was created
        result = await db_session.execute(
            select(MessageDeliveryLog).where(
                MessageDeliveryLog.provider_message_id == status_payload["MessageSid"]
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.status == "delivered"
        assert log.channel == "whatsapp"
        assert log.error_code is None

    async def test_status_callback_rejects_missing_signature(
        self,
        client: AsyncClient,
        status_payload,
    ):
        """Status callback rejects requests without signature header."""
        response = await client.post(
            "/api/v1/channels/whatsapp/status",
            data=status_payload,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error = response.json()
        assert "Missing X-Twilio-Signature" in error["error"]["message"]

    @patch("app.api.whatsapp.TwilioWhatsAppProvider.validate_webhook_signature")
    async def test_status_callback_rejects_invalid_signature(
        self,
        mock_validate_sig,
        client: AsyncClient,
        status_payload,
    ):
        """Status callback rejects requests with invalid signature."""
        mock_validate_sig.return_value = False

        headers = {"X-Twilio-Signature": "bad_signature"}

        response = await client.post(
            "/api/v1/channels/whatsapp/status",
            data=status_payload,
            headers=headers,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error = response.json()
        assert "Invalid Twilio signature" in error["error"]["message"]

    @patch("app.api.whatsapp.TwilioWhatsAppProvider.validate_webhook_signature")
    @patch("app.core.redis.get_resilient_redis")
    async def test_status_callback_idempotency(
        self,
        mock_get_redis,
        mock_validate_sig,
        client: AsyncClient,
        workspace_with_whatsapp,
        status_payload,
    ):
        """Duplicate status callback is ignored (returns 200 but no new log)."""
        mock_validate_sig.return_value = True

        # Mock Redis: IS a duplicate
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "1"
        mock_get_redis.return_value = mock_redis

        headers = {"X-Twilio-Signature": "valid_signature"}

        response = await client.post(
            "/api/v1/channels/whatsapp/status",
            data=status_payload,
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        # Redis.set should NOT have been called (duplicate was detected before)
        mock_redis.set.assert_not_called()

    @patch("app.api.whatsapp.TwilioWhatsAppProvider.validate_webhook_signature")
    @patch("app.core.redis.get_resilient_redis")
    async def test_status_callback_with_error(
        self,
        mock_get_redis,
        mock_validate_sig,
        client: AsyncClient,
        db_session,
        workspace_with_whatsapp,
        status_payload,
    ):
        """Failed status callback stores error code and message."""
        mock_validate_sig.return_value = True

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_get_redis.return_value = mock_redis

        # Add error fields
        status_payload["MessageStatus"] = "failed"
        status_payload["ErrorCode"] = "30008"
        status_payload["ErrorMessage"] = "Unknown error"

        headers = {"X-Twilio-Signature": "valid_signature"}

        response = await client.post(
            "/api/v1/channels/whatsapp/status",
            data=status_payload,
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify error fields are stored
        result = await db_session.execute(
            select(MessageDeliveryLog).where(
                MessageDeliveryLog.provider_message_id == status_payload["MessageSid"],
                MessageDeliveryLog.status == "failed",
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.error_code == "30008"
        assert log.error_message == "Unknown error"
