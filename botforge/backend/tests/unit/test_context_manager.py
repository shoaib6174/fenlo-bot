"""Tests for Context Manager"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.context_manager import ContextManager, LoadContextStep, PersistenceStep
from app.core.engine import MessageContext
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.models.workspace import Workspace


@pytest.fixture
async def test_workspace(db_session):
    """Create a test workspace with owner user"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        password_hash="fake_hash",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Test Workspace",
        features={},
        settings={},
    )
    db_session.add(workspace)
    await db_session.flush()
    return workspace


@pytest.mark.asyncio
async def test_create_new_conversation(db_session, test_workspace):
    """Test that first message creates a new conversation"""
    manager = ContextManager(db_session)
    workspace_id = test_workspace.id

    conversation_id, history, system_prompt, lead_score = await manager.load_context(
        workspace_id=workspace_id,
        conversation_id=None,
    )

    # Should create new conversation
    assert conversation_id is not None
    assert isinstance(conversation_id, uuid.UUID)
    assert history == []
    assert "helpful AI assistant" in system_prompt

    # Verify conversation exists in DB
    query = select(Conversation).where(Conversation.id == conversation_id)
    result = await db_session.execute(query)
    conversation = result.scalar_one()
    assert conversation.workspace_id == workspace_id
    assert conversation.channel == "web"
    assert conversation.status == "active"


@pytest.mark.asyncio
async def test_load_existing_conversation_history(db_session, test_workspace):
    """Test loading last 20 messages from existing conversation"""
    workspace_id = test_workspace.id
    conversation_id = uuid.uuid4()

    # Create conversation
    conversation = Conversation(
        id=conversation_id,
        workspace_id=workspace_id,
        channel="web",
        status="active",
        started_at=datetime.now(UTC),
    )
    db_session.add(conversation)
    await db_session.flush()

    # Create 25 messages (should only load last 20)
    from datetime import timedelta

    base_time = datetime.now(UTC)
    for i in range(25):
        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
            created_at=base_time + timedelta(seconds=i),  # Increment time for each message
        )
        db_session.add(msg)
    await db_session.flush()

    # Load context
    manager = ContextManager(db_session)
    loaded_id, history, system_prompt, lead_score = await manager.load_context(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
    )

    # Should load only last 20 messages
    assert loaded_id == conversation_id
    assert len(history) == 20
    # Should be in chronological order (oldest first)
    assert history[0]["content"] == "Message 5"
    assert history[-1]["content"] == "Message 24"


@pytest.mark.asyncio
async def test_save_message_pair(db_session, test_workspace):
    """Test saving user-assistant message pair"""
    workspace_id = test_workspace.id
    conversation_id = uuid.uuid4()

    # Create conversation
    conversation = Conversation(
        id=conversation_id,
        workspace_id=workspace_id,
        channel="web",
        status="active",
        started_at=datetime.now(UTC),
    )
    db_session.add(conversation)
    await db_session.flush()

    # Save message pair
    manager = ContextManager(db_session)
    metadata = {
        "sentiment": "positive",
        "quality_score": 0.85,
        "intent": "faq",
        "tokens_used": 150,
        "citations": [{"doc_name": "test.pdf", "page": 1}],
    }
    await manager.save_message_pair(
        conversation_id=conversation_id,
        user_message="What is your return policy?",
        assistant_message="Our return policy is 30 days.",
        metadata=metadata,
    )
    await db_session.flush()

    # Verify messages saved
    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    result = await db_session.execute(query)
    messages = result.scalars().all()

    assert len(messages) == 2

    # User message
    user_msg = messages[0]
    assert user_msg.role == "user"
    assert user_msg.content == "What is your return policy?"

    # Assistant message with metadata
    assistant_msg = messages[1]
    assert assistant_msg.role == "assistant"
    assert assistant_msg.content == "Our return policy is 30 days."
    assert assistant_msg.sentiment == "positive"
    assert assistant_msg.quality_score == 0.85
    assert assistant_msg.intent == "faq"
    assert assistant_msg.tokens_used == 150
    assert assistant_msg.citations == [{"doc_name": "test.pdf", "page": 1}]


@pytest.mark.asyncio
async def test_load_context_step_creates_conversation(db_session, test_workspace):
    """Test LoadContextStep pipeline step creates conversation"""
    step = LoadContextStep(db_session)
    workspace_id = test_workspace.id

    context = MessageContext(
        workspace_id=workspace_id,
        user_id=None,
        conversation_id=None,
        message="Hello",
    )

    updated_context = await step.execute(context)

    # Should populate context with conversation_id, history, system_prompt
    assert updated_context.conversation_id is not None
    assert updated_context.conversation_history == []
    assert "helpful AI assistant" in updated_context.system_prompt


@pytest.mark.asyncio
async def test_load_context_step_loads_history(db_session, test_workspace):
    """Test LoadContextStep loads existing conversation history"""
    workspace_id = test_workspace.id
    conversation_id = uuid.uuid4()

    # Create conversation with messages
    conversation = Conversation(
        id=conversation_id,
        workspace_id=workspace_id,
        channel="web",
        status="active",
        started_at=datetime.now(UTC),
    )
    db_session.add(conversation)

    for i in range(3):
        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
            created_at=datetime.now(UTC),
        )
        db_session.add(msg)
    await db_session.flush()

    # Execute step
    step = LoadContextStep(db_session)
    context = MessageContext(
        workspace_id=workspace_id,
        user_id=None,
        conversation_id=conversation_id,
        message="New message",
    )

    updated_context = await step.execute(context)

    assert updated_context.conversation_id == conversation_id
    assert len(updated_context.conversation_history) == 3


@pytest.mark.asyncio
async def test_persistence_step_saves_message_pair(db_session, test_workspace):
    """Test PersistenceStep saves message pair to DB"""
    workspace_id = test_workspace.id
    conversation_id = uuid.uuid4()

    # Create conversation
    conversation = Conversation(
        id=conversation_id,
        workspace_id=workspace_id,
        channel="web",
        status="active",
        started_at=datetime.now(UTC),
    )
    db_session.add(conversation)
    await db_session.flush()

    # Execute persistence step
    step = PersistenceStep(db_session)
    context = MessageContext(
        workspace_id=workspace_id,
        user_id=None,
        conversation_id=conversation_id,
        message="What is your refund policy?",
        response="Refunds are available within 30 days.",
        sentiment="neutral",
        quality_score=0.9,
        intent="faq",
        tokens_used=120,
    )

    await step.execute(context)
    await db_session.flush()

    # Verify messages saved
    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    result = await db_session.execute(query)
    messages = result.scalars().all()

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "What is your refund policy?"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Refunds are available within 30 days."
    assert messages[1].sentiment == "neutral"
    assert messages[1].quality_score == 0.9


@pytest.mark.asyncio
async def test_persistence_step_skips_if_no_response(db_session):
    """Test PersistenceStep skips saving if no response generated"""
    step = PersistenceStep(db_session)
    workspace_id = uuid.uuid4()

    context = MessageContext(
        workspace_id=workspace_id,
        user_id=None,
        conversation_id=None,
        message="Test",
        response=None,  # No response
    )

    # Should not raise error
    await step.execute(context)
    await db_session.flush()

    # No messages should be saved
    query = select(Message)
    result = await db_session.execute(query)
    messages = result.scalars().all()
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_save_message_pair_invalid_conversation_id(db_session, test_workspace):
    """Test that saving a message with a non-existent conversation_id raises ValueError"""
    manager = ContextManager(db_session)
    fake_conversation_id = uuid.uuid4()

    with pytest.raises(ValueError, match="does not exist"):
        await manager.save_message_pair(
            conversation_id=fake_conversation_id,
            user_message="This should fail",
            assistant_message="Never saved",
        )


@pytest.mark.asyncio
async def test_default_system_prompt():
    """Test default system prompt contains expected content"""
    manager = ContextManager(None)  # No DB needed for this test
    prompt = manager._get_default_system_prompt()

    assert "helpful AI assistant" in prompt
    assert "professional and friendly" in prompt
