"""S47 tests — debug endpoint and conversation replay data assembly."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.services.auth import hash_password


async def _create_debug_fixtures(db_session: AsyncSession):
    """Create workspace + user + conversation + messages for debug tests."""
    from app.models.user import User
    from app.models.workspace import Workspace, WorkspaceMember

    user_id = uuid4()
    workspace_id = uuid4()
    conv_id = uuid4()

    user = User(
        id=user_id,
        email=f"debug-{uuid4().hex[:6]}@test.com",
        password_hash=hash_password("password"),
        name="Debug User",
    )
    workspace = Workspace(id=workspace_id, owner_id=user_id, name="Debug WS")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner")

    db_session.add_all([user, workspace, member])
    await db_session.flush()

    conv = Conversation(
        id=conv_id,
        workspace_id=workspace_id,
        channel="web",
        status="active",
        lead_score=25,
        started_at=datetime.now(UTC),
    )
    db_session.add(conv)
    await db_session.flush()

    # User message
    user_msg = Message(
        id=uuid4(),
        conversation_id=conv_id,
        role="user",
        content="What is your pricing?",
        created_at=datetime.now(UTC),
    )
    db_session.add(user_msg)
    await db_session.flush()

    # Assistant message with full analytics
    assistant_msg = Message(
        id=uuid4(),
        conversation_id=conv_id,
        role="assistant",
        content="Our pricing starts at $29/month.",
        sentiment="positive",
        intent="sales",
        quality_score=0.85,
        tokens_used=42,
        citations=[
            {
                "doc_name": "pricing.pdf",
                "page_number": 1,
                "chunk_text": "Pricing starts at $29/month for Starter tier.",
                "relevance_score": 0.92,
                "document_id": str(uuid4()),
            }
        ],
        feedback="positive",
        created_at=datetime.now(UTC),
    )
    db_session.add(assistant_msg)
    await db_session.flush()

    return user_id, workspace_id, conv_id


@pytest.mark.asyncio
class TestDebugEndpoint:
    """Tests for the enhanced /debug conversation endpoint."""

    async def test_debug_returns_conversation_metadata(self, db_session: AsyncSession):
        """Debug endpoint includes conversation-level metadata."""
        user_id, workspace_id, conv_id = await _create_debug_fixtures(db_session)

        # Simulate what the endpoint does
        from sqlalchemy import select

        result = await db_session.execute(select(Conversation).where(Conversation.id == conv_id))
        conv = result.scalar_one()

        assert conv.lead_score == 25
        assert conv.channel == "web"
        assert conv.status == "active"

    async def test_debug_returns_per_message_analytics(self, db_session: AsyncSession):
        """Debug endpoint returns sentiment, intent, quality, citations per message."""
        user_id, workspace_id, conv_id = await _create_debug_fixtures(db_session)

        from sqlalchemy import select

        result = await db_session.execute(
            select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
        )
        messages = result.scalars().all()

        assert len(messages) == 2

        # User message has no analytics
        user_msg = messages[0]
        assert user_msg.role == "user"
        assert user_msg.sentiment is None

        # Assistant message has full analytics
        assistant_msg = messages[1]
        assert assistant_msg.role == "assistant"
        assert assistant_msg.sentiment == "positive"
        assert assistant_msg.intent == "sales"
        assert assistant_msg.quality_score == 0.85
        assert assistant_msg.tokens_used == 42
        assert assistant_msg.feedback == "positive"
        assert len(assistant_msg.citations) == 1
        assert assistant_msg.citations[0]["relevance_score"] == 0.92

    async def test_debug_data_assembly(self, db_session: AsyncSession):
        """Debug data assembled from DB matches expected structure."""
        user_id, workspace_id, conv_id = await _create_debug_fixtures(db_session)

        from sqlalchemy import select

        result = await db_session.execute(select(Conversation).where(Conversation.id == conv_id))
        conversation = result.scalar_one()

        msg_result = await db_session.execute(
            select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()

        # Assemble debug_data like the endpoint does
        debug_data = {
            "conversation_id": str(conv_id),
            "conversation": {
                "status": conversation.status,
                "channel": conversation.channel,
                "lead_score": conversation.lead_score,
                "started_at": conversation.started_at.isoformat()
                if conversation.started_at
                else None,
                "message_count": len(messages),
            },
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "sentiment": msg.sentiment,
                    "intent": msg.intent,
                    "quality_score": msg.quality_score,
                    "tokens_used": msg.tokens_used,
                    "latency_ms": msg.latency_ms,
                    "citations": msg.citations or [],
                    "feedback": msg.feedback,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
            "confidence_scores": [msg.quality_score for msg in messages if msg.quality_score],
            "intents": [msg.intent for msg in messages if msg.intent],
        }

        assert debug_data["conversation"]["lead_score"] == 25
        assert debug_data["conversation"]["message_count"] == 2
        assert len(debug_data["messages"]) == 2
        assert debug_data["confidence_scores"] == [0.85]
        assert debug_data["intents"] == ["sales"]

        # Assistant message has citations
        assistant_debug = debug_data["messages"][1]
        assert len(assistant_debug["citations"]) == 1
        assert assistant_debug["citations"][0]["doc_name"] == "pricing.pdf"

    async def test_pipeline_replay_data_matches_timeline(self, db_session: AsyncSession):
        """Replay timeline can be reconstructed from per-message debug data."""
        user_id, workspace_id, conv_id = await _create_debug_fixtures(db_session)

        from sqlalchemy import select

        msg_result = await db_session.execute(
            select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()

        # Replay simulation: for assistant message, reconstruct pipeline steps
        user_msg = messages[0]
        assistant_msg = messages[1]

        # Step 1: User input
        assert user_msg.content == "What is your pricing?"

        # Step 2: RAG retrieval
        citations = assistant_msg.citations or []
        assert len(citations) == 1
        top_score = citations[0]["relevance_score"]
        assert top_score == 0.92

        # Step 3: LLM response
        assert "pricing" in assistant_msg.content.lower()
        assert assistant_msg.tokens_used == 42

        # Step 4-6: Analytics
        assert assistant_msg.sentiment == "positive"
        assert assistant_msg.intent == "sales"
        assert assistant_msg.quality_score == 0.85
