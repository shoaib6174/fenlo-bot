"""Unit tests for Widget Chat SSE endpoint (S75)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from pydantic import ValidationError

from app.api.widget import _check_rate_limit
from app.models.channel import ChannelConfig
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.widget import WidgetChatRequest
from app.services.auth import hash_password

# --- Test Fixtures ---


@pytest.fixture
async def workspace_with_widget(db_session):
    """Create a workspace with an active widget config."""
    user = User(
        email="widgetchat@example.com",
        password_hash=hash_password("password123"),
        name="Widget Chat User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(owner_id=user.id, name="Widget Chat Workspace")
    db_session.add(workspace)
    await db_session.flush()

    widget_config = ChannelConfig(
        workspace_id=workspace.id,
        channel="widget",
        config={
            "colors": {"primary": "#007bff", "background": "#ffffff"},
            "position": "bottom-right",
            "greeting": "Hi! How can I help?",
            "allowed_domains": ["example.com", "localhost:3000"],
            "widget_id_hmac_salt": "test_salt_for_chat",
        },
        is_active=True,
    )
    db_session.add(widget_config)
    await db_session.commit()
    await db_session.refresh(widget_config)

    return workspace, widget_config, user


@pytest.fixture
async def inactive_widget(db_session):
    """Create a workspace with an inactive widget config."""
    user = User(
        email="inactive@example.com",
        password_hash=hash_password("password123"),
        name="Inactive Widget User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(owner_id=user.id, name="Inactive Workspace")
    db_session.add(workspace)
    await db_session.flush()

    widget_config = ChannelConfig(
        workspace_id=workspace.id,
        channel="widget",
        config={
            "allowed_domains": ["example.com"],
            "widget_id_hmac_salt": "salt",
        },
        is_active=False,
    )
    db_session.add(widget_config)
    await db_session.commit()
    await db_session.refresh(widget_config)

    return workspace, widget_config


# --- Schema Tests ---


class TestWidgetChatSchema:
    """Test WidgetChatRequest schema validation."""

    def test_valid_message(self):
        """Valid message passes validation."""
        req = WidgetChatRequest(message="What is your return policy?")
        assert req.message == "What is your return policy?"
        assert req.conversation_id is None

    def test_message_with_conversation_id(self):
        """Message with conversation_id for multi-turn."""
        conv_id = uuid4()
        req = WidgetChatRequest(message="Follow-up question", conversation_id=conv_id)
        assert req.conversation_id == conv_id

    def test_empty_message_rejected(self):
        """Empty message is rejected."""
        with pytest.raises(ValidationError):
            WidgetChatRequest(message="")

    def test_message_max_length(self):
        """Message exceeding 500 chars is rejected."""
        with pytest.raises(ValidationError):
            WidgetChatRequest(message="x" * 501)

    def test_message_at_max_length_accepted(self):
        """Message at exactly 500 chars is accepted."""
        req = WidgetChatRequest(message="x" * 500)
        assert len(req.message) == 500


# --- Rate Limiting Tests ---


class TestWidgetRateLimit:
    """Test rate limiting logic."""

    async def test_rate_limit_allows_under_threshold(self):
        """Rate limit allows requests under threshold."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 5
        mock_redis.expire.return_value = True

        with patch("app.api.widget.get_redis_client", return_value=mock_redis):
            result = await _check_rate_limit("widget-123", "127.0.0.1")
            assert result is True

    async def test_rate_limit_blocks_over_threshold(self):
        """Rate limit blocks requests over threshold (20/hour)."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 21

        with patch("app.api.widget.get_redis_client", return_value=mock_redis):
            result = await _check_rate_limit("widget-123", "127.0.0.1")
            assert result is False

    async def test_rate_limit_graceful_without_redis(self):
        """Rate limit allows all requests when Redis is unavailable."""
        with patch("app.api.widget.get_redis_client", return_value=None):
            result = await _check_rate_limit("widget-123", "127.0.0.1")
            assert result is True

    async def test_rate_limit_graceful_on_redis_error(self):
        """Rate limit allows requests when Redis raises error."""
        mock_redis = AsyncMock()
        mock_redis.incr.side_effect = Exception("Redis connection refused")

        with patch("app.api.widget.get_redis_client", return_value=mock_redis):
            result = await _check_rate_limit("widget-123", "127.0.0.1")
            assert result is True

    async def test_rate_limit_sets_expiry_on_first_request(self):
        """Rate limit sets TTL on first request (count=1)."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        with patch("app.api.widget.get_redis_client", return_value=mock_redis):
            await _check_rate_limit("widget-123", "127.0.0.1")
            mock_redis.expire.assert_called_once_with("widget_rl:widget-123:127.0.0.1", 3600)


# --- Endpoint Tests ---


class TestWidgetChatEndpoint:
    """Test POST /api/v1/widget/{widget_id}/chat endpoint."""

    async def test_invalid_widget_returns_404(self, client: AsyncClient):
        """Non-existent widget ID returns 404."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/widget/{fake_id}/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_inactive_widget_returns_404(self, client: AsyncClient, inactive_widget):
        """Inactive widget returns 404."""
        _, widget_config = inactive_widget
        response = await client.post(
            f"/api/v1/widget/{widget_config.id}/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_rate_limited_returns_429(self, client: AsyncClient, workspace_with_widget):
        """Rate-limited request returns 429."""
        _, widget_config, _ = workspace_with_widget

        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 21  # Over limit

        with patch("app.api.widget.get_redis_client", return_value=mock_redis):
            response = await client.post(
                f"/api/v1/widget/{widget_config.id}/chat",
                json={"message": "Hello"},
            )
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @patch("app.api.widget.MessagePipeline")
    @patch("app.api.widget.LLMRouter")
    async def test_successful_chat_returns_sse(
        self, mock_router, mock_pipeline_cls, client: AsyncClient, workspace_with_widget
    ):
        """Successful chat returns SSE stream with token and done events."""
        _, widget_config, _ = workspace_with_widget

        # Mock pipeline to return a simple result
        from app.core.engine import MessageResult

        mock_result = MessageResult(
            conversation_id=uuid4(),
            response="Hello world",
            citations=[{"doc": "Test.pdf", "page": 1, "score": 95}],
        )
        mock_pipeline = AsyncMock()
        mock_pipeline.process.return_value = mock_result
        mock_pipeline_cls.return_value = mock_pipeline

        with patch("app.api.widget.get_redis_client", return_value=None):
            response = await client.post(
                f"/api/v1/widget/{widget_config.id}/chat",
                json={"message": "What is your return policy?"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE events
        body = response.text
        assert "event: token" in body
        assert "event: done" in body
        assert "conversation_id" in body

    @patch("app.api.widget.MessagePipeline")
    @patch("app.api.widget.LLMRouter")
    async def test_chat_returns_citations_in_done(
        self, mock_router, mock_pipeline_cls, client: AsyncClient, workspace_with_widget
    ):
        """Done event includes citations when present."""
        _, widget_config, _ = workspace_with_widget

        from app.core.engine import MessageResult

        mock_result = MessageResult(
            conversation_id=uuid4(),
            response="Policy answer",
            citations=[{"doc": "Policy.pdf", "page": 3, "score": 96}],
        )
        mock_pipeline = AsyncMock()
        mock_pipeline.process.return_value = mock_result
        mock_pipeline_cls.return_value = mock_pipeline

        with patch("app.api.widget.get_redis_client", return_value=None):
            response = await client.post(
                f"/api/v1/widget/{widget_config.id}/chat",
                json={"message": "Return policy?"},
            )

        body = response.text
        assert "Policy.pdf" in body

    async def test_invalid_message_returns_422(self, client: AsyncClient, workspace_with_widget):
        """Invalid message (too long, empty) returns 422."""
        _, widget_config, _ = workspace_with_widget

        # Empty message
        response = await client.post(
            f"/api/v1/widget/{widget_config.id}/chat",
            json={"message": ""},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Too long
        response = await client.post(
            f"/api/v1/widget/{widget_config.id}/chat",
            json={"message": "x" * 501},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
