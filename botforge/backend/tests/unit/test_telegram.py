"""Tests for Telegram channel provider and webhook processing."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.channels.provider import InboundMessage
from app.modules.channels.telegram_provider import TelegramProvider


class TestTelegramProviderProcessInbound:
    """Test inbound Telegram update parsing."""

    def setup_method(self):
        self.provider = TelegramProvider()
        self.config = MagicMock()
        self.config.config = {"bot_token": "123:ABC"}

    @pytest.mark.asyncio
    async def test_parse_valid_message(self):
        payload = {
            "update_id": 999,
            "message": {
                "message_id": 42,
                "from": {"id": 12345, "first_name": "John", "username": "johndoe"},
                "chat": {"id": 12345, "type": "private"},
                "text": "Hello bot",
            },
        }
        result = await self.provider.process_inbound(payload, self.config)

        assert isinstance(result, InboundMessage)
        assert result.content == "Hello bot"
        assert result.sender_id == "12345"
        assert result.metadata["first_name"] == "John"
        assert result.metadata["username"] == "johndoe"
        assert result.metadata["chat_type"] == "private"

    @pytest.mark.asyncio
    async def test_empty_text_raises(self):
        payload = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 1},
                "chat": {"id": 1, "type": "private"},
                "text": "",
            },
        }
        with pytest.raises(ValueError, match="empty"):
            await self.provider.process_inbound(payload, self.config)

    @pytest.mark.asyncio
    async def test_missing_message_raises(self):
        payload = {"update_id": 1}
        with pytest.raises(ValueError, match="message"):
            await self.provider.process_inbound(payload, self.config)

    @pytest.mark.asyncio
    async def test_missing_chat_id_raises(self):
        payload = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 1},
                "chat": {},
                "text": "Hello",
            },
        }
        with pytest.raises(ValueError, match="chat.id"):
            await self.provider.process_inbound(payload, self.config)


class TestTelegramProviderSendMessage:
    """Test outbound message delivery."""

    def setup_method(self):
        self.provider = TelegramProvider()
        self.config = MagicMock()
        self.config.config = {
            "bot_token": "123:ABC",
            "recipient_chat_id": "67890",
        }

    @pytest.mark.asyncio
    async def test_send_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 100},
        }

        with patch("app.modules.channels.telegram_provider.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await self.provider.send_message(uuid4(), "Hello!", self.config)

        assert result.success is True
        assert result.provider_message_id == "100"

    @pytest.mark.asyncio
    async def test_send_no_token(self):
        self.config.config = {"recipient_chat_id": "123"}
        result = await self.provider.send_message(uuid4(), "Hi", self.config)
        assert result.success is False
        assert "token" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_no_chat_id(self):
        self.config.config = {"bot_token": "123:ABC"}
        result = await self.provider.send_message(uuid4(), "Hi", self.config)
        assert result.success is False
        assert "chat_id" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_api_error_retryable(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        with patch("app.modules.channels.telegram_provider.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            result = await self.provider.send_message(uuid4(), "Hello!", self.config)

        assert result.success is False
        assert result.should_retry is True


class TestTelegramProviderValidateConfig:
    """Test bot token validation via getMe."""

    def setup_method(self):
        self.provider = TelegramProvider()

    @pytest.mark.asyncio
    async def test_valid_token(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"username": "testbot"}}

        with patch("app.modules.channels.telegram_provider.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            assert await self.provider.validate_config({"bot_token": "123:ABC"}) is True

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"ok": False}

        with patch("app.modules.channels.telegram_provider.httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            assert await self.provider.validate_config({"bot_token": "bad"}) is False

    @pytest.mark.asyncio
    async def test_empty_token(self):
        assert await self.provider.validate_config({"bot_token": ""}) is False
        assert await self.provider.validate_config({}) is False
