"""Unit tests for Human Handoff + Unified Inbox API (S52)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.channel import ChannelConfig
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.channels.provider import ChannelSendResult
from app.services.auth import hash_password

# --- Test Fixtures ---


@pytest.fixture
async def test_workspace(db_session):
    """Create a test workspace with user."""
    # Use unique email to avoid conflicts across tests
    unique_email = f"test-{uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        password_hash=hash_password("password123"),
        name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(owner_id=user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    return workspace, user


@pytest.fixture
async def whatsapp_conversation(test_workspace, db_session):
    """Create a WhatsApp conversation with messages and analytics."""
    workspace, user = test_workspace

    # Create WhatsApp channel config
    channel_config = ChannelConfig(
        workspace_id=workspace.id,
        channel="whatsapp",
        config={"recipient_phone": "+15551234567"},
        is_active=True,
    )
    db_session.add(channel_config)
    await db_session.flush()

    # Create conversation
    conversation = Conversation(
        workspace_id=workspace.id,
        channel="whatsapp",
        external_id="+15551234567",
        contact_name="John Doe",
        contact_info={"phone": "+15551234567"},
        status="escalated",
        lead_score=72,
        metadata_={
            "escalation_trigger": {
                "rule_type": "keyword",
                "matched": "cancel my account",
            }
        },
    )
    db_session.add(conversation)
    await db_session.flush()

    # Create messages with analytics
    messages_data = [
        {
            "role": "user",
            "content": "I want to upgrade my plan",
            "sentiment": "positive",
            "intent": "sales",
            "quality_score": None,
        },
        {
            "role": "assistant",
            "content": "Great! Let me help you with that.",
            "sentiment": None,
            "intent": None,
            "quality_score": 0.85,
            "citations": [
                {
                    "doc_name": "pricing-plans.pdf",
                    "chunk": "Our premium plan includes...",
                    "relevance": 0.89,
                }
            ],
        },
        {
            "role": "user",
            "content": "Actually, I want to cancel",
            "sentiment": "negative",
            "intent": "escalation",
            "quality_score": None,
        },
        {
            "role": "assistant",
            "content": "I understand your concern.",
            "sentiment": None,
            "intent": None,
            "quality_score": 0.45,
        },
    ]

    for msg_data in messages_data:
        message = Message(
            conversation_id=conversation.id,
            **msg_data,
        )
        db_session.add(message)

    await db_session.commit()
    await db_session.refresh(conversation)

    return conversation, workspace, channel_config


# --- TestHandoffContext ---


class TestHandoffContext:
    """Test handoff context assembly."""

    async def test_assembles_citations_from_messages(self, whatsapp_conversation, db_session):
        """Handoff context includes RAG citations from message metadata."""
        from app.modules.channels.handoff import assemble_handoff_context

        conversation, workspace, _ = whatsapp_conversation

        context = await assemble_handoff_context(conversation.id, db_session)

        assert "rag_contexts" in context
        assert len(context["rag_contexts"]) == 1
        assert context["rag_contexts"][0]["source"] == "pricing-plans.pdf"
        assert context["rag_contexts"][0]["score"] == 0.89

    async def test_assembles_sentiment_timeline(self, whatsapp_conversation, db_session):
        """Handoff context includes sentiment timeline."""
        from app.modules.channels.handoff import assemble_handoff_context

        conversation, workspace, _ = whatsapp_conversation

        context = await assemble_handoff_context(conversation.id, db_session)

        assert "sentiment_timeline" in context
        sentiments = [s["sentiment"] for s in context["sentiment_timeline"]]
        assert sentiments == ["positive", None, "negative", None]

    async def test_assembles_intent_history(self, whatsapp_conversation, db_session):
        """Handoff context includes intent history."""
        from app.modules.channels.handoff import assemble_handoff_context

        conversation, workspace, _ = whatsapp_conversation

        context = await assemble_handoff_context(conversation.id, db_session)

        assert "intent_history" in context
        intents = [i["intent"] for i in context["intent_history"]]
        assert intents == ["sales", None, "escalation", None]

    async def test_includes_quality_scores(self, whatsapp_conversation, db_session):
        """Handoff context includes quality scores."""
        from app.modules.channels.handoff import assemble_handoff_context

        conversation, workspace, _ = whatsapp_conversation

        context = await assemble_handoff_context(conversation.id, db_session)

        assert "quality_scores" in context
        scores = [q["score"] for q in context["quality_scores"]]
        assert scores == [None, 0.85, None, 0.45]

    async def test_empty_rag_returns_empty_array(self, test_workspace, db_session):
        """Handoff context returns empty array for RAG when no citations exist."""
        from app.modules.channels.handoff import assemble_handoff_context

        workspace, user = test_workspace

        # Create conversation with no citations
        conversation = Conversation(
            workspace_id=workspace.id,
            channel="web",
            status="active",
        )
        db_session.add(conversation)
        await db_session.flush()

        # Add message without citations
        message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Hello",
        )
        db_session.add(message)
        await db_session.commit()

        context = await assemble_handoff_context(conversation.id, db_session)

        assert context["rag_contexts"] == []  # Empty array, not null

    async def test_includes_lead_score(self, whatsapp_conversation, db_session):
        """Handoff context includes lead score."""
        from app.modules.channels.handoff import assemble_handoff_context

        conversation, workspace, _ = whatsapp_conversation

        context = await assemble_handoff_context(conversation.id, db_session)

        assert "lead_score" in context
        assert context["lead_score"] == 72

    async def test_includes_escalation_reason(self, whatsapp_conversation, db_session):
        """Handoff context includes human-readable escalation reason."""
        from app.modules.channels.handoff import assemble_handoff_context

        conversation, workspace, _ = whatsapp_conversation

        context = await assemble_handoff_context(conversation.id, db_session)

        assert "escalation_reason" in context
        assert context["escalation_reason"] == "keyword: cancel my account"


# --- TestConversationFiltering ---


class TestConversationFiltering:
    """Test conversation listing filters."""

    async def test_filter_by_channel(self, test_workspace, db_session, client: AsyncClient):
        """Conversation listing filters by channel."""
        workspace, user = test_workspace

        # Create conversations with different channels (valid: web, whatsapp, telegram, voice)
        for channel in ["whatsapp", "telegram", "web"]:
            conversation = Conversation(
                workspace_id=workspace.id,
                channel=channel,
                status="active",
            )
            db_session.add(conversation)

        await db_session.commit()

        # Login with the unique email from fixture
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "password123"},  # pragma: allowlist secret
        )
        assert login_response.status_code == status.HTTP_200_OK

        # Filter by whatsapp
        response = await client.get("/api/v1/chat/conversations?channel=whatsapp")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conversations"]) == 1

    async def test_filter_by_status(self, test_workspace, db_session, client: AsyncClient):
        """Conversation listing filters by status."""
        workspace, user = test_workspace

        # Create conversations with different statuses (valid: active, escalated, closed)
        for conv_status in ["active", "escalated", "closed"]:
            conversation = Conversation(
                workspace_id=workspace.id,
                channel="web",
                status=conv_status,
            )
            db_session.add(conversation)

        await db_session.commit()

        # Login with the unique email from fixture
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "password123"},  # pragma: allowlist secret
        )
        assert login_response.status_code == status.HTTP_200_OK

        # Filter by escalated
        response = await client.get("/api/v1/chat/conversations?status=escalated")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conversations"]) == 1

    async def test_filter_by_lead_score_range(
        self, test_workspace, db_session, client: AsyncClient
    ):
        """Conversation listing filters by minimum lead score."""
        workspace, user = test_workspace

        # Create conversations with different lead scores
        for lead_score in [10, 50, 90]:
            conversation = Conversation(
                workspace_id=workspace.id,
                channel="web",
                status="active",
                lead_score=lead_score,
            )
            db_session.add(conversation)

        await db_session.commit()

        # Login with the unique email from fixture
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "password123"},  # pragma: allowlist secret
        )
        assert login_response.status_code == status.HTTP_200_OK

        # Filter by min_lead_score=50
        response = await client.get("/api/v1/chat/conversations?min_lead_score=50")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conversations"]) == 2  # 50 and 90


# --- TestChannelResponseRouting ---


class TestChannelResponseRouting:
    """Test channel response routing."""

    async def test_routes_reply_through_whatsapp(self, whatsapp_conversation, db_session):
        """Response router sends replies through WhatsApp for WhatsApp conversations."""
        from app.modules.channels.response_router import _PROVIDER_REGISTRY, send_channel_response

        conversation, workspace, channel_config = whatsapp_conversation

        # Mock provider send_message
        mock_provider = MagicMock()
        mock_provider.send_message = AsyncMock(
            return_value=ChannelSendResult(
                success=True,
                provider_message_id="SM1234567890",
            )
        )

        # Replace registry entry with mock
        original_provider = _PROVIDER_REGISTRY.get("whatsapp")
        _PROVIDER_REGISTRY["whatsapp"] = mock_provider

        try:
            # Send response
            result = await send_channel_response(
                conversation_id=conversation.id,
                message="Thanks for your feedback!",
                db=db_session,
            )

            assert result.success is True
            assert result.provider_message_id == "SM1234567890"
        finally:
            # Restore original provider
            if original_provider:
                _PROVIDER_REGISTRY["whatsapp"] = original_provider

    async def test_routes_reply_through_widget(self, test_workspace, db_session):
        """Response router sends replies through Widget for web conversations."""
        from app.modules.channels.response_router import _PROVIDER_REGISTRY, send_channel_response

        workspace, user = test_workspace

        # Create widget channel config (ChannelConfig uses 'widget', Conversation uses 'web')
        channel_config = ChannelConfig(
            workspace_id=workspace.id,
            channel="widget",
            config={"domain": "example.com"},
            is_active=True,
        )
        db_session.add(channel_config)
        await db_session.flush()

        # Create web conversation (Conversation model uses 'web' channel)
        conversation = Conversation(
            workspace_id=workspace.id,
            channel="web",
            status="active",
        )
        db_session.add(conversation)
        await db_session.commit()

        # Mock provider send_message
        mock_provider = MagicMock()
        mock_provider.send_message = AsyncMock(
            return_value=ChannelSendResult(
                success=True,
                provider_message_id="web_msg_123",
            )
        )

        # Replace registry entry with mock
        original_provider = _PROVIDER_REGISTRY.get("web")
        _PROVIDER_REGISTRY["web"] = mock_provider

        try:
            # Send response
            result = await send_channel_response(
                conversation_id=conversation.id,
                message="How can I help?",
                db=db_session,
            )

            assert result.success is True
            assert result.provider_message_id == "web_msg_123"
        finally:
            # Restore original provider
            if original_provider:
                _PROVIDER_REGISTRY["web"] = original_provider

    @patch("app.modules.channels.response_router.create_event_bus")
    async def test_queues_on_send_failure(self, mock_event_bus, whatsapp_conversation, db_session):
        """Response router queues message in outbox when send fails with should_retry=True."""
        from app.modules.channels.response_router import _PROVIDER_REGISTRY, send_channel_response

        conversation, workspace, channel_config = whatsapp_conversation

        # Mock provider send_message failure
        mock_provider = MagicMock()
        mock_provider.send_message = AsyncMock(
            return_value=ChannelSendResult(
                success=False,
                error="Network timeout",
                should_retry=True,
            )
        )

        # Mock event bus
        mock_bus_instance = AsyncMock()
        mock_event_bus.return_value = mock_bus_instance

        # Replace registry entry with mock
        original_provider = _PROVIDER_REGISTRY.get("whatsapp")
        _PROVIDER_REGISTRY["whatsapp"] = mock_provider

        try:
            # Send response
            result = await send_channel_response(
                conversation_id=conversation.id,
                message="Retry me",
                db=db_session,
            )

            # Verify failure result
            assert result.success is False
            assert result.should_retry is True

            # Verify event was published to queue message
            mock_bus_instance.publish.assert_called_once()
            call_args = mock_bus_instance.publish.call_args
            assert (
                "WEBHOOK_DELIVERY_REQUIRED" in str(call_args)
                or call_args[0][0] == "webhook.delivery_required"
            )
        finally:
            # Restore original provider
            if original_provider:
                _PROVIDER_REGISTRY["whatsapp"] = original_provider
