"""Unit tests for Meta WhatsApp Cloud API Integration."""

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.channel import ChannelConfig
from app.modules.channels.meta_whatsapp_provider import MetaWhatsAppProvider
from app.modules.channels.provider import InboundMessage

# --- Test Fixtures ---


@pytest.fixture
def meta_config_data():
    """Valid Meta WhatsApp Cloud API configuration."""
    return {
        "access_token": "EAAxxxxxxxxxxxxxxxx",  # pragma: allowlist secret
        "phone_number_id": "123456789012345",
        "app_secret": "abcdef1234567890abcdef1234567890",  # pragma: allowlist secret
        "verify_token": "my-verify-token",  # pragma: allowlist secret
        "phone_number": "+15551234567",
    }


@pytest.fixture
def meta_channel_config(meta_config_data):
    """ChannelConfig model instance for Meta WhatsApp."""
    return ChannelConfig(
        id=uuid4(),
        workspace_id=uuid4(),
        channel="whatsapp",
        provider="meta",
        config=meta_config_data,
        is_active=True,
    )


@pytest.fixture
def valid_meta_webhook_payload():
    """Valid Meta WhatsApp webhook payload for inbound text message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "123456789012345",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": "15559876543",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "15559876543",
                                    "id": "wamid.HBgNMTU1NTk4NzY1NDMVAgASGCA2MDAwMDAwMDAwMDAwMDAwMA==",
                                    "timestamp": "1677777777",
                                    "text": {"body": "Hello from Meta WhatsApp"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def meta_status_webhook_payload():
    """Meta WhatsApp webhook payload for delivery status update."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "123456789012345",
                            },
                            "statuses": [
                                {
                                    "id": "wamid.HBgNMTU1NTk4NzY1NDMVAgASGCA2MDAwMDAwMDAwMDAwMDAwMA==",
                                    "status": "delivered",
                                    "timestamp": "1677777888",
                                    "recipient_id": "15559876543",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


# --- TestMetaProvider ---


class TestMetaProvider:
    """Test MetaWhatsAppProvider interface and message handling."""

    async def test_provider_interface_contract(self):
        """MetaWhatsAppProvider implements ChannelProvider protocol."""
        provider = MetaWhatsAppProvider()

        assert hasattr(provider, "send_message")
        assert hasattr(provider, "validate_config")
        assert hasattr(provider, "process_inbound")
        assert hasattr(provider, "format_message")

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    async def test_config_validation_valid(self, mock_settings):
        """Config validation passes with valid Meta credentials."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = ""
        mock_settings.meta_whatsapp_phone_number_id = ""
        mock_settings.meta_whatsapp_app_secret = ""

        # Valid config from DB
        config = {
            "access_token": "EAAxxxxxxxx",  # pragma: allowlist secret
            "phone_number_id": "123456789",
            "app_secret": "abcdef123456",  # pragma: allowlist secret
        }
        assert await provider.validate_config(config)

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    async def test_config_validation_falls_back_to_env(self, mock_settings):
        """Config validation falls back to env vars when DB config is empty."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = "EAAxxxxxxxx"
        mock_settings.meta_whatsapp_phone_number_id = "123456789"
        mock_settings.meta_whatsapp_app_secret = "abcdef123456"  # pragma: allowlist secret

        assert await provider.validate_config({})

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    async def test_config_validation_missing_access_token(self, mock_settings):
        """Config validation fails when access_token is missing."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = ""
        mock_settings.meta_whatsapp_phone_number_id = "123456789"
        mock_settings.meta_whatsapp_app_secret = "abcdef123456"  # pragma: allowlist secret

        assert not await provider.validate_config({})

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    async def test_config_validation_missing_phone_number_id(self, mock_settings):
        """Config validation fails when phone_number_id is missing."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = "EAAxxxxxxxx"
        mock_settings.meta_whatsapp_phone_number_id = ""
        mock_settings.meta_whatsapp_app_secret = "abcdef123456"  # pragma: allowlist secret

        assert not await provider.validate_config({})

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    async def test_config_validation_missing_app_secret(self, mock_settings):
        """Config validation fails when app_secret is missing."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = "EAAxxxxxxxx"
        mock_settings.meta_whatsapp_phone_number_id = "123456789"
        mock_settings.meta_whatsapp_app_secret = ""

        assert not await provider.validate_config({})

    async def test_process_inbound_valid_message(
        self, valid_meta_webhook_payload, meta_channel_config
    ):
        """process_inbound extracts message from valid Meta payload."""
        provider = MetaWhatsAppProvider()

        result: InboundMessage = await provider.process_inbound(
            valid_meta_webhook_payload, meta_channel_config
        )

        assert result.content == "Hello from Meta WhatsApp"
        assert result.sender_id == "15559876543"
        assert (
            result.provider_message_id
            == "wamid.HBgNMTU1NTk4NzY1NDMVAgASGCA2MDAwMDAwMDAwMDAwMDAwMA=="
        )
        assert result.metadata["contact_name"] == "Test User"
        assert result.metadata["message_type"] == "text"

    async def test_process_inbound_rejects_invalid_payload(self, meta_channel_config):
        """process_inbound rejects malformed payloads."""
        provider = MetaWhatsAppProvider()

        # Invalid: not a dict
        with pytest.raises(ValueError, match="must be a dict"):
            await provider.process_inbound("not_a_dict", meta_channel_config)

        # Invalid: missing entry
        with pytest.raises(ValueError, match="'entry' is required"):
            await provider.process_inbound({}, meta_channel_config)

        # Invalid: empty entry list
        with pytest.raises(ValueError, match="'entry' is required"):
            await provider.process_inbound({"entry": []}, meta_channel_config)

        # Invalid: missing changes
        with pytest.raises(ValueError, match="'entry\\[0\\].changes' is required"):
            await provider.process_inbound({"entry": [{}]}, meta_channel_config)

        # Invalid: no messages
        with pytest.raises(ValueError, match="no messages found"):
            await provider.process_inbound(
                {"entry": [{"changes": [{"value": {}}]}]}, meta_channel_config
            )

    async def test_process_inbound_non_text_message(self, meta_channel_config):
        """process_inbound handles non-text messages (e.g. image)."""
        provider = MetaWhatsAppProvider()

        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "15559876543",
                                        "id": "wamid.test",
                                        "type": "image",
                                        "image": {"id": "img123"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ],
        }

        result = await provider.process_inbound(payload, meta_channel_config)
        assert result.content == "[image message]"
        assert result.metadata["message_type"] == "image"

    async def test_format_message(self):
        """format_message returns plain text (passthrough)."""
        provider = MetaWhatsAppProvider()

        formatted = await provider.format_message("Hello, world!", {})
        assert formatted == "Hello, world!"

    @patch("app.modules.channels.meta_whatsapp_provider.httpx.AsyncClient")
    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    async def test_send_message_success(
        self, mock_settings, mock_client_class, meta_channel_config
    ):
        """send_message successfully sends via Meta Graph API."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = ""
        mock_settings.meta_whatsapp_phone_number_id = ""
        mock_settings.meta_whatsapp_app_secret = ""
        mock_settings.meta_whatsapp_api_version = "v21.0"

        meta_channel_config.config["recipient_phone"] = "15559876543"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "15559876543", "wa_id": "15559876543"}],
            "messages": [{"id": "wamid.sent123"}],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance

        result = await provider.send_message(
            conversation_id=uuid4(),
            message="Hello from BotForge",
            config=meta_channel_config,
        )

        assert result.success is True
        assert result.provider_message_id == "wamid.sent123"
        assert result.error is None

    async def test_send_message_no_recipient(self, meta_channel_config):
        """send_message fails gracefully when no recipient phone is set."""
        provider = MetaWhatsAppProvider()

        # Ensure no recipient_phone in config
        meta_channel_config.config.pop("recipient_phone", None)

        result = await provider.send_message(
            conversation_id=uuid4(),
            message="Hello",
            config=meta_channel_config,
        )

        assert result.success is False
        assert "Recipient phone number not found" in result.error
        assert result.should_retry is False


# --- TestMetaSignatureValidation ---


class TestMetaSignatureValidation:
    """Test Meta webhook signature validation (HMAC-SHA256)."""

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    def test_valid_signature(self, mock_settings):
        """Valid Meta signature passes validation."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = ""
        mock_settings.meta_whatsapp_phone_number_id = ""
        mock_settings.meta_whatsapp_app_secret = "test_app_secret_12345"  # pragma: allowlist secret
        mock_settings.meta_whatsapp_api_version = "v21.0"

        raw_body = b'{"object":"whatsapp_business_account","entry":[]}'

        # Generate expected signature
        expected_hash = hmac.new(
            b"test_app_secret_12345",  # pragma: allowlist secret
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        signature_header = f"sha256={expected_hash}"

        assert provider.validate_webhook_signature(signature_header, raw_body)

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    def test_invalid_signature(self, mock_settings):
        """Invalid Meta signature is rejected."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = ""
        mock_settings.meta_whatsapp_phone_number_id = ""
        mock_settings.meta_whatsapp_app_secret = "test_app_secret_12345"  # pragma: allowlist secret
        mock_settings.meta_whatsapp_api_version = "v21.0"

        raw_body = b'{"object":"whatsapp_business_account","entry":[]}'
        invalid_signature = "sha256=invalid_hex_value"

        assert not provider.validate_webhook_signature(invalid_signature, raw_body)

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    def test_missing_app_secret(self, mock_settings):
        """Signature validation fails when app_secret is not configured."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = ""
        mock_settings.meta_whatsapp_phone_number_id = ""
        mock_settings.meta_whatsapp_app_secret = ""
        mock_settings.meta_whatsapp_api_version = "v21.0"

        raw_body = b'{"test": "data"}'
        assert not provider.validate_webhook_signature("sha256=abc", raw_body)

    def test_empty_inputs(self):
        """Signature validation rejects empty inputs."""
        provider = MetaWhatsAppProvider()

        assert not provider.validate_webhook_signature("", b"body")
        assert not provider.validate_webhook_signature("sha256=abc", b"")

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    def test_missing_sha256_prefix(self, mock_settings):
        """Signature validation rejects headers without sha256= prefix."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = ""
        mock_settings.meta_whatsapp_phone_number_id = ""
        mock_settings.meta_whatsapp_app_secret = "test_secret"  # pragma: allowlist secret
        mock_settings.meta_whatsapp_api_version = "v21.0"

        raw_body = b'{"test": "data"}'
        assert not provider.validate_webhook_signature("no_prefix_here", raw_body)

    @patch("app.modules.channels.meta_whatsapp_provider.settings")
    def test_signature_from_channel_config(self, mock_settings):
        """Signature validation uses app_secret from channel config over env vars."""
        provider = MetaWhatsAppProvider()

        mock_settings.meta_whatsapp_access_token = ""
        mock_settings.meta_whatsapp_phone_number_id = ""
        mock_settings.meta_whatsapp_app_secret = "wrong_secret"  # pragma: allowlist secret
        mock_settings.meta_whatsapp_api_version = "v21.0"

        config = ChannelConfig(
            id=uuid4(),
            workspace_id=uuid4(),
            channel="whatsapp",
            provider="meta",
            config={"app_secret": "correct_secret"},  # pragma: allowlist secret
            is_active=True,
        )

        raw_body = b'{"test": "data"}'
        expected_hash = hmac.new(
            b"correct_secret",  # pragma: allowlist secret
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        assert provider.validate_webhook_signature(
            f"sha256={expected_hash}", raw_body, config=config
        )


# --- TestResponseRouterProviderAware ---

# These tests require the twilio SDK which is not installed locally.
# They will pass in CI where twilio is available.

try:
    from app.modules.channels.response_router import _PROVIDER_REGISTRY

    _has_response_router = True
except ImportError:
    _has_response_router = False


@pytest.mark.skipif(not _has_response_router, reason="twilio SDK not installed locally")
class TestResponseRouterProviderAware:
    """Test that response router uses provider-aware dispatch."""

    def test_provider_registry_has_meta(self):
        """Provider registry includes Meta WhatsApp provider."""
        assert "whatsapp:meta" in _PROVIDER_REGISTRY
        assert "whatsapp:twilio" in _PROVIDER_REGISTRY
        assert "whatsapp" in _PROVIDER_REGISTRY  # fallback

    def test_meta_provider_type(self):
        """whatsapp:meta registry entry is MetaWhatsAppProvider."""
        assert isinstance(_PROVIDER_REGISTRY["whatsapp:meta"], MetaWhatsAppProvider)

    def test_twilio_provider_type(self):
        """whatsapp:twilio registry entry is TwilioWhatsAppProvider."""
        from app.modules.channels.twilio_whatsapp_provider import TwilioWhatsAppProvider

        assert isinstance(_PROVIDER_REGISTRY["whatsapp:twilio"], TwilioWhatsAppProvider)
        assert isinstance(_PROVIDER_REGISTRY["whatsapp"], TwilioWhatsAppProvider)


# --- TestWebhookVerification ---
# These tests need the full app (which imports twilio), so they're skipped locally.
# They will pass in CI where twilio is available.

try:
    from httpx import AsyncClient as _AsyncClient  # noqa: F401

    # Try importing the app to see if twilio is available
    from app.main import app as _app  # noqa: F401

    _has_app = True
except ImportError:
    _has_app = False


@pytest.mark.skipif(not _has_app, reason="twilio SDK not installed locally — app cannot start")
class TestWebhookVerification:
    """Test Meta webhook verification endpoint."""

    @patch("app.api.whatsapp_meta.settings")
    async def test_verify_success(self, mock_settings, client):
        """GET /webhook with valid verify_token returns hub.challenge."""
        mock_settings.meta_whatsapp_verify_token = "my-test-token"

        response = await client.get(
            "/api/v1/channels/whatsapp-meta/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "my-test-token",
                "hub.challenge": "challenge_12345",
            },
        )

        assert response.status_code == 200
        assert response.text == "challenge_12345"

    @patch("app.api.whatsapp_meta.settings")
    async def test_verify_wrong_token(self, mock_settings, client):
        """GET /webhook with wrong verify_token returns 403."""
        mock_settings.meta_whatsapp_verify_token = "correct-token"

        response = await client.get(
            "/api/v1/channels/whatsapp-meta/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge_12345",
            },
        )

        assert response.status_code == 403

    @patch("app.api.whatsapp_meta.settings")
    async def test_verify_wrong_mode(self, mock_settings, client):
        """GET /webhook with wrong hub.mode returns 403."""
        mock_settings.meta_whatsapp_verify_token = "my-test-token"

        response = await client.get(
            "/api/v1/channels/whatsapp-meta/webhook",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": "my-test-token",
                "hub.challenge": "challenge_12345",
            },
        )

        assert response.status_code == 403
